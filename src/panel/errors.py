"""Panel error types mapped to JSON envelopes for the SPA."""

from typing import Any, Dict, Optional


class PanelError(Exception):
    """Base panel error carrying an HTTP status and a user-safe message."""

    status_code: int = 400

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"ok": False, "error": self.message}
        if self.retry_after is not None:
            body["retry_after"] = self.retry_after
        return body


class PanelFloodError(PanelError):
    """Telegram asked us to wait longer than we're willing to block."""

    def __init__(self, seconds: int) -> None:
        super().__init__(
            f"Telegram is rate-limiting this account. Try again in ~{seconds}s.",
            status_code=429,
            retry_after=seconds,
        )


class PanelUnavailable(PanelError):
    """The live Telegram client is not available (bot/panel not connected)."""

    def __init__(
        self, message: str = "Telegram client not available (bot not running)."
    ) -> None:
        super().__init__(message, status_code=503)


class PanelNotFound(PanelError):
    def __init__(self, message: str = "Not found.") -> None:
        super().__init__(message, status_code=404)
