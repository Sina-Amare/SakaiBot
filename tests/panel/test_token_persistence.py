"""The panel access token must be STABLE across restarts.

An installed PWA saves the token in localStorage and reuses it on launch; if the
panel minted a fresh token every run the home-screen app would log out on every
restart. resolve_panel_token persists a generated token to .env so it survives.
"""

import os

import pytest

from src.panel.config import resolve_panel_token, rotate_panel_token
from src.panel.env_writer import EnvWriter


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("PANEL_TOKEN", raising=False)
    yield
    # resolve/rotate set os.environ directly (not via monkeypatch) — clean up.
    os.environ.pop("PANEL_TOKEN", None)


def _writer(tmp_path) -> EnvWriter:
    return EnvWriter(path=tmp_path / ".env")


def test_explicit_env_token_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("PANEL_TOKEN", "explicit-123")
    w = _writer(tmp_path)
    assert resolve_panel_token(w) == "explicit-123"
    # An explicitly-provided env token is honored as-is, never persisted.
    assert "PANEL_TOKEN" not in w.read()


def test_generates_persists_and_is_stable(tmp_path, clean_env, monkeypatch):
    w = _writer(tmp_path)
    t1 = resolve_panel_token(w)
    assert t1 and len(t1) > 20
    assert w.read().get("PANEL_TOKEN") == t1       # persisted to .env
    assert os.environ.get("PANEL_TOKEN") == t1     # exported for PanelConfig.from_env

    # Simulate a restart: env cleared, but the saved token is reused (stable).
    monkeypatch.delenv("PANEL_TOKEN", raising=False)
    t2 = resolve_panel_token(w)
    assert t2 == t1


def test_rotate_changes_and_persists(tmp_path, clean_env, monkeypatch):
    w = _writer(tmp_path)
    t1 = resolve_panel_token(w)
    monkeypatch.delenv("PANEL_TOKEN", raising=False)
    t2 = rotate_panel_token(w)
    assert t2 != t1
    assert w.read().get("PANEL_TOKEN") == t2
