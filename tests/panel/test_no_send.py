"""THE critical invariant: the panel web layer never sends to Telegram.

Two checks:
1. Static guard — forbidden Telegram write identifiers must not appear in the
   panel service/web layer source (monitor_runtime.py is the deliberate, allowed
   bot-monitoring bridge and is excluded).
2. Runtime guard — drive every endpoint and assert the mock client's write
   methods are never called.
"""

from pathlib import Path

import pytest

from .conftest import FORBIDDEN_CLIENT_CALLS

PANEL_DIR = Path(__file__).resolve().parents[2] / "src" / "panel"

# Files allowed to reference event-handler registration (the monitoring bridge).
EXCLUDED = {"monitor_runtime.py"}

FORBIDDEN_TOKENS = [
    "send_message",
    "send_file",
    "forward_messages",
    "edit_message",
    "delete_messages",
    "send_read_acknowledge",
    "add_event_handler",
]


def _scanned_files():
    for path in PANEL_DIR.rglob("*.py"):
        if path.name in EXCLUDED:
            continue
        yield path


def test_static_no_send_guard():
    offenders = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                offenders.append(f"{path.name}: {token}")
    assert not offenders, (
        "Panel web layer must never reference Telegram write APIs: " + ", ".join(offenders)
    )


def test_monitor_runtime_is_the_only_handler_registrar():
    # Sanity: the one allowed file does use add_event_handler (so the exclusion
    # is meaningful, not hiding a real leak elsewhere).
    mr = (PANEL_DIR / "monitor_runtime.py").read_text(encoding="utf-8")
    assert "add_event_handler" in mr


ALL_ENDPOINT_CALLS = [
    ("GET", "/api/status", None),
    ("GET", "/api/keys", None),
    ("GET", "/api/models", None),
    ("GET", "/api/help", None),
    ("GET", "/api/dialogs", None),
    ("POST", "/api/dialogs/refresh", {}),
    ("GET", "/api/entity/101", None),
    ("GET", "/api/entity/101/history", None),
    ("GET", "/api/entity/201/media", None),
    ("GET", "/api/auth", None),
    ("POST", "/api/cmd/prompt", {"text": "Explain gravity simply"}),
    ("POST", "/api/cmd/translate", {"text": "hello", "target_lang": "fa"}),
    ("POST", "/api/cmd/analyze", {"entity_id": 201, "count": 5, "mode": "general", "language": "english"}),
    ("POST", "/api/cmd/tellme", {"entity_id": 201, "count": 5, "question": "what?"}),
    ("POST", "/api/cmd/image", {"model": "flux", "prompt": "a cat"}),
    ("POST", "/api/cmd/tts", {"text": "hello there"}),
    ("POST", "/api/cmd/stt", {"entity_id": 201, "message_id": 7}),
    ("POST", "/api/auth", {"identifier": "@newuser"}),
    ("DELETE", "/api/auth/101", None),
]


def test_runtime_never_sends_to_chat(client, mock_client, auth_headers):
    for method, path, body in ALL_ENDPOINT_CALLS:
        resp = client.request(method, path, json=body, headers=auth_headers)
        # We only assert the no-send invariant here; any 2xx/4xx is fine.
        assert resp.status_code < 500, f"{method} {path} -> {resp.status_code}: {resp.text}"

    for name in FORBIDDEN_CLIENT_CALLS:
        getattr(mock_client, name).assert_not_called()
