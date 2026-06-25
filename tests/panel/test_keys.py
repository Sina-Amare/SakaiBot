"""Offline tests for provider key management + atomic .env writes."""

from unittest.mock import AsyncMock

import pytest

from src.panel.env_writer import EnvWriter
from src.panel.errors import PanelError


def test_env_writer_atomic_and_comment_preserving(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# my config\nTELEGRAM_API_ID=123\nGEMINI_API_KEY_1=old\n", encoding="utf-8")
    w = EnvWriter(p)
    w.set_many({"GEMINI_API_KEY_1": "newkey", "GEMINI_API_KEY_2": "second"})
    txt = p.read_text(encoding="utf-8")
    assert "# my config" in txt                 # comment preserved
    assert "TELEGRAM_API_ID=123" in txt          # untouched key preserved
    assert "GEMINI_API_KEY_1=newkey" in txt       # replaced
    assert "GEMINI_API_KEY_2=second" in txt       # appended
    assert (tmp_path / ".env.bak").exists()       # backup written
    # removal
    w.set_many({"GEMINI_API_KEY_2": None})
    assert "GEMINI_API_KEY_2" not in p.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_list_keys_masked(panel_state):
    d = panel_state.keys.list_keys()
    g = next(p for p in d["providers"] if p["provider"] == "gemini")
    assert g["is_primary"] is True
    masked = g["slots"][0]["masked"]
    assert masked and masked != "k1value123"      # masked, not raw
    assert g["slots"][2]["present"] is False        # slot 3 empty
    assert d["primary"] == "gemini"


@pytest.mark.asyncio
async def test_add_key_uses_first_empty_slot(panel_state, monkeypatch):
    monkeypatch.setattr(panel_state.keys, "reload_ai", AsyncMock())
    await panel_state.keys.add_key("gemini", "X" * 20)
    panel_state.env_writer.set_many.assert_called_once()
    assert panel_state.env_writer.set_many.call_args[0][0] == {"GEMINI_API_KEY_3": "X" * 20}
    panel_state.keys.reload_ai.assert_awaited()


@pytest.mark.asyncio
async def test_remove_key(panel_state, monkeypatch):
    monkeypatch.setattr(panel_state.keys, "reload_ai", AsyncMock())
    await panel_state.keys.remove_key("gemini", 1)
    assert panel_state.env_writer.set_many.call_args[0][0] == {"GEMINI_API_KEY_1": None}


@pytest.mark.asyncio
async def test_set_provider(panel_state, monkeypatch):
    monkeypatch.setattr(panel_state.keys, "reload_ai", AsyncMock())
    await panel_state.keys.set_provider("openrouter", "none")
    upd = panel_state.env_writer.set_many.call_args[0][0]
    assert upd["LLM_PROVIDER"] == "openrouter"
    assert upd["LLM_FALLBACK_PROVIDER"] == "none"


@pytest.mark.asyncio
async def test_set_models_allowlisted(panel_state, monkeypatch):
    monkeypatch.setattr(panel_state.keys, "reload_ai", AsyncMock())
    await panel_state.keys.set_models({"GEMINI_MODEL_ANALYZE": "gemini-x"})
    assert panel_state.env_writer.set_many.call_args[0][0] == {"GEMINI_MODEL_ANALYZE": "gemini-x"}
    with pytest.raises(PanelError):
        await panel_state.keys.set_models({"SOME_RANDOM_ENV": "x"})


@pytest.mark.asyncio
async def test_test_key_rejects_unknown_provider(panel_state):
    with pytest.raises(PanelError):
        await panel_state.keys.test_key("anthropic", key="x" * 20)


@pytest.mark.asyncio
async def test_add_key_rejects_short(panel_state, monkeypatch):
    monkeypatch.setattr(panel_state.keys, "reload_ai", AsyncMock())
    with pytest.raises(PanelError):
        await panel_state.keys.add_key("gemini", "short")
