"""Structural checks on the rewritten Persian AI prompts.

These don't validate prose quality - they enforce the contract every
prompt must satisfy: HTML-only formatting rule, shared tone rules
included, evidence-via-direct-quote, no bureaucratic Persian, format()
works with the documented placeholders.
"""

from src.ai.prompts import (
    SHARED_PERSIAN_TONE_RULES,
    PROMPT_ADAPTIVE_PROMPT,
    TRANSLATION_AUTO_DETECT_PROMPT,
    TRANSLATION_SOURCE_TARGET_PROMPT,
    ANALYZE_GENERAL_PROMPT,
    ANALYZE_FUN_PROMPT,
    ANALYZE_ROMANCE_PROMPT,
    QUESTION_ANSWER_PROMPT,
    get_response_scaling_instructions,
)


# ---- Shared rules ----------------------------------------------------------

class TestSharedRules:
    def test_demands_telegram_html(self) -> None:
        assert "Telegram HTML" in SHARED_PERSIAN_TONE_RULES

    def test_lists_allowed_tags(self) -> None:
        for tag in ("<b>", "<i>", "<blockquote>", "<code>", "<pre>"):
            assert tag in SHARED_PERSIAN_TONE_RULES

    def test_forbids_markdown(self) -> None:
        # The rule explicitly tells the model "no Markdown"; that text
        # contains literal **bold** as an example of what NOT to use.
        assert "Markdown" in SHARED_PERSIAN_TONE_RULES
        assert "نه **bold**" in SHARED_PERSIAN_TONE_RULES

    def test_evidence_via_quote(self) -> None:
        assert "نقل‌قول مستقیم" in SHARED_PERSIAN_TONE_RULES

    def test_forbids_bureaucratic_persian(self) -> None:
        assert "می‌باشد" in SHARED_PERSIAN_TONE_RULES
        assert "می‌گردد" in SHARED_PERSIAN_TONE_RULES

    def test_half_space_rule(self) -> None:
        assert "نیم‌فاصله" in SHARED_PERSIAN_TONE_RULES

    def test_adaptive_length_not_fixed_floor(self) -> None:
        # The rule explicitly tells the model NOT to pad short chats.
        assert "کوتاه" in SHARED_PERSIAN_TONE_RULES

    def test_shared_rules_do_not_inject_confidence_grades(self) -> None:
        for grade in ("کم", "متوسط", "بالا"):
            assert f"({grade})" not in SHARED_PERSIAN_TONE_RULES
        assert "هیچ برچسب اطمینانی" in SHARED_PERSIAN_TONE_RULES


# ---- All prompts inherit the shared rules ----------------------------------

ALL_PROMPTS = (
    ("PROMPT_ADAPTIVE_PROMPT", PROMPT_ADAPTIVE_PROMPT, {"user_prompt": "x"}),
    ("ANALYZE_GENERAL_PROMPT", ANALYZE_GENERAL_PROMPT, {"messages_text": "x"}),
    ("ANALYZE_FUN_PROMPT", ANALYZE_FUN_PROMPT, {"messages_text": "x"}),
    ("ANALYZE_ROMANCE_PROMPT", ANALYZE_ROMANCE_PROMPT, {"messages_text": "x"}),
    (
        "QUESTION_ANSWER_PROMPT", QUESTION_ANSWER_PROMPT,
        {"combined_history_text": "x", "user_question": "x"},
    ),
)


class TestEveryPrompt:
    def test_includes_shared_rules(self) -> None:
        for name, prompt, _ in ALL_PROMPTS:
            assert SHARED_PERSIAN_TONE_RULES in prompt, (
                f"{name} does not include SHARED_PERSIAN_TONE_RULES"
            )

    def test_format_works_with_documented_placeholders(self) -> None:
        for name, prompt, kwargs in ALL_PROMPTS:
            rendered = prompt.format(**kwargs)
            # No leftover {placeholder} after rendering.
            assert "{" not in rendered or "}" not in rendered, (
                f"{name}: leftover placeholder after format"
            )

    def test_no_stray_markdown_bold(self) -> None:
        # Each prompt should contain only ONE `**` occurrence pair (the
        # "نه **bold**" don't-use example in the shared rules) - any more
        # means a Markdown leftover from the old prompt format.
        for name, prompt, _ in ALL_PROMPTS:
            count = prompt.count("**")
            assert count == 2, (
                f"{name}: expected 2 ** characters (one example), got {count}"
            )

    def test_uses_html_bold_for_real_headers(self) -> None:
        for name, prompt, _ in ALL_PROMPTS:
            # Each rewritten prompt uses real <b>...</b> for its own headers.
            assert "<b>" in prompt, f"{name} has no <b> tags"
            assert "</b>" in prompt, f"{name} has no </b> tags"


# ---- Per-prompt domain-specific checks ------------------------------------

class TestAnalyzePrompts:
    def test_general_has_executive_summary(self) -> None:
        assert "خلاصه اجرایی" in ANALYZE_GENERAL_PROMPT

    def test_general_demands_evidence(self) -> None:
        assert "نقل‌قول مستقیم" in ANALYZE_GENERAL_PROMPT

    def test_general_rejects_confidence_label_style(self) -> None:
        assert "بدون برچسب‌های خشک" in ANALYZE_GENERAL_PROMPT
        assert "درجه اطمینان" not in ANALYZE_GENERAL_PROMPT

    def test_fun_demands_chat_specific_humor(self) -> None:
        # The whole point of fun mode: jokes must come from THIS chat.
        assert "از خود این چت بیاید" in ANALYZE_FUN_PROMPT
        assert "شوخی عمومی" in ANALYZE_FUN_PROMPT

    def test_fun_rejects_confidence_labels(self) -> None:
        assert "آخر جمله‌ها برچسب" in ANALYZE_FUN_PROMPT
        assert "برچسب اطمینانی" in ANALYZE_FUN_PROMPT
        assert "فرم ارزیابی کارمند نیست" in ANALYZE_FUN_PROMPT
        assert "درجه اطمینان" not in ANALYZE_FUN_PROMPT

    def test_shared_rules_do_not_force_confidence_labels_everywhere(self) -> None:
        assert "فقط وقتی خود پرامپت" in SHARED_PERSIAN_TONE_RULES
        assert "هیچ برچسب اطمینانی" in SHARED_PERSIAN_TONE_RULES
        assert "درجه اطمینان" not in SHARED_PERSIAN_TONE_RULES

    def test_fun_requires_fact_checking_before_jokes(self) -> None:
        assert "فکت را دوباره" in ANALYZE_FUN_PROMPT
        assert "نقل‌قول ساختگی" in ANALYZE_FUN_PROMPT
        assert "شخصیت‌سازی" in ANALYZE_FUN_PROMPT

    def test_fun_demands_colloquial_persian(self) -> None:
        assert "محاوره‌ای" in ANALYZE_FUN_PROMPT
        assert "گزارش تحلیلی" in ANALYZE_FUN_PROMPT
        assert "می‌کنه" in ANALYZE_FUN_PROMPT
        assert "فیلتر ضد رسمی‌نویسی" in ANALYZE_FUN_PROMPT
        assert "پویایی عاطفی" in ANALYZE_FUN_PROMPT
        assert "کارآموز روان‌شناسی" in ANALYZE_FUN_PROMPT

    def test_romance_demands_natural_uncertainty_without_grade_labels(self) -> None:
        # Romance is the prompt most vulnerable to confident hallucination,
        # so it must discuss uncertainty, but not with ugly (بالا)/(متوسط)
        # labels that leak into every sentence.
        assert "قاعده قطعیت" in ANALYZE_ROMANCE_PROMPT
        assert "شواهد کافی نیست" in ANALYZE_ROMANCE_PROMPT
        assert "درجه اطمینان" not in ANALYZE_ROMANCE_PROMPT
        assert "هر مورد: نقل‌قول + توضیح + درجه اطمینان" not in ANALYZE_ROMANCE_PROMPT
        assert "درصد" in ANALYZE_ROMANCE_PROMPT

    def test_main_prompts_do_not_force_grade_tags(self) -> None:
        for name, prompt in (
            ("shared", SHARED_PERSIAN_TONE_RULES),
            ("general", ANALYZE_GENERAL_PROMPT),
            ("fun", ANALYZE_FUN_PROMPT),
            ("romance", ANALYZE_ROMANCE_PROMPT),
            ("question", QUESTION_ANSWER_PROMPT),
        ):
            for grade in ("(کم)", "(متوسط)", "(بالا)"):
                assert grade not in prompt, f"{name} contains {grade}"

    def test_romance_no_prompt_level_censorship(self) -> None:
        # The user's editorial choice: the prompt does not tell the model
        # to soften or moralize. (Provider safety filters may still block.)
        # We assert by checking the actual rule list is there.
        assert "بدون تعارف" in ANALYZE_ROMANCE_PROMPT

    def test_scaling_instructions_are_html_not_markdown(self) -> None:
        for mode in ("general", "fun", "romance"):
            rendered = get_response_scaling_instructions(250, mode)
            assert "<b>RESPONSE DEPTH SCALING</b>" in rendered
            assert "**RESPONSE" not in rendered
            assert "  * " not in rendered
            assert "```" not in rendered


class TestQuestionAnswer:
    def test_strict_history_grounding(self) -> None:
        # /tellme must refuse to fabricate quotes / times / names.
        assert "هیچ سناریو" in QUESTION_ANSWER_PROMPT
        assert "نساز" in QUESTION_ANSWER_PROMPT

    def test_admits_when_evidence_missing(self) -> None:
        assert "صحبت نشده" in QUESTION_ANSWER_PROMPT

    def test_adaptive_length(self) -> None:
        # Short question -> short answer; explicit rule in the prompt.
        assert "یک‌خطی" in QUESTION_ANSWER_PROMPT


class TestTranslationPrompts:
    def test_translation_prompts_fix_persian_typos_before_translation(self) -> None:
        for prompt in (TRANSLATION_AUTO_DETECT_PROMPT, TRANSLATION_SOURCE_TARGET_PROMPT):
            assert "silently fix obvious Persian typos" in prompt
            assert "Normalize intent before translating" in prompt
            assert "شومارم خسته کردم" in prompt
            assert "phone/number" in prompt
