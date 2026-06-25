"""Messenger service: the ONE place the panel writes to Telegram.

Aigram is an AI-powered Telegram client, so the composer must be able to send.
This is the single, deliberate exception to the panel's otherwise read-only
posture — it is excluded from ``tests/panel/test_no_send.py``'s static guard the
same way ``monitor_runtime.py`` is. Every send here is an *explicit, user-initiated*
action from the chat composer (never automation), goes through the ban-safety
throttle (pacing + FloodWait handling), and is length-capped.
"""

from typing import Any, Dict, Optional

from ...utils.logging import get_logger
from ..errors import PanelError, PanelUnavailable

logger = get_logger(__name__)

MAX_LEN = 4096  # Telegram's single-message text limit


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
