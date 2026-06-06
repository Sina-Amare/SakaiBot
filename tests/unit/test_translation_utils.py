"""Tests for translation formatting and prompt-facing helpers."""

from telethon.extensions import html as telethon_html

from src.utils.translation_utils import format_translation_response


def test_translation_response_uses_telegram_html_not_markdown() -> None:
    out = format_translation_response(
        "I wore you out too.",
        "آی وُر یو آوت تو",
        "en",
    )

    assert "<b>ترجمه به English</b>" in out
    assert "<b>تلفظ</b>" in out
    assert "**" not in out

    parsed_text, entities = telethon_html.parse(out)
    assert "I wore you out too." in parsed_text
    assert entities
