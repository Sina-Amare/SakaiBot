"""Tests for Input Validators.

Critical tests for input validation and sanitization.
This is a high priority test file as validators prevent injection attacks.
"""

import pytest

from src.utils.validators import (
    InputValidator,
    VALID_LANGUAGE_CODES,
    MAX_PROMPT_LENGTH,
    MAX_COMMAND_LENGTH,
)


class TestValidatePrompt:
    """Tests for prompt validation."""

    def test_valid_prompt_passes(self):
        """Valid prompt is returned sanitized."""
        result = InputValidator.validate_prompt("Hello world")
        assert result == "Hello world"

    def test_prompt_strips_whitespace(self):
        """Prompt is trimmed of whitespace."""
        result = InputValidator.validate_prompt("  Hello world  ")
        assert result == "Hello world"

    def test_prompt_removes_control_chars(self):
        """Control characters are removed from prompt."""
        result = InputValidator.validate_prompt("Hello\x00\x1fworld")
        assert result == "Helloworld"

    def test_empty_prompt_raises_error(self):
        """Empty prompt raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            InputValidator.validate_prompt("")

    def test_none_prompt_raises_error(self):
        """None prompt raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            InputValidator.validate_prompt(None)

    def test_whitespace_only_prompt_raises_error(self):
        """Whitespace-only prompt raises ValueError."""
        with pytest.raises(ValueError, match="empty after sanitization"):
            InputValidator.validate_prompt("   \n\t   ")

    def test_prompt_too_long_raises_error(self):
        """Prompt exceeding max length raises ValueError."""
        long_prompt = "a" * (MAX_PROMPT_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            InputValidator.validate_prompt(long_prompt)

    def test_prompt_at_max_length_passes(self):
        """Prompt at exactly max length passes."""
        exact_prompt = "a" * MAX_PROMPT_LENGTH
        result = InputValidator.validate_prompt(exact_prompt)
        assert len(result) == MAX_PROMPT_LENGTH

    def test_custom_max_length(self):
        """Custom max length is respected."""
        with pytest.raises(ValueError, match="max 100"):
            InputValidator.validate_prompt("a" * 101, max_length=100)


class TestValidateLanguageCode:
    """Tests for language code validation."""

    def test_valid_codes_pass(self):
        """Known valid language codes return True."""
        valid_codes = ["en", "fa", "es", "fr", "de", "ja", "zh", "ar"]
        for code in valid_codes:
            assert InputValidator.validate_language_code(code) is True

    def test_invalid_code_fails(self):
        """Invalid language code returns False."""
        assert InputValidator.validate_language_code("xyz") is False

    def test_empty_code_fails(self):
        """Empty code returns False."""
        assert InputValidator.validate_language_code("") is False

    def test_none_code_fails(self):
        """None code returns False."""
        assert InputValidator.validate_language_code(None) is False

    def test_case_insensitive(self):
        """Language codes are case insensitive."""
        assert InputValidator.validate_language_code("EN") is True
        assert InputValidator.validate_language_code("Fa") is True

    def test_code_with_whitespace(self):
        """Whitespace is stripped from codes."""
        assert InputValidator.validate_language_code("  en  ") is True


class TestSanitizeCommandInput:
    """Tests for command input sanitization."""

    def test_normal_text_unchanged(self):
        """Normal text passes through unchanged."""
        result = InputValidator.sanitize_command_input("normal text")
        assert result == "normal text"

    def test_removes_control_characters(self):
        """Control characters are removed."""
        result = InputValidator.sanitize_command_input("hello\x00world")
        assert result == "helloworld"

    def test_removes_script_tags(self):
        """Script tags are removed."""
        result = InputValidator.sanitize_command_input("<script>alert()</script>")
        assert "<script" not in result.lower()

    def test_removes_javascript_protocol(self):
        """javascript: protocol is removed."""
        result = InputValidator.sanitize_command_input("javascript:alert()")
        assert "javascript:" not in result.lower()

    def test_removes_event_handlers(self):
        """Event handlers are removed."""
        result = InputValidator.sanitize_command_input('onclick="alert()"')
        assert "onclick" not in result.lower()

    def test_removes_command_substitution(self):
        """Command substitution patterns are removed."""
        result = InputValidator.sanitize_command_input("$(rm -rf /)")
        assert "$(" not in result

    def test_removes_backtick_commands(self):
        """Backtick command execution is removed."""
        result = InputValidator.sanitize_command_input("`rm -rf /`")
        assert "`" not in result

    def test_removes_variable_substitution(self):
        """Variable substitution is removed."""
        result = InputValidator.sanitize_command_input("${PATH}")
        assert "${" not in result

    def test_empty_string_returns_empty(self):
        """Empty string returns empty."""
        result = InputValidator.sanitize_command_input("")
        assert result == ""

    def test_none_returns_empty(self):
        """None returns empty string."""
        result = InputValidator.sanitize_command_input(None)
        assert result == ""

    def test_truncates_long_input(self):
        """Long input is truncated to max length."""
        long_input = "a" * (MAX_COMMAND_LENGTH + 100)
        result = InputValidator.sanitize_command_input(long_input)
        assert len(result) == MAX_COMMAND_LENGTH


class TestValidateCommandArgs:
    """Tests for command arguments validation."""

    def test_valid_args_pass(self):
        """Valid arguments pass validation."""
        result = InputValidator.validate_command_args("arg1 arg2")
        assert result == "arg1 arg2"

    def test_dangerous_script_rejected(self):
        """Script tags are rejected."""
        result = InputValidator.validate_command_args("<script>alert()</script>")
        assert result is None

    def test_dangerous_javascript_rejected(self):
        """javascript: protocol is rejected."""
        result = InputValidator.validate_command_args("javascript:void(0)")
        assert result is None

    def test_dangerous_command_substitution_rejected(self):
        """Command substitution is rejected."""
        result = InputValidator.validate_command_args("$(whoami)")
        assert result is None

    def test_empty_args_returns_none(self):
        """Empty args returns None."""
        result = InputValidator.validate_command_args("")
        assert result is None


class TestValidateFilePath:
    """Tests for file path validation."""

    def test_valid_path_passes(self):
        """Valid relative path passes."""
        assert InputValidator.validate_file_path("file.txt") is True
        assert InputValidator.validate_file_path("dir/file.txt") is True

    def test_directory_traversal_blocked(self):
        """Directory traversal is blocked."""
        assert InputValidator.validate_file_path("../etc/passwd") is False
        assert InputValidator.validate_file_path("..\\windows\\system32") is False

    def test_absolute_unix_path_blocked(self):
        """Absolute Unix paths are blocked."""
        assert InputValidator.validate_file_path("/etc/passwd") is False

    def test_absolute_windows_path_blocked(self):
        """Absolute Windows paths are blocked."""
        assert InputValidator.validate_file_path("C:\\Windows\\System32") is False

    def test_command_injection_blocked(self):
        """Command injection patterns are blocked."""
        assert InputValidator.validate_file_path("file.txt; rm -rf /") is False
        assert InputValidator.validate_file_path("file.txt | cat") is False
        assert InputValidator.validate_file_path("file.txt & del") is False
        assert InputValidator.validate_file_path("$(cmd)") is False

    def test_empty_path_fails(self):
        """Empty path fails validation."""
        assert InputValidator.validate_file_path("") is False

    def test_none_path_fails(self):
        """None path fails validation."""
        assert InputValidator.validate_file_path(None) is False


class TestValidateNumber:
    """Tests for number validation."""

    def test_valid_number_passes(self):
        """Valid number string is parsed."""
        assert InputValidator.validate_number("42") == 42

    def test_number_with_whitespace(self):
        """Whitespace is stripped from numbers."""
        assert InputValidator.validate_number("  42  ") == 42

    def test_number_below_min_fails(self):
        """Number below minimum returns None."""
        assert InputValidator.validate_number("0", min_val=1) is None

    def test_number_above_max_fails(self):
        """Number above maximum returns None."""
        assert InputValidator.validate_number("100", max_val=50) is None

    def test_number_at_min_passes(self):
        """Number at minimum passes."""
        assert InputValidator.validate_number("1", min_val=1) == 1

    def test_number_at_max_passes(self):
        """Number at maximum passes."""
        assert InputValidator.validate_number("100", max_val=100) == 100

    def test_non_numeric_fails(self):
        """Non-numeric string returns None."""
        assert InputValidator.validate_number("abc") is None

    def test_float_fails(self):
        """Float string returns None."""
        assert InputValidator.validate_number("3.14") is None

    def test_empty_string_fails(self):
        """Empty string returns None."""
        assert InputValidator.validate_number("") is None

    def test_none_fails(self):
        """None returns None."""
        assert InputValidator.validate_number(None) is None


class TestValidateImageModel:
    """Tests for image model validation."""

    def test_valid_models_pass(self):
        """Valid model names pass."""
        assert InputValidator.validate_image_model("flux") is True
        assert InputValidator.validate_image_model("sdxl") is True

    def test_invalid_model_fails(self):
        """Invalid model name fails."""
        assert InputValidator.validate_image_model("dalle") is False
        assert InputValidator.validate_image_model("midjourney") is False

    def test_case_insensitive(self):
        """Model names are case insensitive."""
        assert InputValidator.validate_image_model("FLUX") is True
        assert InputValidator.validate_image_model("Sdxl") is True

    def test_with_whitespace(self):
        """Whitespace is stripped."""
        assert InputValidator.validate_image_model("  flux  ") is True

    def test_empty_fails(self):
        """Empty string fails."""
        assert InputValidator.validate_image_model("") is False

    def test_none_fails(self):
        """None fails."""
        assert InputValidator.validate_image_model(None) is False


class TestValidateImagePrompt:
    """Tests for image prompt validation."""

    def test_valid_prompt_passes(self):
        """Valid image prompt passes."""
        result = InputValidator.validate_image_prompt("a beautiful sunset")
        assert result == "a beautiful sunset"

    def test_strips_whitespace(self):
        """Whitespace is stripped."""
        result = InputValidator.validate_image_prompt("  sunset  ")
        assert result == "sunset"

    def test_removes_control_chars(self):
        """Control characters are removed."""
        result = InputValidator.validate_image_prompt("sun\x00set")
        assert result == "sunset"

    def test_empty_prompt_raises(self):
        """Empty prompt raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            InputValidator.validate_image_prompt("")

    def test_none_prompt_raises(self):
        """None prompt raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            InputValidator.validate_image_prompt(None)
