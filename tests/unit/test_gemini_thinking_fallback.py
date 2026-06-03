"""Unit tests for Gemini thinking/model fallback behavior."""

from types import SimpleNamespace

import pytest

from src.ai.providers.gemini import GeminiProvider
from src.ai.response_metadata import AIResponseMetadata
from src.core.exceptions import AIProcessorError


@pytest.fixture
def gemini_config():
    """Minimal Gemini config for provider unit tests."""
    return SimpleNamespace(
        gemini_api_keys=["test-key-1", "test-key-2"],
        gemini_api_key=None,
        gemini_model="gemini-default",
        gemini_model_pro="gemini-2.5-flash",
        gemini_model_flash="gemini-3.1-flash-lite",
        gemini_model_pro_fallback=None,
    )


@pytest.mark.asyncio
async def test_execute_prompt_retries_thinking_request_with_flash_after_pro_exhaustion(
    gemini_config, monkeypatch
):
    """Pro quota exhaustion retries the same thinking request on Flash."""
    provider = GeminiProvider(gemini_config)
    calls = []

    async def fake_execute_prompt_internal(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            provider._mark_pro_model_exhausted()
            raise AIProcessorError("RETRY_WITH_FLASH: Pro model quota exceeded")
        return AIResponseMetadata(
            response_text="flash response",
            thinking_requested=kwargs["use_thinking"],
            thinking_applied=True,
            thinking_summary="mock thinking summary",
            model_used=kwargs["model"],
        )

    monkeypatch.setattr(provider, "_execute_prompt_internal", fake_execute_prompt_internal)

    response = await provider.execute_prompt(
        user_prompt="Explain the retry behavior",
        task_type="prompt",
        use_thinking=True,
    )

    assert [call["model"] for call in calls] == [
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
    ]
    assert all(call["use_thinking"] is True for call in calls)
    assert response.response_text == "flash response"
    assert response.thinking_requested is True
    assert response.thinking_applied is True
    assert response.model_fallback_applied is True
    assert response.model_fallback_reason == "Pro model quota exceeded"


def test_gemini_per_task_model_override(gemini_config):
    """Per-command Gemini env fields override the generic pro/flash tiers."""
    gemini_config.gemini_model_prompt = "gemini-custom-prompt"
    gemini_config.gemini_summary_model = "gemini-summary-model"
    provider = GeminiProvider(gemini_config)

    assert provider.get_model_for_task("prompt") == "gemini-custom-prompt"
    assert provider.get_model_for_task("analyze") == "gemini-2.5-flash"
    assert provider.get_model_for_task("voice_summary") == "gemini-summary-model"
