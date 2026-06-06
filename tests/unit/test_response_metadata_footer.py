"""Tests for the dynamic conditional metadata footer."""

from src.ai.response_metadata import (
    AIResponseMetadata,
    build_response_parts,
    _format_thinking_block,
)


def _footer_lines(metadata: AIResponseMetadata) -> list[str]:
    """Return the data-bearing lines of the footer (no separator, no LRE/PDF)."""
    _, footer = build_response_parts(metadata)
    if not footer:
        return []
    lines = []
    for raw in footer.split("\n"):
        line = raw.strip()
        if not line or line.startswith("━"):
            continue
        # Strip directional markers for readable comparisons.
        line = line.replace("‪", "").replace("‬", "")
        lines.append(line)
    return lines


class TestEmptyMetadata:
    def test_nothing_known_means_empty_footer(self) -> None:
        m = AIResponseMetadata(response_text="hi")
        h, f = build_response_parts(m)
        assert h == ""
        assert f == ""


class TestFactsLine:
    def test_model_only(self) -> None:
        m = AIResponseMetadata(
            response_text="hi", model_used="gemini-3.5-flash",
        )
        lines = _footer_lines(m)
        assert lines == ["<b>Model:</b> gemini-3.5-flash"]

    def test_full_facts(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            model_used="gemini-3.5-flash",
            latency_seconds=4.234,
            input_tokens=128,
            output_tokens=312,
        )
        lines = _footer_lines(m)
        assert len(lines) == 1
        assert "<b>Model:</b> gemini-3.5-flash" in lines[0]
        assert "<b>Time:</b> 4.2s" in lines[0]
        assert "<b>Tokens:</b> 128/312" in lines[0]

    def test_output_only_tokens(self) -> None:
        # Some free models don't report prompt_tokens. Show just the
        # output count rather than the "in/out" form.
        m = AIResponseMetadata(
            response_text="hi",
            model_used="deepseek/deepseek-v4-flash:free",
            output_tokens=312,
        )
        lines = _footer_lines(m)
        # Single token line with no "in/out" separator.
        assert "<b>Tokens:</b> 312" in lines[0]
        # No "NNN/NNN" pattern when only output_tokens is set.
        import re as _re
        assert not _re.search(r"\d+/\d+", lines[0])

    def test_zero_placeholders_hidden(self) -> None:
        # Tokens=0 and Time=0.0 are NOT legitimate facts - they're the
        # default uninitialized values. The renderer must hide them.
        m = AIResponseMetadata(
            response_text="hi",
            model_used="gemini-3.5-flash",
            latency_seconds=0.0,
            input_tokens=0,
            output_tokens=0,
        )
        lines = _footer_lines(m)
        assert lines == ["<b>Model:</b> gemini-3.5-flash"]

    def test_none_means_not_measured(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            model_used="gemini-3.5-flash",
            latency_seconds=None,
            input_tokens=None,
            output_tokens=None,
        )
        lines = _footer_lines(m)
        assert lines == ["<b>Model:</b> gemini-3.5-flash"]


class TestBadgesLine:
    def test_thinking_badge_when_applied(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            thinking_requested=True, thinking_applied=True,
        )
        lines = _footer_lines(m)
        assert any("🧠 Deep Thinking" in ln for ln in lines)

    def test_thinking_warning_when_not_applied(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            thinking_requested=True, thinking_applied=False,
            fallback_reason="unsupported",
        )
        lines = _footer_lines(m)
        assert any("Thinking unsupported" in ln for ln in lines)

    def test_web_search_badge(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            web_search_requested=True, web_search_applied=True,
        )
        lines = _footer_lines(m)
        assert any("🌐 Web Search" in ln for ln in lines)

    def test_provider_fallback_badge(self) -> None:
        m = AIResponseMetadata(
            response_text="hi",
            provider_fallback_applied=True,
            provider_used="OpenRouter",
            provider_fallback_reason="primary blocked",
        )
        lines = _footer_lines(m)
        assert any("🔄 Fallback: OpenRouter" in ln for ln in lines)


class TestThinkingBlock:
    def test_uses_real_blockquote(self) -> None:
        # The header is a real <blockquote>, not the legacy ▎ workaround.
        block = _format_thinking_block("Step 1\nStep 2")
        assert "<blockquote>" in block
        assert "</blockquote>" in block
        assert "▎" not in block

    def test_escapes_html_specials_in_reasoning(self) -> None:
        block = _format_thinking_block("user < said \"hi\" & left")
        assert "&lt;" in block
        assert "&amp;" in block

    def test_truncation_marker_stylized(self) -> None:
        block = _format_thinking_block("partial reasoning [...truncated]")
        # The literal upstream marker gets replaced with styled italics.
        assert "[...truncated]" not in block
        assert "truncated" in block.lower()
        assert "<i>" in block

    def test_empty_reasoning_returns_empty(self) -> None:
        assert _format_thinking_block("") == ""
        assert _format_thinking_block("   \n  \n") == ""
