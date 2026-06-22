"""Ban-safety chokepoint.

EVERY Telegram read the panel performs goes through ``Throttle.tg_read`` so the
account is never hammered. This mirrors the proven FloodWait handling in
``src/utils/message_sender.py`` (sleep ``e.seconds + 1``) but is tuned for an
interactive, read-only panel: one retry, and a hard cap above which we surface
the wait to the UI instead of blocking.
"""

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

from telethon.errors import FloodWaitError

from ..utils.logging import get_logger
from .errors import PanelFloodError

logger = get_logger(__name__)

# Above this many seconds we do NOT sleep — a human is waiting on the panel.
FLOOD_HARD_CAP_SECONDS = 120

T = TypeVar("T")


class Throttle:
    """Concurrency caps + pacing + FloodWait handling for Telegram reads."""

    def __init__(
        self,
        max_concurrent_rpc: int = 3,
        max_concurrent_downloads: int = 2,
        min_gap_seconds: float = 0.35,
    ) -> None:
        self._rpc = asyncio.Semaphore(max_concurrent_rpc)
        self._downloads = asyncio.Semaphore(max_concurrent_downloads)
        self._min_gap = min_gap_seconds
        self._pace_lock = asyncio.Lock()
        self._last_start = 0.0

    async def _pace(self) -> None:
        async with self._pace_lock:
            now = time.monotonic()
            wait = self._min_gap - (now - self._last_start)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_start = time.monotonic()

    async def tg_read(
        self,
        coro_factory: Callable[[], Awaitable[T]],
        *,
        kind: str = "rpc",
    ) -> T:
        """Run a Telegram read coroutine under concurrency + FloodWait control.

        Args:
            coro_factory: zero-arg callable returning a fresh awaitable each call
                (so we can retry it once after a short FloodWait).
            kind: "rpc" (default) or "download" — selects which semaphore caps it.
        """
        sem = self._downloads if kind == "download" else self._rpc
        async with sem:
            await self._pace()
            try:
                return await coro_factory()
            except FloodWaitError as exc:
                seconds = int(getattr(exc, "seconds", 0) or 0)
                if seconds > FLOOD_HARD_CAP_SECONDS:
                    logger.warning(
                        "FloodWait %ss exceeds hard cap; surfacing to UI", seconds
                    )
                    raise PanelFloodError(seconds)
                logger.warning("FloodWait %ss; sleeping once then retrying", seconds)
                await asyncio.sleep(seconds + 1)
                return await coro_factory()
