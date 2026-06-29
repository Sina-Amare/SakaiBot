"""EventHub (SSE fan-out) contract: routing + bounded backlog + route auth."""

from src.panel.events import QUEUE_MAX, EventHub


def test_subscribe_unsubscribe():
    hub = EventHub()
    s = hub.subscribe(5)
    assert hub.subscriber_count == 1
    hub.unsubscribe(s)
    assert hub.subscriber_count == 0


def test_message_and_typing_route_only_to_open_chat():
    hub = EventHub()
    a, b = hub.subscribe(5), hub.subscribe(9)
    hub.publish({"type": "message", "entity_id": 5, "message": {"id": 1}})
    hub.publish({"type": "typing", "entity_id": 5})
    assert a.queue.qsize() == 2
    assert b.queue.qsize() == 0  # different chat open → not delivered


def test_presence_broadcasts_to_all():
    hub = EventHub()
    a, b = hub.subscribe(5), hub.subscribe(9)
    hub.publish({"type": "presence", "entity_id": 5, "presence": {"state": "online"}})
    assert a.queue.qsize() == 1 and b.queue.qsize() == 1


def test_bounded_queue_drops_oldest():
    hub = EventHub()
    s = hub.subscribe(5)
    for i in range(QUEUE_MAX + 25):
        hub.publish({"type": "presence", "entity_id": 5, "i": i})
    assert s.queue.qsize() == QUEUE_MAX  # never grows unbounded


def test_events_route_requires_token(client):
    # Dependency rejects before any streaming starts, so this returns promptly.
    resp = client.get("/api/events")
    assert resp.status_code == 401
