"""Offline tests for the first-run onboarding flow (Telethon login mocked)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.panel.errors import PanelError


def _fake_client(authorized=False, code_side_effect=None):
    c = MagicMock()
    c.connect = AsyncMock()
    c.is_user_authorized = AsyncMock(return_value=authorized)
    c.send_code_request = AsyncMock(return_value=SimpleNamespace(phone_code_hash="HASH"))
    c.sign_in = AsyncMock(side_effect=code_side_effect)
    c.disconnect = AsyncMock()
    return c


def _patch_client(monkeypatch, fake):
    import telethon
    monkeypatch.setattr(telethon, "TelegramClient", MagicMock(return_value=fake))


@pytest.mark.asyncio
async def test_onboarding_happy_path(panel_state, monkeypatch):
    _patch_client(monkeypatch, _fake_client())
    ob = panel_state.onboarding
    r = await ob.start(12345678, "abcdef1234567890", "+15551234567")
    assert r.get("code_sent")
    assert (await ob.submit_code("11111")).get("authorized")
    assert (await ob.finalize({"provider": "gemini", "keys": ["G" * 20]})).get("done")
    upd = panel_state.env_writer.set_many.call_args[0][0]
    assert upd["TELEGRAM_API_ID"] == "12345678"
    assert upd["TELEGRAM_API_HASH"] == "abcdef1234567890"
    assert upd["LLM_PROVIDER"] == "gemini"
    assert upd["GEMINI_API_KEY_1"] == "G" * 20


@pytest.mark.asyncio
async def test_onboarding_two_factor(panel_state, monkeypatch):
    from telethon.errors import SessionPasswordNeededError

    exc = SessionPasswordNeededError.__new__(SessionPasswordNeededError)
    fake = _fake_client(code_side_effect=[exc, None])  # code -> needs pw, pw -> ok
    _patch_client(monkeypatch, fake)
    ob = panel_state.onboarding
    await ob.start(1, "abcdef1234567890", "+1555")
    assert (await ob.submit_code("123")).get("needs_password")
    assert (await ob.submit_password("hunter2")).get("authorized")


@pytest.mark.asyncio
async def test_onboarding_validation(panel_state):
    ob = panel_state.onboarding
    with pytest.raises(PanelError):
        await ob.start("not-a-number", "abcdef1234567890", "+1555")
    with pytest.raises(PanelError):
        await ob.start(1, "short", "+1555")        # bad hash
    with pytest.raises(PanelError):
        await ob.start(1, "abcdef1234567890", "0912")  # no country code
    with pytest.raises(PanelError):
        await ob.finalize({})                       # not authorized yet


def test_onboarding_status_not_needed_when_connected(panel_state):
    # panel_state has a connected mock client → no setup needed
    assert panel_state.onboarding.status()["needs_setup"] is False
