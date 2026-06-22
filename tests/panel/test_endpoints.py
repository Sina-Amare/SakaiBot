"""FastAPI endpoint tests (offline) — auth, shapes, content-types, degraded."""

import pytest
from starlette.testclient import TestClient

from src.panel.app import create_app
from src.panel.config import PanelConfig

from .conftest import TOKEN, build_state


def test_health_is_open(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["panel"] == "up"
    assert body["client"] == "connected"


def test_requires_token(client):
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_status_shape(client, auth_headers):
    r = client.get("/api/status", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["client"] == "connected"
    assert body["account"]["name"] == "Owner"
    assert body["provider"] == "gemini"


def test_dialogs_classification_and_counts(client, auth_headers):
    r = client.get("/api/dialogs", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    kinds = sorted(item["kind"] for item in body["items"])
    assert kinds == ["bot", "channel", "group", "pv"]
    assert body["counts"]["pv"] == 1
    assert body["counts"]["channel"] == 1
    assert body["counts"]["bot"] == 1
    assert body["counts"]["group"] == 1


def test_dialogs_filter_channel_only(client, auth_headers):
    r = client.get("/api/dialogs?type=channel", headers=auth_headers)
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["kind"] == "channel"


def test_dialogs_search(client, auth_headers):
    r = client.get("/api/dialogs?q=alice", headers=auth_headers)
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["id"] == 101


def test_avatar_initials_is_svg(client, auth_headers):
    r = client.get(f"/api/avatar/101?t={TOKEN}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in r.content


def test_loopback_guard_rejects_non_local():
    with pytest.raises(ValueError):
        PanelConfig(host="0.0.0.0")


def test_image_result_media_streams_png(client, auth_headers):
    r = client.post("/api/cmd/image", json={"model": "flux", "prompt": "a cat"}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "image"
    media = client.get(body["media_url"] + f"?t={TOKEN}")
    assert media.status_code == 200
    assert media.headers["content-type"] == "image/png"


def test_degraded_mode_when_no_client(tmp_path):
    state = build_state(tmp_path, client=None)
    app = create_app(state)
    c = TestClient(app)
    # health reports degraded
    assert c.get("/api/health").json()["client"] == "degraded"
    # status still answers (cache-only) but marks degraded
    s = c.get("/api/status", headers={"Authorization": f"Bearer {TOKEN}"})
    assert s.status_code == 200 and s.json()["client"] == "degraded"
    # live dialog walk is unavailable
    d = c.get("/api/dialogs", headers={"Authorization": f"Bearer {TOKEN}"})
    assert d.status_code == 503
