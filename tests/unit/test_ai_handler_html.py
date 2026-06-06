"""Tests for AI handler HTML delivery paths."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.telegram.handlers.ai_handler import AIHandler


class _BlockedRateLimiter:
    _window_seconds = 60

    async def check_rate_limit(self, user_id):
        return False

    async def get_remaining_requests(self, user_id):
        return 0


@pytest.mark.asyncio
async def test_ai_rate_limit_message_uses_html_parse_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.telegram.handlers.ai_handler.get_ai_rate_limiter",
        lambda: _BlockedRateLimiter(),
    )

    handler = AIHandler(ai_processor=Mock())
    event_message = SimpleNamespace(
        id=10,
        chat_id=123,
        sender_id=456,
        get_input_chat=AsyncMock(return_value=123),
    )
    client = SimpleNamespace(send_message=AsyncMock())

    await handler.process_ai_command(
        "/prompt",
        event_message,
        client,
        "sina",
        user_prompt_text="سلام",
    )

    client.send_message.assert_awaited_once()
    assert client.send_message.await_args.kwargs["parse_mode"] == "html"
