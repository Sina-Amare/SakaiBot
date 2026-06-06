r"""Live Persian output smoke tests against the configured AI provider.

These tests intentionally call the real API, so they are opt-in only.
Run on Windows:

    $env:SAKAIBOT_RUN_LIVE_TESTS="1"
    .\venv\Scripts\python.exe -m pytest -s -o addopts="" tests\integration\test_live_persian_ai_output.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from telethon.extensions import html as telethon_html

from src.ai.processor import AIProcessor
from src.core.config import Config
from src.utils.rtl_fixer import ensure_rtl_safe
from src.utils.telegram_html import clean_telegram_html

load_dotenv()


def _live_enabled() -> bool:
    return (
        os.getenv("SAKAIBOT_RUN_LIVE_TESTS") == "1"
        or os.getenv("SAKAIBOT_LIVE_AI_TESTS") == "1"
    )


pytestmark = [
    pytest.mark.integration,
    pytest.mark.live,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not _live_enabled(),
        reason="Set SAKAIBOT_RUN_LIVE_TESTS=1 to call the real AI API",
    ),
]


def _mock_persian_messages() -> list[dict]:
    base = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
    rows = [
        ("سینا", "من می‌گم ساعت ۸ بریم کافه، ولی لطفاً این دفعه کسی نیم ساعت دیر نیاد."),
        ("مریم", "من میام، ولی اگه باز بحث انتخاب جا سه ساعت طول بکشه واقعاً تسلیم می‌شم."),
        ("علی", "من فقط گفتم شاید کافه قبلی بهتر بود، چرا همه فکر می‌کنن دارم مخالفت می‌کنم؟"),
        ("نرگس", "چون هر بار می‌گی فقط یه پیشنهاد دارم، بعد کل برنامه عوض می‌شه."),
        ("سینا", "اوکی پس تصمیم نهایی: کافه رستا، ساعت ۸. این بار واقعاً نهایی."),
        ("مریم", "عالیه. علی جان فقط لطفاً پنج دقیقه قبلش نگو یه جای بهتر پیدا کردی."),
        ("علی", "باشه بابا، قول می‌دم. ولی رستا پارکینگ داره؟"),
        ("نرگس", "دیدی؟ شروع شد."),
        ("مریم", "😂 همین الان احتمال تغییر برنامه رفت روی ۷۰ درصد."),
        ("سینا", "نه دیگه. اگر تغییر بدیم من رسماً از گروه خداحافظی می‌کنم."),
        ("علی", "باشه، رستا. منم میام. فقط یکی لوکیشن دقیق بفرسته."),
        ("نرگس", "فرستادم. لطفاً این یکی رو دیگه گم نکنید."),
    ]
    return [
        {
            "sender": sender,
            "text": text,
            "timestamp": base + timedelta(minutes=i * 3),
        }
        for i, (sender, text) in enumerate(rows)
    ]


@pytest.mark.parametrize("mode", ["general", "fun", "romance"])
async def test_live_persian_analyze_output_is_telegram_html_safe(mode: str) -> None:
    # Some Windows shells expose DEBUG=release. Override only this field so
    # live tests still use the real .env credentials and model configuration.
    processor = AIProcessor(Config(debug=False))

    result = await processor.analyze_conversation_messages(
        _mock_persian_messages(),
        analysis_mode=mode,
        output_language="persian",
        use_thinking=False,
    )

    response_text = result.response_text.strip()
    assert response_text
    assert any("\u0600" <= ch <= "\u06ff" for ch in response_text)

    telegram_text = clean_telegram_html(ensure_rtl_safe(response_text))
    parsed_text, entities = telethon_html.parse(telegram_text)

    assert parsed_text.strip()
    assert entities
    assert "&amp;lt;" not in telegram_text
    assert "&amp;amp;" not in telegram_text

    safe_preview = parsed_text[:240].encode("unicode_escape").decode("ascii")
    print(
        f"\nLIVE {mode}: provider={result.provider_used} model={result.model_used} "
        f"chars={len(response_text)} preview={safe_preview}"
    )
