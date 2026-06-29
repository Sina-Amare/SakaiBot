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


def test_media_download_forces_attachment_for_docs(client, panel_state):
    """Untrusted Telegram docs (e.g. HTML) must download, not render inline."""
    mc = panel_state.media_cache
    mc.media.mkdir(parents=True, exist_ok=True)
    (mc.media / "101_5.html").write_bytes(b"<h1>hi</h1>")
    r = client.get(f"/api/entity/101/media/5/file?t={TOKEN}")
    assert r.status_code == 200
    assert r.headers.get("content-disposition", "").startswith("attachment")


def test_media_download_inline_for_images(client, panel_state):
    """Plain images stay inline (no forced download) so chat thumbnails work."""
    mc = panel_state.media_cache
    mc.media.mkdir(parents=True, exist_ok=True)
    (mc.media / "101_6.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")
    r = client.get(f"/api/entity/101/media/6/file?t={TOKEN}")
    assert r.status_code == 200
    assert "attachment" not in r.headers.get("content-disposition", "")


def test_send_file_route_rejects_oversize(client, auth_headers, monkeypatch):
    """The upload route caps body size during read (not just in the service)."""
    import src.panel.services.messenger_service as ms

    monkeypatch.setattr(ms, "MAX_FILE_BYTES", 1024)
    r = client.post(
        "/api/entity/101/send-file",
        files={"file": ("big.bin", b"x" * 4096, "application/octet-stream")},
        headers=auth_headers,
    )
    assert r.status_code == 413


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
