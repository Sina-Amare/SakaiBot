"""Messenger service: the ONE place the panel writes to Telegram.

Aigram is an AI-powered Telegram client, so the composer must be able to send.
This is the single, deliberate exception to the panel's otherwise read-only
posture — it is excluded from ``tests/panel/test_no_send.py``'s static guard the
same way ``monitor_runtime.py`` is. Every send here is an *explicit, user-initiated*
action from the chat composer (never automation), goes through the ban-safety
throttle (pacing + FloodWait handling), and is length-capped.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from ...utils.logging import get_logger
from ..errors import PanelError, PanelUnavailable

logger = get_logger(__name__)

MAX_LEN = 4096  # Telegram's single-message text limit
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB upload cap (keeps sends ban-safe)


class MessengerService:
    def __init__(self, state: Any) -> None:
        self.state = state

    def _require_client(self):
        if self.state.client is None:
            raise PanelUnavailable()
        return self.state.client

    async def send_text(
        self, entity_id: int, text: str, reply_to: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send a text message (optionally as a reply) and echo it back shaped
        exactly like a history item, so the UI can swap its optimistic bubble."""
        client = self._require_client()
        text = (text or "").strip()
        if not text:
            raise PanelError("Message is empty.")
        if len(text) > MAX_LEN:
            raise PanelError(f"Message too long (max {MAX_LEN} characters).")
        rt = int(reply_to) if reply_to else None

        sent = await self.state.throttle.tg_write(
            lambda: client.send_message(int(entity_id), text, reply_to=rt)
        )

        row = self.state.dialogs.find(int(entity_id)) or {}
        kind = row.get("kind", "pv")
        ename = row.get("display_name", str(entity_id))
        message = self.state.entity._format_message(sent, kind, ename)
        logger.info("panel send -> entity %s (%d chars)", entity_id, len(text))
        return {"ok": True, "message": message}

    async def send_attachment(
        self,
        entity_id: int,
        upload: bytes,
        file_name: str,
        caption: Optional[str] = None,
        reply_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a user-provided file (with optional caption) and echo it back.

        Telethon auto-detects type (images go as photos), so a pasted image
        arrives as a photo. The file is staged in a temp dir under the media
        cache so its real name is preserved, then removed after the send."""
        client = self._require_client()
        if not upload:
            raise PanelError("Empty file.")
        if len(upload) > MAX_FILE_BYTES:
            raise PanelError(f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).")
        caption = (caption or "").strip()
        if len(caption) > MAX_LEN:
            raise PanelError(f"Caption too long (max {MAX_LEN} characters).")
        rt = int(reply_to) if reply_to else None
        safe_name = Path(file_name or "file").name or "file"  # strip path components

        uploads = self.state.media_cache.root / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(dir=str(uploads)))
        path = staging / safe_name
        try:
            path.write_bytes(upload)
            sent = await self.state.throttle.tg_write(
                lambda: client.send_file(
                    int(entity_id), file=str(path),
                    caption=caption or None, reply_to=rt, force_document=False,
                )
            )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        row = self.state.dialogs.find(int(entity_id)) or {}
        kind = row.get("kind", "pv")
        ename = row.get("display_name", str(entity_id))
        message = self.state.entity._format_message(sent, kind, ename)
        logger.info("panel send_file -> entity %s (%s, %d bytes)", entity_id, safe_name, len(upload))
        return {"ok": True, "message": message}

    async def edit_text(
        self, entity_id: int, message_id: int, text: str
    ) -> Dict[str, Any]:
        """Edit one of the user's own messages; echo the updated message back."""
        client = self._require_client()
        text = (text or "").strip()
        if not text:
            raise PanelError("Message is empty.")
        if len(text) > MAX_LEN:
            raise PanelError(f"Message too long (max {MAX_LEN} characters).")

        edited = await self.state.throttle.tg_write(
            lambda: client.edit_message(int(entity_id), int(message_id), text)
        )
        logger.info("panel edit -> entity %s msg %s", entity_id, message_id)
        if edited is None or not hasattr(edited, "id"):
            # Telethon can return a non-message for some edits; succeed quietly.
            return {"ok": True}
        row = self.state.dialogs.find(int(entity_id)) or {}
        message = self.state.entity._format_message(
            edited, row.get("kind", "pv"), row.get("display_name", str(entity_id))
        )
        return {"ok": True, "message": message}

    async def forward_message(
        self, from_entity_id: int, message_id: int, to_entity_id: int
    ) -> Dict[str, Any]:
        """Forward a message from the open chat to another chat the user picks."""
        client = self._require_client()
        await self.state.throttle.tg_write(
            lambda: client.forward_messages(
                int(to_entity_id), int(message_id), int(from_entity_id)
            )
        )
        row = self.state.dialogs.find(int(to_entity_id)) or {}
        target = row.get("display_name", str(to_entity_id))
        logger.info(
            "panel forward -> from %s msg %s to %s", from_entity_id, message_id, to_entity_id
        )
        return {"ok": True, "target": target}

    async def delete_message(self, entity_id: int, message_id: int) -> Dict[str, Any]:
        """Delete one of the user's own messages for everyone (revoke)."""
        client = self._require_client()
        await self.state.throttle.tg_write(
            lambda: client.delete_messages(int(entity_id), [int(message_id)], revoke=True)
        )
        logger.info("panel delete -> entity %s msg %s", entity_id, message_id)
        return {"ok": True, "deleted": int(message_id)}
