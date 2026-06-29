"""Entity service: per-entity detail, message history, media enumeration,
and lazy/cached real profile photos. All READ-ONLY and throttled.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from telethon.tl.types import (
    InputMessagesFilterDocument,
    InputMessagesFilterGif,
    InputMessagesFilterMusic,
    InputMessagesFilterPhotos,
    InputMessagesFilterPhotoVideo,
    InputMessagesFilterUrl,
    InputMessagesFilterVideo,
    InputMessagesFilterVoice,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

from ...utils.logging import get_logger
from ..errors import PanelNotFound, PanelUnavailable
from ..media_cache import AVATAR_TTL_SECONDS

logger = get_logger(__name__)

HISTORY_MAX = 200
MEDIA_MAX = 60


class EntityService:
    def __init__(self, state: Any) -> None:
        self.state = state
        self._profile_cache: Dict[int, tuple] = {}  # id -> (data, monotonic ts)

    def _require_client(self):
        if self.state.client is None:
            raise PanelUnavailable()
        return self.state.client

    # ---------- presence ----------
    def _presence(self, entity: Any) -> Optional[Dict[str, Any]]:
        """Interpret a User's last-seen status. Pure — rides the get_entity
        result, so it costs NO extra Telegram RPC. Returns None when status is
        unavailable (privacy-hidden, a bot, or a group/channel)."""
        status = getattr(entity, "status", None)
        if status is None:
            return None
        if isinstance(status, UserStatusOnline):
            exp = getattr(status, "expires", None)
            return {"state": "online", "expires": exp.isoformat() if exp else None}
        if isinstance(status, UserStatusOffline):
            was = getattr(status, "was_online", None)
            return {"state": "offline", "was_online": was.isoformat() if was else None}
        if isinstance(status, UserStatusRecently):
            return {"state": "recently"}
        if isinstance(status, UserStatusLastWeek):
            return {"state": "last_week"}
        if isinstance(status, UserStatusLastMonth):
            return {"state": "last_month"}
        return None

    # ---------- detail ----------
    async def detail(self, entity_id: int) -> Dict[str, Any]:
        client = self._require_client()
        row = self.state.dialogs.find(entity_id) or {}
        entity = await self.state.throttle.tg_read(lambda: client.get_entity(int(entity_id)))
        display_name = row.get("display_name")
        if not display_name:
            display_name = (
                getattr(entity, "title", None)
                or " ".join(
                    p for p in [getattr(entity, "first_name", ""), getattr(entity, "last_name", "")] if p
                ).strip()
                or f"Entity {entity_id}"
            )
        return {
            "ok": True,
            "id": int(entity_id),
            "kind": row.get("kind", "pv"),
            "display_name": display_name,
            "username": (f"@{entity.username}" if getattr(entity, "username", None) else None),
            "is_forum": bool(getattr(entity, "forum", False)),
            "member_count": getattr(entity, "participants_count", None),
            "has_photo": getattr(entity, "photo", None) is not None,
            "verified": bool(getattr(entity, "verified", False)),
            "is_bot": bool(getattr(entity, "bot", False)),
            "presence": self._presence(entity),
        }

    # ---------- history ----------
    def _sender_name(self, msg: Any, entity_kind: str, entity_name: str) -> str:
        if getattr(msg, "out", False):
            return "You"
        if entity_kind == "pv":
            return entity_name
        sender = getattr(msg, "sender", None)  # cached only; no extra RPC
        if sender is not None:
            name = " ".join(
                p for p in [getattr(sender, "first_name", ""), getattr(sender, "last_name", "")] if p
            ).strip()
            if name:
                return name
            if getattr(sender, "title", None):
                return sender.title
        sid = getattr(msg, "sender_id", None)
        return f"#{sid}" if sid else "Unknown"

    def _format_message(self, msg: Any, kind: str, ename: str) -> Dict[str, Any]:
        """Shared message shape used by history, polling, and send echo."""
        media_kind = self._media_kind(msg)
        file_name, mime = self._doc_meta(msg)
        sticker_format, is_animated, is_video = self._sticker_meta(msg)
        return {
            "id": msg.id,
            "sender": self._sender_name(msg, kind, ename),
            "sender_id": getattr(msg, "sender_id", None),
            "out": bool(getattr(msg, "out", False)),
            "text": msg.message or "",
            "timestamp": msg.date.isoformat() if msg.date else None,
            "edited": bool(getattr(msg, "edit_date", None)),
            "has_media": getattr(msg, "media", None) is not None,
            "media_kind": media_kind,
            "file_name": file_name,
            "mime": mime,
            "is_voice": bool(getattr(msg, "voice", None) or getattr(msg, "audio", None)),
            "sticker_format": sticker_format,
            "is_animated": is_animated,
            "is_video": is_video,
        }

    def _reply_snippet(self, msg: Any, kind: str, ename: str) -> Dict[str, Any]:
        """Compact preview of a replied-to message (text or a media label)."""
        text = (msg.message or "").strip()
        if not text:
            mk = self._media_kind(msg)
            text = {
                "photo": "Photo", "sticker": "Sticker", "video": "Video",
                "gif": "GIF", "audio": "Voice message", "document": "File",
            }.get(mk, "Media" if getattr(msg, "media", None) else "")
        return {"id": msg.id, "sender": self._sender_name(msg, kind, ename), "text": text}

    async def history(
        self,
        entity_id: int,
        *,
        limit: int = 30,
        before_id: Optional[int] = None,
        after_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        client = self._require_client()
        limit = max(1, min(int(limit), HISTORY_MAX))
        row = self.state.dialogs.find(entity_id) or {}
        kind = row.get("kind", "pv")
        ename = row.get("display_name", str(entity_id))

        kwargs: Dict[str, Any] = {"limit": limit}
        if before_id:
            kwargs["max_id"] = int(before_id)
        if after_id:  # live polling: only messages newer than what we have
            kwargs["min_id"] = int(after_id)

        messages = await self.state.throttle.tg_read(
            lambda: client.get_messages(int(entity_id), **kwargs)
        )
        items: List[Dict[str, Any]] = [self._format_message(m, kind, ename) for m in messages]

        # Batch-resolve reply previews for the whole page in ONE extra read.
        reply_ids = {
            getattr(m.reply_to, "reply_to_msg_id", None)
            for m in messages
            if getattr(m, "reply_to", None) is not None
        }
        reply_ids.discard(None)
        if reply_ids:
            try:
                replied = await self.state.throttle.tg_read(
                    lambda: client.get_messages(int(entity_id), ids=list(reply_ids))
                )
                rmap = {
                    r.id: self._reply_snippet(r, kind, ename)
                    for r in replied
                    if r is not None
                }
                for item, m in zip(items, messages):
                    rid = getattr(getattr(m, "reply_to", None), "reply_to_msg_id", None)
                    if rid in rmap:
                        item["reply"] = rmap[rid]
            except Exception as exc:  # noqa: BLE001 - reply preview is best-effort
                logger.debug("reply preview fetch failed for %s: %s", entity_id, exc)

        oldest_id = messages[-1].id if messages else None
        newest_id = messages[0].id if messages else None
        return {"ok": True, "items": items, "oldest_id": oldest_id, "newest_id": newest_id}

    async def messages_for_ai(self, entity_id: int, count: int) -> List[Dict[str, Any]]:
        """Chronological [{sender, text, timestamp}] for analyze/tellme."""
        client = self._require_client()
        count = max(1, min(int(count), 10000))
        row = self.state.dialogs.find(entity_id) or {}
        kind = row.get("kind", "pv")
        ename = row.get("display_name", str(entity_id))
        messages = await self.state.throttle.tg_read(
            lambda: client.get_messages(int(entity_id), limit=count)
        )
        out: List[Dict[str, Any]] = []
        for msg in reversed(messages):  # oldest -> newest
            if not (msg.message or "").strip():
                continue
            out.append(
                {
                    "sender": self._sender_name(msg, kind, ename),
                    "text": msg.message,
                    "timestamp": msg.date,
                }
            )
        return out

    # ---------- media enumeration ----------
    @staticmethod
    def _media_kind(msg: Any) -> Optional[str]:
        if getattr(msg, "photo", None):
            return "photo"
        if getattr(msg, "sticker", None):
            return "sticker"
        if getattr(msg, "gif", None):
            return "gif"
        if getattr(msg, "voice", None) or getattr(msg, "audio", None):
            return "audio"
        doc = getattr(msg, "document", None)
        if doc is not None:
            mime = (getattr(doc, "mime_type", "") or "").lower()
            if mime.startswith("video/"):
                return "video"
            if mime.startswith("audio/"):
                return "audio"
            if mime.startswith("image/"):
                return "photo"
            return "document"
        if getattr(msg, "video", None):
            return "video"
        return None

    @staticmethod
    def _sticker_meta(msg: Any) -> tuple[Optional[str], bool, bool]:
        """(sticker_format, is_animated, is_video) — pure, no RPC.

        tgs = gzipped Lottie (animated), webm = video sticker, webp = static.
        Telegram GIFs are delivered as muted mp4/webm video → is_video so the
        UI can autoplay them in a <video> loop."""
        fmt: Optional[str] = None
        is_animated = False
        is_video = False
        if getattr(msg, "sticker", None):
            doc = getattr(msg, "document", None)
            mime = (getattr(doc, "mime_type", "") or "").lower() if doc else ""
            if mime == "application/x-tgsticker":
                fmt, is_animated = "tgs", True
            elif mime == "video/webm":
                fmt, is_video = "webm", True
            else:
                fmt = "webp"
        elif getattr(msg, "gif", None):
            is_video = True
        return fmt, is_animated, is_video

    @staticmethod
    def _doc_meta(msg: Any) -> tuple[Optional[str], Optional[str]]:
        """(file_name, mime) for a message's document, if any — no RPC."""
        doc = getattr(msg, "document", None)
        if doc is None:
            return None, None
        file_name = None
        for attr in getattr(doc, "attributes", []) or []:
            if getattr(attr, "file_name", None):
                file_name = attr.file_name
        return file_name, getattr(doc, "mime_type", None)

    async def media(
        self,
        entity_id: int,
        *,
        kind: str = "all",
        limit: int = 24,
        before_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        client = self._require_client()
        limit = max(1, min(int(limit), MEDIA_MAX))
        # Telegram-style profile categories. "media" = photos+videos combined.
        flt = {
            "media": InputMessagesFilterPhotoVideo(),
            "photo": InputMessagesFilterPhotos(),
            "video": InputMessagesFilterVideo(),
            "document": InputMessagesFilterDocument(),
            "voice": InputMessagesFilterVoice(),
            "music": InputMessagesFilterMusic(),
            "gif": InputMessagesFilterGif(),
            "url": InputMessagesFilterUrl(),
        }.get(kind)

        kwargs: Dict[str, Any] = {"limit": limit}
        if flt is not None:
            kwargs["filter"] = flt
        if before_id:
            kwargs["max_id"] = int(before_id)

        messages = await self.state.throttle.tg_read(
            lambda: client.get_messages(int(entity_id), **kwargs)
        )
        items: List[Dict[str, Any]] = []
        for msg in messages:
            text = (getattr(msg, "message", "") or "").strip()
            # The Links tab lists messages that CONTAIN a URL (often no media).
            if kind == "url":
                if not text:
                    continue
                items.append({
                    "message_id": msg.id, "kind": "url", "text": text,
                    "file_name": None, "size": None, "mime": None, "has_thumb": False,
                    "timestamp": msg.date.isoformat() if msg.date else None,
                })
                continue
            mk = self._media_kind(msg)
            if mk is None:
                continue
            doc = getattr(msg, "document", None)
            file_name = None
            size = None
            mime = None
            if doc is not None:
                mime = getattr(doc, "mime_type", None)
                size = getattr(doc, "size", None)
                for attr in getattr(doc, "attributes", []) or []:
                    if getattr(attr, "file_name", None):
                        file_name = attr.file_name
            items.append(
                {
                    "message_id": msg.id,
                    "kind": mk,
                    "text": text,
                    "file_name": file_name,
                    "size": size,
                    "mime": mime,
                    "has_thumb": bool(getattr(msg, "photo", None) or doc),
                    "timestamp": msg.date.isoformat() if msg.date else None,
                }
            )
        oldest_id = messages[-1].id if messages else None
        return {"ok": True, "items": items, "oldest_id": oldest_id}

    # ---------- profile (detail + bio, cached) ----------
    async def profile(self, entity_id: int) -> Dict[str, Any]:
        """Detail plus the bio/about (one GetFull* RPC). Cached ~60s so
        reopening the profile drawer doesn't re-hit Telegram."""
        import time

        eid = int(entity_id)
        hit = self._profile_cache.get(eid)
        if hit and (time.monotonic() - hit[1]) < 60:
            return hit[0]

        data = await self.detail(eid)
        about = None
        client = self._require_client()
        try:
            from telethon.tl import functions

            entity = await self.state.throttle.tg_read(lambda: client.get_entity(eid))
            if data.get("kind") in ("group", "channel"):
                full = await self.state.throttle.tg_read(
                    lambda: client(functions.channels.GetFullChannelRequest(entity))
                )
                about = getattr(getattr(full, "full_chat", None), "about", None)
            else:
                full = await self.state.throttle.tg_read(
                    lambda: client(functions.users.GetFullUserRequest(entity))
                )
                about = getattr(getattr(full, "full_user", None), "about", None)
        except Exception as exc:  # noqa: BLE001 - bio is best-effort
            logger.warning("profile bio fetch failed for %s: %s", eid, exc)
        data["about"] = about or None
        self._profile_cache[eid] = (data, time.monotonic())
        return data

    # ---------- real profile photo (lazy + cached) ----------
    async def real_avatar_path(self, entity_id: int) -> Optional[str]:
        cache = self.state.media_cache
        path = cache.avatar_path(entity_id)
        if cache.is_fresh(path, AVATAR_TTL_SECONDS):
            return str(path)
        if cache.is_fresh(cache.avatar_sentinel(entity_id), AVATAR_TTL_SECONDS):
            return None  # known to have no photo

        client = self._require_client()
        try:
            entity = await self.state.throttle.tg_read(lambda: client.get_entity(int(entity_id)))
            result = await self.state.throttle.tg_read(
                lambda: client.download_profile_photo(entity, file=str(path)),
                kind="download",
            )
        except Exception as exc:  # noqa: BLE001 - avatar is best-effort
            logger.warning("avatar download failed for %s: %s", entity_id, exc)
            return None
        if result:
            return str(result)
        # No photo — write a sentinel to avoid re-downloading on every scroll.
        try:
            cache.avatar_sentinel(entity_id).write_text("1", encoding="utf-8")
        except OSError:
            pass
        return None

    # ---------- media download (file / thumb) ----------
    async def media_file(
        self, entity_id: int, message_id: int, *, thumb: bool = False
    ) -> Dict[str, Any]:
        client = self._require_client()
        cache = self.state.media_cache

        # Cache hit. Thumbs are a fixed path; full media has a Telethon-chosen
        # extension, so look it up via find_media (the old .bin check missed it).
        if thumb:
            cached = cache.thumb_path(entity_id, message_id)
            if cache.is_fresh(cached):
                return {"path": str(cached), "mime": self._guess_mime(cached)}
        else:
            hit = cache.find_media(entity_id, message_id)
            if hit:
                return {"path": str(hit), "mime": self._guess_mime(hit)}

        msg = await self.state.throttle.tg_read(
            lambda: client.get_messages(int(entity_id), ids=int(message_id))
        )
        if not msg or getattr(msg, "media", None) is None:
            raise PanelNotFound("No media on that message.")

        if thumb:
            out = await self.state.throttle.tg_read(
                lambda: client.download_media(msg, file=str(cache.thumb_path(entity_id, message_id)), thumb=-1),
                kind="download",
            )
        else:
            # No suffix → Telethon appends the correct one (.jpg/.tgs/.webm/...).
            base = cache.media_path(entity_id, message_id).with_suffix("")
            out = await self.state.throttle.tg_read(
                lambda: client.download_media(msg, file=str(base)),
                kind="download",
            )
        if not out:
            raise PanelNotFound("Could not download media.")
        return {"path": str(out), "mime": self._guess_mime(Path(out))}

    _MIME_OVERRIDES = {
        ".tgs": "application/gzip",       # gzipped Lottie sticker
        ".webm": "video/webm",
        ".webp": "image/webp",
        ".json": "application/json",
        ".oga": "audio/ogg",              # Telegram voice notes
        ".ogg": "audio/ogg",
    }

    @classmethod
    def _guess_mime(cls, path: Path) -> str:
        ext = path.suffix.lower()
        if ext in cls._MIME_OVERRIDES:
            return cls._MIME_OVERRIDES[ext]
        import mimetypes

        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"
