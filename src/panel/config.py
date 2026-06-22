"""Panel configuration. The panel is loopback-only by hard rule."""

import os
import secrets
from dataclasses import dataclass
from typing import Optional

# A userbot control panel can drive a real account. It must never be reachable
# off the local machine, so we hard-refuse any non-loopback bind address.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

DEFAULT_PORT = 8765


@dataclass
class PanelConfig:
    """Runtime config for the web panel."""

    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    token: str = ""
    # When False (default) avatars are colored initials only (zero Telegram
    # API calls). When True, real profile photos are fetched lazily, throttled
    # and disk-cached — opt-in to keep the account ban-safe.
    real_photos: bool = False
    # When False, the panel runs as a pure private console (no Telegram event
    # handlers). When True (default for `sakaibot panel`), the bot also stays
    # live in chats.
    with_monitoring: bool = True

    def __post_init__(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            raise ValueError(
                f"Panel host must be loopback (one of {sorted(_LOOPBACK_HOSTS)}), "
                f"got '{self.host}'. Refusing to expose a userbot control panel "
                f"to a non-local address."
            )
        if not self.token:
            # Generated per run and printed once to the console.
            self.token = secrets.token_urlsafe(32)

    @classmethod
    def from_env(
        cls,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        real_photos: Optional[bool] = None,
        with_monitoring: Optional[bool] = None,
    ) -> "PanelConfig":
        """Build config from CLI overrides falling back to env vars."""
        resolved_host = host or os.environ.get("PANEL_HOST", "127.0.0.1")
        resolved_port = int(port or os.environ.get("PANEL_PORT", str(DEFAULT_PORT)))
        token = os.environ.get("PANEL_TOKEN", "") or ""
        if real_photos is None:
            real_photos = os.environ.get("PANEL_REAL_PHOTOS", "0") == "1"
        if with_monitoring is None:
            with_monitoring = os.environ.get("PANEL_WITH_MONITORING", "1") != "0"
        return cls(
            host=resolved_host,
            port=resolved_port,
            token=token,
            real_photos=bool(real_photos),
            with_monitoring=bool(with_monitoring),
        )
