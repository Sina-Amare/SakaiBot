"""In-process pub/sub that fans Telegram updates to SSE clients.

The monitor_runtime tap (the panel's sole Telegram event-handler registrar)
feeds NORMALIZED dict events here; the /api/events SSE route subscribes and
streams them to the browser. Contains NO Telegram API calls and never blocks
the asyncio loop: publish is non-blocking and drops the oldest event for a slow
subscriber rather than growing memory.

Routing: typing + new-message events go only to subscribers with THAT chat
open; presence broadcasts to everyone (so the chat list / header can update).
"""

import asyncio
from typing import Any, Dict, Optional, Set

QUEUE_MAX = 100  # per-subscriber backlog before we drop the oldest event


class Subscriber:
    __slots__ = ("queue", "entity_id")

    def __init__(self, entity_id: Optional[int]) -> None:
        self.queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=QUEUE_MAX)
        self.entity_id = entity_id


class EventHub:
    def __init__(self) -> None:
        self._subs: Set[Subscriber] = set()

    def subscribe(self, entity_id: Optional[int] = None) -> Subscriber:
        sub = Subscriber(entity_id)
        self._subs.add(sub)
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        self._subs.discard(sub)

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)

    def publish(self, event: Dict[str, Any]) -> None:
        """Route an event to the relevant subscribers. Non-blocking."""
        etype = event.get("type")
        eid = event.get("entity_id")
        for sub in list(self._subs):
            if etype in ("typing", "message") and sub.entity_id != eid:
                continue
            self._offer(sub, event)

    @staticmethod
    def _offer(sub: Subscriber, event: Dict[str, Any]) -> None:
        try:
            sub.queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                sub.queue.get_nowait()       # drop oldest, keep the stream live
                sub.queue.put_nowait(event)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
