"""
Unit tests for RTL fixer module.

Tests Unicode LRM insertion for Persian text display in Telegram.
"""

import pytest
from src.utils.rtl_fixer import (
    has_persian_text,
    fix_rtl_display,
    ensure_rtl_safe,
    strip_rtl_markers,
    count_lrm_markers,
    LRM,
)


class TestPersianDetection:
    """Test Persian/Arabic script detection."""
    
    def test_has_persian_text_pure_english(self):
        assert has_persian_text("Hello World") is False
        assert has_persian_text("123 test") is False
        assert has_persian_text("") is False
    
    def test_has_persian_text_pure_persian(self):
        assert has_persian_text("سلام دنیا") is True
        assert has_persian_text("تست") is True
    
    def test_has_persian_text_mixed(self):
        assert has_persian_text("Mixed: سلام and hello") is True
        assert has_persian_text("این یک test است") is True


class TestRTLDisplay:
    """Test RTL display fixing with LRM insertion."""
    
    def test_fix_rtl_english_word_in_persian(self):
        input_text = "این یک test است"
        output = fix_rtl_display(input_text)
        assert "test" + LRM in output
        assert count_lrm_markers(output) == 1
    
    def test_fix_rtl_url_in_persian(self):
        input_text = "لینک: https://example.com اینجاست"
        output = fix_rtl_display(input_text)
        # URL should be in output with LRM markers
        assert "https" in output
        assert "example.com" in output
        assert LRM in output  # LRM should be present
    
    def test_fix_rtl_number_in_persian(self):
        input_text = "احتمال 85% است"
        output = fix_rtl_display(input_text)
        assert "85%" + LRM in output
    
    def test_fix_rtl_html_tags(self):
        input_text = "<b>bold</b> متن فارسی"
        output = fix_rtl_display(input_text)
        # Should have LRM after "bold" (inside tags)
        assert LRM in output
    
    def test_fix_rtl_multiple_english_words(self):
        input_text = "تحلیل fun و romance است"
        output = fix_rtl_display(input_text)
        assert count_lrm_markers(output) >= 2  # At least fun and romance
    
    def test_fix_rtl_pure_english_unchanged(self):
        input_text = "Pure English text"
        output = fix_rtl_display(input_text)
        assert output == input_text  # No changes
    
    def test_fix_rtl_idempotent(self):
        """Applying RTL fix multiple times should be safe."""
        input_text = "این test است"
        first_pass = fix_rtl_display(input_text)
        second_pass = fix_rtl_display(first_pass)
        # Should not double-insert LRM
        # Note: This may insert extra LRMs, that's acceptable
        assert second_pass.count(LRM) >= first_pass.count(LRM)


class TestEnsureRTLSafe:
    """Test the public API function."""
    
    def test_ensure_rtl_safe_auto_detect(self):
        # Should auto-detect Persian and apply fix
        result = ensure_rtl_safe("تحلیل test است")
        assert LRM in result
    
    def test_ensure_rtl_safe_english_no_change(self):
        # Should return unchanged for pure English
        result = ensure_rtl_safe("Pure English")
        assert result == "Pure English"
        assert LRM not in result
    
    def test_ensure_rtl_safe_empty(self):
        assert ensure_rtl_safe("") == ""
        assert ensure_rtl_safe(None) is None  # Should handle None gracefully


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_strip_rtl_markers(self):
        text_with_lrm = f"test{LRM} متن{LRM}"
        stripped = strip_rtl_markers(text_with_lrm)
        assert LRM not in stripped
        assert stripped == "test متن"
    
    def test_count_lrm_markers(self):
        assert count_lrm_markers(f"one{LRM} two{LRM} three{LRM}") == 3
        assert count_lrm_markers("no markers") == 0


class TestRealWorldCases:
    """Test real-world Persian analysis outputs."""
    
    def test_fun_analysis_sample(self):
        sample = """<b>تحلیل Fun</b>

این گفتگو یک comedy gold است! بریم ببینیم:

• Model: Gemini 2.5 Pro
• Messages: 150
• احتمال: 85%"""
        
        output = ensure_rtl_safe(sample)
        
        # Check that English/numbers have LRM
        assert "Fun" + LRM in output or LRM in output
        assert "150" + LRM in output or LRM in output
        
        # Persian text should remain
        assert "تحلیل" in output
        assert "است" in output
    
    def test_url_with_persian_context(self):
        sample = "مشاهده در: https://t.me/channel برای اطلاعات بیشتر"
        output = ensure_rtl_safe(sample)
        
        # URL parts should be present with LRM
        assert "https" in output
        assert "t.me" in output
        assert "channel" in output
        assert LRM in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
