"""Structural contract for the rewritten prompts (not prose quality).

Enforces: one shared output spec, friendly محاوره‌ای Persian, Telegram-HTML
only (never Markdown), evidence-via-direct-quote, no bureaucratic Persian,
and that the builders render cleanly with no leftover placeholders.
"""

import pytest

from src.ai.prompts import (
    PROMPT_ADAPTIVE_PROMPT,
    TRANSLATION_AUTO_DETECT_PROMPT,
    TRANSLATION_SOURCE_TARGET_PROMPT,
    build_analysis_prompt,
    build_question_prompt,
    output_spec,
)

MODES = ("fun", "general", "romance")
LANGS = ("persian", "english")


def _no_markdown(text: str) -> None:
    """A built prompt must never instruct in Markdown (the old contradiction)."""
    assert "```" not in text
    assert "## " not in text
    assert "**" not in text  # no Markdown bold anywhere in the new prompts


class TestOutputSpec:
    def test_persian_spec_core_rules(self):
        s = output_spec("persian")
        assert "Telegram HTML" in s
        for tag in ("<b>", "<i>", "<blockquote>", "<code>", "<pre>"):
            assert tag in s
        assert "Markdown" in s
        assert "نقل‌قول" in s          # evidence via direct quote
        assert "می‌باشد" in s and "می‌گردد" in s  # bans bureaucratic Persian
        assert "نیم‌فاصله" in s
        assert "محاوره‌ای" in s        # friendly conversational target
        _no_markdown(s)

    def test_english_spec_core_rules(self):
        s = output_spec("english")
        assert "Telegram HTML" in s and "Markdown" in s
        assert "direct quote" in s
        _no_markdown(s)


class TestAnalysisBuilder:
    @pytest.mark.parametrize("mode", MODES)
    @pytest.mark.parametrize("lang", LANGS)
    def test_renders_cleanly(self, mode, lang):
        p = build_analysis_prompt(mode, lang, "CHAT_TEXT_MARKER", 50)
        assert "CHAT_TEXT_MARKER" in p          # the chat is embedded
        assert "<b>" in p and "</b>" in p        # real HTML headers
        assert "{" not in p and "}" not in p     # no leftover placeholders
        _no_markdown(p)
        assert output_spec(lang).strip()[:20] in p  # the shared spec is applied

    def test_persian_modes_have_signature_sections(self):
        assert "شوی اصلی" in build_analysis_prompt("fun", "persian", "x")
        assert "خلاصه اجرایی" in build_analysis_prompt("general", "persian", "x")
        romance = build_analysis_prompt("romance", "persian", "x")
        assert "نشانه‌ها" in romance and "درصد" in romance

    def test_unknown_mode_falls_back_to_general(self):
        assert "خلاصه اجرایی" in build_analysis_prompt("wat", "persian", "x")


class TestQuestionBuilder:
    def test_persian_strict_grounding_and_adaptive(self):
        p = build_question_prompt("persian", "HISTORY_X", "QUESTION_Y")
        assert "HISTORY_X" in p and "QUESTION_Y" in p
        assert "نساز" in p                       # invent nothing
        assert "یک‌خطی" in p                     # adaptive length
        _no_markdown(p)

    def test_english_strict_grounding(self):
        p = build_question_prompt("english", "HIST", "Q")
        assert "HIST" in p and "Q" in p
        assert "invent" in p.lower()
        _no_markdown(p)


class TestPromptCommand:
    def test_adaptive_prompt_renders(self):
        rendered = PROMPT_ADAPTIVE_PROMPT.format(user_prompt="hello")
        assert "hello" in rendered
        assert "محاوره‌ای" in rendered or "محاوره" in rendered
        assert "{" not in rendered or "}" not in rendered
        _no_markdown(rendered)


class TestTranslation:
    def test_typo_fixing_and_phonetics(self):
        for p in (TRANSLATION_AUTO_DETECT_PROMPT, TRANSLATION_SOURCE_TARGET_PROMPT):
            assert "silently fix" in p.lower()
            assert "Phonetic" in p
            assert "{text}" in p and "{target_language_name}" in p
