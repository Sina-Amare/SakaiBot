"""Unit tests for OpenRouter chat-history Q&A response metadata."""

from types import SimpleNamespace

import pytest

from src.ai.providers.openrouter import OpenRouterProvider
from src.ai.response_metadata import AIResponseMetadata


@pytest.fixture
def openrouter_config():
    """Minimal OpenRouter config for provider unit tests."""
    return SimpleNamespace(
        openrouter_api_keys=["sk-or-v1-test123456"],
        openrouter_api_key=None,
        openrouter_model="default-model",
        openrouter_model_pro="pro-model",
        openrouter_model_flash="flash-model",
        openrouter_model_prompt=None,
        openrouter_model_analyze=None,
        openrouter_model_tellme=None,
        openrouter_model_translate=None,
        openrouter_model_image_enhance=None,
        openrouter_model_prompt_enhancer=None,
        openrouter_model_voice_summary=None,
    )


@pytest.mark.asyncio
async def test_answer_question_from_history_returns_metadata(
    openrouter_config, monkeypatch
):
    """OpenRouter Q&A preserves metadata instead of returning raw text."""
    provider = OpenRouterProvider(openrouter_config)

    async def fake_execute_prompt(*args, **kwargs):
        assert args
        assert kwargs["task_type"] == "tellme"
        assert kwargs["use_web_search"] is True
        return AIResponseMetadata(
            response_text="fallback answer",
            web_search_requested=kwargs["use_web_search"],
            web_search_applied=False,
            model_used="pro-model",
        )

    monkeypatch.setattr(provider, "execute_prompt", fake_execute_prompt)

    result = await provider.answer_question_from_history(
        messages=[{"sender_name": "Alice", "text": "hello"}],
        question="What happened?",
        use_web_search=True,
    )

    assert isinstance(result, AIResponseMetadata)
    assert result.response_text == "fallback answer"
    assert result.web_search_requested is True
    assert result.web_search_applied is False


@pytest.mark.asyncio
async def test_answer_question_from_history_empty_text_returns_metadata(
    openrouter_config,
):
    """Empty text history returns the standard no-content answer as metadata."""
    provider = OpenRouterProvider(openrouter_config)

    result = await provider.answer_question_from_history(
        messages=[{"sender_name": "Alice", "text": ""}],
        question="What happened?",
        use_thinking=True,
        use_web_search=True,
    )

    assert isinstance(result, AIResponseMetadata)
    assert "هیچ پیام متنی" in result.response_text
    assert result.thinking_requested is True
    assert result.web_search_requested is True


def test_openrouter_per_task_model_override(openrouter_config):
    """Per-command OpenRouter env fields override the generic pro/flash tiers."""
    openrouter_config.openrouter_model_translate = "translation-model"
    provider = OpenRouterProvider(openrouter_config)

    assert provider.get_model_for_task("translate") == "translation-model"
    assert provider.get_model_for_task("tellme") == "pro-model"
