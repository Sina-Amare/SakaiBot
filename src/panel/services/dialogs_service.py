"""Dialogs service: one throttled ``iter_dialogs`` pass classified into
PV / group / channel / bot, cached for 5 minutes, with search.

This fills a gap in the existing code, which only fetched PVs and megagroups
(never broadcast channels). It is READ-ONLY.
"""

import time
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

    async def _ensure(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        cache = self.state.dialogs_cache
        fresh = (
            cache is not None
            and not force_refresh
            and (time.monotonic() - cache.get("ts", 0)) < DIALOGS_TTL_SECONDS
        )
        if fresh:
            return cache["items"]
        items = await self._walk()
        self.state.dialogs_cache = {"items": items, "ts": time.monotonic()}
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
            items = [r for r in items if r["kind"] == kind]
        if q:
            items = [r for r in items if self._matches(r, q)]
        total = len(items)
        page = items[offset: offset + limit]
        counts: Dict[str, int] = {"pv": 0, "group": 0, "channel": 0, "bot": 0}
        for r in (self.state.dialogs_cache or {}).get("items", []):
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        return {
            "ok": True,
            "items": page,
            "total": total,
            "counts": counts,
            "cached_at": (self.state.dialogs_cache or {}).get("ts"),
        }

    def find(self, entity_id: int) -> Optional[Dict[str, Any]]:
        cache = self.state.dialogs_cache
        if not cache:
            return None
        for r in cache["items"]:
            if r["id"] == int(entity_id):
                return r
        return None
