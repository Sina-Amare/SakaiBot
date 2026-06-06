"""Tests for HTML-safe image captions."""

from telethon.extensions import html as telethon_html

from src.telegram.handlers.image_handler import ImageHandler


def test_image_caption_prompt_text_is_html_escaped() -> None:
    escaped = ImageHandler._escape_caption_text("a <cat> & dog", 200)

    assert escaped == "a &lt;cat&gt; &amp; dog"

    text, _ = telethon_html.parse(
        "🎨 Image generated\n<b>Enhanced prompt:</b>\n" + escaped
    )
    assert "a <cat> & dog" in text


def test_image_caption_truncation_does_not_cut_entity() -> None:
    escaped = ImageHandler._escape_caption_text("A & B & C", 8)

    assert escaped.endswith("...")
    assert not escaped.endswith("&...")
    telethon_html.parse("<b>Enhanced prompt:</b>\n" + escaped)
