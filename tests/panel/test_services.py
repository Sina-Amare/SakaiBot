"""Service-layer tests (offline) — exercise real services with mock client/AI."""

import pytest


@pytest.mark.asyncio
async def test_dialogs_classification(panel_state):
    data = await panel_state.dialogs.list_dialogs()
    by_kind = {item["kind"]: item for item in data["items"]}
    assert by_kind["pv"]["id"] == 101
    assert by_kind["bot"]["id"] == 102
    assert by_kind["group"]["id"] == 201
    assert by_kind["channel"]["id"] == 202


@pytest.mark.asyncio
async def test_dialogs_cached(panel_state, mock_client):
    await panel_state.dialogs.list_dialogs()
    first_calls = mock_client.iter_dialogs.call_count
    await panel_state.dialogs.list_dialogs(kind="pv")
    # Second call served from cache (no extra Telegram walk).
    assert mock_client.iter_dialogs.call_count == first_calls


@pytest.mark.asyncio
async def test_prompt_renders_text(panel_state):
    out = await panel_state.commands.run_prompt("Explain gravity simply")
    assert out["kind"] == "text"
    assert "PROMPT_RESULT" in out["html"]
    assert out["meta"]["model"] == "gemini-test-pro"


@pytest.mark.asyncio
async def test_analyze_uses_history(panel_state, mock_client):
    out = await panel_state.commands.run_analyze(201, count=5, language="english")
    assert "ANALYZE_RESULT" in out["html"]
    panel_state.ai_processor.analyze_conversation_messages.assert_awaited()
    # It read history but never sent.
    mock_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_translate(panel_state):
    out = await panel_state.commands.run_translate("hello", "fa")
    assert "TRANSLATION_RESULT" in out["html"]


@pytest.mark.asyncio
async def test_image_returns_media_url(panel_state):
    out = await panel_state.commands.run_image("flux", "a sunset")
    assert out["kind"] == "image"
    assert out["media_url"].startswith("/api/cmd/result-media/")
    token = out["media_url"].rsplit("/", 1)[-1]
    assert token in panel_state.result_tokens


@pytest.mark.asyncio
async def test_tts_returns_audio_url(panel_state):
    out = await panel_state.commands.run_tts("hello there")
    assert out["kind"] == "audio"
    assert out["media_url"].startswith("/api/cmd/result-media/")


@pytest.mark.asyncio
async def test_stt_transcribes(panel_state, mock_client):
    out = await panel_state.commands.run_stt(201, 7)
    assert out["kind"] == "text"
    assert out["text"] == "TRANSCRIBED TEXT"
    mock_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_auth_add(panel_state):
    out = await panel_state.auth.add("@newuser")
    assert out["added"]["id"] == 555
    panel_state.settings_manager.save_user_settings.assert_called()
    saved = panel_state.settings_manager.save_user_settings.call_args[0][0]
    assert 555 in saved["directly_authorized_pvs"]


def test_auth_remove(panel_state):
    out = panel_state.auth.remove(101)
    assert out["removed"] == 101
    panel_state.settings_manager.save_user_settings.assert_called()


def test_keys_and_models(panel_state):
    keys = panel_state.status.keys()
    names = {p["name"] for p in keys["providers"]}
    assert {"gemini", "openrouter"} <= names
    models = panel_state.status.models()
    assert models["tasks"]["analyze"] == "gemini-test-pro"
