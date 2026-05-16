"""Unit tests for AIProcessor chat-history Q&A metadata normalization."""

import logging
from types import SimpleNamespace

import pytest

from src.ai.processor import AIProcessor
from src.ai.response_metadata import AIResponseMetadata
from src.core.exceptions import AIProcessorError


class _FailingQuestionProvider:
    is_configured = True

    async def answer_question_from_history(self, **kwargs):
        raise AIProcessorError("primary failed")


class _PlainTextQuestionProvider:
    is_configured = True

    async def answer_question_from_history(self, **kwargs):
        return "raw fallback answer"


@pytest.mark.asyncio
async def test_answer_question_from_chat_history_wraps_plain_text_fallback():
    """Plain text fallback results do not crash metadata-based handlers."""
    processor = object.__new__(AIProcessor)
    processor._config = SimpleNamespace(llm_provider="gemini")
    processor._logger = logging.getLogger("test")
    processor._primary_provider = _FailingQuestionProvider()
    processor._fallback_provider = _PlainTextQuestionProvider()
    processor._provider = processor._primary_provider
    processor._using_fallback = False

    result = await processor.answer_question_from_chat_history(
        messages_data=[{"sender": "Alice", "text": "hello"}],
        user_question="What happened?",
        use_thinking=True,
        use_web_search=True,
    )

    assert isinstance(result, AIResponseMetadata)
    assert result.response_text == "raw fallback answer"
    assert result.thinking_requested is True
    assert result.web_search_requested is True
    assert result.provider_fallback_applied is True
