"""Dialogs service: one throttled ``iter_dialogs`` pass classified into
PV / group / channel / bot, cached for 5 minutes, with search.

This fills a gap in the existing code, which only fetched PVs and megagroups
(never broadcast channels). It is READ-ONLY.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from telethon.tl.types import Channel, Chat, User

from ...utils.logging import get_logger
from ..errors import PanelUnavailable

logger = get_logger(__name__)

DIALOGS_TTL_SECONDS = 300
DIALOGS_WALK_LIMIT = 1000  # cover large accounts; the walk is cached after the first pass


class DialogsService:
    def __init__(self, state: Any) -> None:
        self.state = state

    def _classify(self, dialog: Any) -> Optional[Dict[str, Any]]:
        entity = getattr(dialog, "entity", None)
        if entity is None:
            return None

        kind: Optional[str] = None
        display_name = ""
        username = getattr(entity, "username", None)

        if isinstance(entity, User):
            if getattr(entity, "deleted", False) or getattr(entity, "is_self", False):
                return None
            kind = "bot" if getattr(entity, "bot", False) else "pv"
            first = entity.first_name or ""
            last = entity.last_name or ""
            display_name = (first + " " + last).strip() or (username or f"User {entity.id}")
        elif isinstance(entity, Channel):
            display_name = entity.title or f"Channel {entity.id}"
            if getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False):
                kind = "group"
            elif getattr(entity, "broadcast", False):
                kind = "channel"
            else:
                kind = "group"
        elif isinstance(entity, Chat):
            kind = "group"
            display_name = entity.title or f"Group {entity.id}"
        else:
            return None

        # Last-message preview comes free with iter_dialogs (no extra RPC).
        last = getattr(dialog, "message", None)
        preview = ""
        if last is not None:
            if getattr(last, "message", None):
                preview = last.message.replace("\n", " ")[:90]
            elif getattr(last, "media", None) is not None:
                if getattr(last, "photo", None):
                    preview = "📷 Photo"
                elif getattr(last, "sticker", None):
                    preview = "🩷 Sticker"
                elif getattr(last, "voice", None) or getattr(last, "audio", None):
                    preview = "🎤 Voice"
                elif getattr(last, "video", None) or getattr(last, "gif", None):
                    preview = "🎬 Video"
                else:
                    preview = "📄 File"
        last_date = getattr(dialog, "date", None)

        return {
            "id": int(entity.id),
            "kind": kind,
            "display_name": display_name,
            "username": f"@{username}" if username else None,
            "has_photo": getattr(entity, "photo", None) is not None,
            "is_forum": bool(getattr(entity, "forum", False)),
            "preview": preview,
            "last_date": last_date.isoformat() if last_date else None,
            # Folder signals — all free from iter_dialogs, no extra RPC.
            "unread": int(getattr(dialog, "unread_count", 0) or 0),
            "pinned": bool(getattr(dialog, "pinned", False)),
            "contact": bool(getattr(entity, "contact", False)),
        }

    async def _walk(self) -> List[Dict[str, Any]]:
        client = self.state.client
        if client is None:
            raise PanelUnavailable()

        async def _collect() -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            async for dialog in client.iter_dialogs(limit=DIALOGS_WALK_LIMIT):
                row = self._classify(dialog)
                if row is not None:
                    items.append(row)
            return items

        # One throttled op for the whole walk (paced, FloodWait-handled).
        return await self.state.throttle.tg_read(_collect)

    def _disk_path(self) -> Optional[Path]:
        mc = getattr(self.state, "media_cache", None)
        root = getattr(mc, "root", None)
        return Path(root) / "dialogs.json" if root else None

    def _load_disk(self) -> Optional[List[Dict[str, Any]]]:
        p = self._disk_path()
        if not p or not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            items = data.get("items") if isinstance(data, dict) else data
            return items if isinstance(items, list) and items else None
        except Exception:  # noqa: BLE001 - a corrupt cache just means a live walk
            return None

    def _save_disk(self, items: List[Dict[str, Any]]) -> None:
        p = self._disk_path()
        if not p:
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"items": items}), encoding="utf-8")
        except Exception:  # noqa: BLE001 - best-effort cache
            pass

    async def _refresh_bg(self) -> None:
        try:
            items = await self._walk()
            self.state.dialogs_cache = {"items": items, "ts": time.monotonic()}
            self._save_disk(items)
        except Exception as exc:  # noqa: BLE001
            logger.debug("background dialog refresh skipped: %s", exc)

    async def _ensure(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        cache = self.state.dialogs_cache
        fresh = (
            cache is not None
            and not force_refresh
            and (time.monotonic() - cache.get("ts", 0)) < DIALOGS_TTL_SECONDS
        )
        if fresh:
            return cache["items"]
        # Cold start: serve the disk snapshot INSTANTLY, refresh in the background
        # (stale-while-revalidate) so a panel restart isn't blocked on a full walk.
        if cache is None and not force_refresh:
            disk = self._load_disk()
            if disk is not None:
                self.state.dialogs_cache = {"items": disk, "ts": time.monotonic()}
                asyncio.create_task(self._refresh_bg())
                return disk
        items = await self._walk()
        self.state.dialogs_cache = {"items": items, "ts": time.monotonic()}
        self._save_disk(items)
        return items

    @staticmethod
    def _matches(row: Dict[str, Any], q: str) -> bool:
        q = q.lower()
        if q.startswith("@"):
            q = q[1:]
        if str(row["id"]) == q:
            return True
        uname = (row.get("username") or "").lower().lstrip("@")
        if q in uname:
            return True
        return q in row.get("display_name", "").lower()

    async def list_dialogs(
        self,
        *,
        kind: str = "all",
        q: Optional[str] = None,
        offset: int = 0,
        limit: int = 200,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        items = await self._ensure(force_refresh=force_refresh)
        if kind and kind != "all":
            items = [r for r in items if self._in_folder(r, kind)]
        if q:
            items = [r for r in items if self._matches(r, q)]
        total = len(items)
        page = items[offset: offset + limit]
        return {
            "ok": True,
            "items": page,
            "total": total,
            "counts": self._counts(),       # kept for back-compat (pv/group/channel/bot)
            "folders": self._folder_counts(),
            "cached_at": (self.state.dialogs_cache or {}).get("ts"),
        }

    @staticmethod
    def _in_folder(row: Dict[str, Any], folder: str) -> bool:
        if folder in ("pv", "group", "channel", "bot"):
            return row["kind"] == folder
        if folder == "unread":
            return int(row.get("unread", 0)) > 0
        if folder == "pinned":
            return bool(row.get("pinned"))
        if folder == "contacts":
            return row["kind"] == "pv" and bool(row.get("contact"))
        return True  # "all" / unknown -> no filter

    def _counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"pv": 0, "group": 0, "channel": 0, "bot": 0}
        for r in (self.state.dialogs_cache or {}).get("items", []):
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        return counts

    def _folder_counts(self) -> Dict[str, int]:
        """Counts for every folder in the rail (computed over the full cache)."""
        all_items = (self.state.dialogs_cache or {}).get("items", [])
        f = {k: 0 for k in
             ("all", "unread", "contacts", "pv", "group", "channel", "bot", "pinned")}
        for r in all_items:
            f["all"] += 1
            f[r["kind"]] = f.get(r["kind"], 0) + 1
            if int(r.get("unread", 0)) > 0:
                f["unread"] += 1
            if r.get("pinned"):
                f["pinned"] += 1
            if r["kind"] == "pv" and r.get("contact"):
                f["contacts"] += 1
        return f

    def find(self, entity_id: int) -> Optional[Dict[str, Any]]:
        cache = self.state.dialogs_cache
        if not cache:
            return None
        for r in cache["items"]:
            if r["id"] == int(entity_id):
                return r
        return None
