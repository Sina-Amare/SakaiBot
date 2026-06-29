"""Tests for the telegram_html safety pipeline."""

import pytest

from src.utils.telegram_html import (
    sanitize_html,
    validate_or_escape,
    clean_telegram_html,
)


class TestSanitizeHtml:
    def test_allowed_tag_passes_through(self) -> None:
        assert sanitize_html("<b>hi</b>") == "<b>hi</b>"

    def test_disallowed_tag_escaped_to_literal(self) -> None:
        assert sanitize_html("<h1>x</h1>") == "&lt;h1&gt;x&lt;/h1&gt;"

    def test_attributes_stripped_from_allowed_tag(self) -> None:
        # Allowed tag keeps its name, drops every attribute - prevents
        # attribute-based injection or markup Telegram doesn't honor.
        assert sanitize_html('<b onclick="x()">hi</b>') == "<b>hi</b>"

    def test_nested_allowed_tags(self) -> None:
        assert (
            sanitize_html("<blockquote><b>hi</b></blockquote>")
            == "<blockquote><b>hi</b></blockquote>"
        )

    def test_raw_lt_gt_amp_escaped(self) -> None:
        assert sanitize_html("a < b & c > d") == "a &lt; b &amp; c &gt; d"

    def test_existing_entities_are_preserved(self) -> None:
        assert sanitize_html("5 &lt; 6 &amp; 7 &gt; 3") == "5 &lt; 6 &amp; 7 &gt; 3"

    def test_mixed_allowed_and_disallowed(self) -> None:
        out = sanitize_html("<b>ok</b> and <h2>bad</h2>")
        assert "<b>ok</b>" in out
        assert "&lt;h2&gt;bad&lt;/h2&gt;" in out

    def test_persian_text_preserved(self) -> None:
        out = sanitize_html("سلام <b>دنیا</b>")
        assert "سلام" in out
        assert "<b>دنیا</b>" in out

    def test_empty_input(self) -> None:
        assert sanitize_html("") == ""

    def test_all_allowed_tags(self) -> None:
        for tag in ("b", "i", "u", "s", "code", "pre", "blockquote"):
            assert sanitize_html(f"<{tag}>x</{tag}>") == f"<{tag}>x</{tag}>"


class TestValidateOrEscape:
    def test_valid_markup_unchanged(self) -> None:
        assert validate_or_escape("<b>hi</b>") == "<b>hi</b>"

    def test_empty_unchanged(self) -> None:
        assert validate_or_escape("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert validate_or_escape("plain text") == "plain text"


class TestPipeline:
    def test_pipeline_combines_both(self) -> None:
        out = clean_telegram_html("<h1>x</h1><b>y</b> & z")
        # Disallowed h1 escaped, allowed b preserved, & escaped.
        assert "&lt;h1&gt;" in out
        assert "<b>y</b>" in out
        assert "&amp;" in out

    def test_pipeline_persian_with_specials(self) -> None:
        # Realistic: an analysis output with Persian content, a code block,
        # and a chat-quoted < character.
        text = "<b>تحلیل</b>: کاربر گفت 5 < 3 و <i>این اشتباه است</i>"
        out = clean_telegram_html(text)
        assert "<b>تحلیل</b>" in out
        assert "<i>این اشتباه است</i>" in out
        assert "5 &lt; 3" in out

    def test_pipeline_does_not_double_escape_bot_entities(self) -> None:
        text = "<code>/prompt=&lt;question&gt;</code> Tom &amp; Jerry"
        out = clean_telegram_html(text)
        assert out == "<code>/prompt=&lt;question&gt;</code> Tom &amp; Jerry"

    def test_pipeline_never_crashes_on_garbage(self) -> None:
        # No matter how malformed the input, the pipeline returns a string.
        for garbage in ("<<<<<", "&&&&", "<b><i><blockquote><b>", "<\x00>"):
            assert isinstance(clean_telegram_html(garbage), str)


class TestMarkdownNormalization:
    """Leaked Markdown (from weaker models) is normalized to clean Telegram HTML."""

    def test_bold_and_heading_become_html(self) -> None:
        out = clean_telegram_html("## Summary\nThis is **important** stuff")
        assert "<b>Summary</b>" in out
        assert "<b>important</b>" in out
        assert "**" not in out and "##" not in out

    def test_bullets_and_rules_cleaned(self) -> None:
        out = clean_telegram_html("- first\n- second\n---\n")
        assert "• first" in out and "• second" in out
        assert "---" not in out

    def test_inline_code_normalized(self) -> None:
        assert "<code>backend</code>" in clean_telegram_html("the `backend` part")

    def test_single_asterisk_evidence_preserved(self) -> None:
        # a stray single * in quoted content must NOT be mangled into a tag
        out = clean_telegram_html("she wrote 3 * 4 = 12")
        assert "3 * 4 = 12" in out and "<b>" not in out and "<i>" not in out
