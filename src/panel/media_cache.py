"""Disk cache for avatars / media / generated results.

Aggressive caching is a ban-safety measure: re-viewing a chat or avatar must
not re-hit Telegram. Files live under ``cache/panel`` (gitignored area).
"""

import time
from pathlib import Path
from typing import Optional

CACHE_ROOT = Path("cache/panel")

AVATAR_TTL_SECONDS = 24 * 3600  # profile photos rarely change


class MediaCache:
    """Thin path manager + freshness checks for cached binary assets."""

    def __init__(self, root: Path = CACHE_ROOT) -> None:
        self.root = Path(root)
        self.avatars = self.root / "avatars"
        self.media = self.root / "media"
        self.results = self.root / "results"
        for d in (self.avatars, self.media, self.results):
            d.mkdir(parents=True, exist_ok=True)

    # --- avatars ---
    def avatar_path(self, entity_id: int) -> Path:
        return self.avatars / f"{entity_id}.jpg"

    def avatar_sentinel(self, entity_id: int) -> Path:
        # Written when an entity has no photo, so we don't retry on every scroll.
        return self.avatars / f"{entity_id}.nophoto"

    # --- chat media ---
    def media_path(self, entity_id: int, message_id: int, suffix: str = ".bin") -> Path:
        return self.media / f"{entity_id}_{message_id}{suffix}"

    def thumb_path(self, entity_id: int, message_id: int) -> Path:
        return self.media / f"{entity_id}_{message_id}.thumb.jpg"

    def find_media(self, entity_id: int, message_id: int) -> Optional[Path]:
        """The real cached media file. Telethon picks the extension at download
        time (e.g. .jpg/.tgs/.webm), so glob for ``{e}_{m}.<ext>`` — excluding
        the ``.thumb.jpg`` companion. Fixes a cache-miss where the freshness
        check looked at a ``.bin`` path that was never actually written."""
        stem = f"{entity_id}_{message_id}"
        for p in self.media.glob(stem + ".*"):
            if p.name.endswith(".thumb.jpg"):
                continue
            if self.is_fresh(p):
                return p
        return None

    @staticmethod
    def is_fresh(path: Path, ttl_seconds: Optional[float] = None) -> bool:
        try:
            if not path.exists():
                return False
            if ttl_seconds is None:
                return True
            return (time.time() - path.stat().st_mtime) < ttl_seconds
        except OSError:
            return False
