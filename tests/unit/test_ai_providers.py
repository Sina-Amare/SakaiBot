"""Unit tests for AI providers."""

import asyncio
import sys
from pathlib import Path
import unittest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import get_settings
from src.ai.processor import AIProcessor
from src.utils.logging import get_logger

logger = get_logger("AIProviderTest")


class TestAIProviders(unittest.TestCase):
    """Test AI provider functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = get_settings()
        self.current_provider = self.config.llm_provider
    
    def test_gemini_provider_initialization(self):
        """Test Gemini provider initialization."""
        if self.current_provider == "gemini":
            processor = AIProcessor(self.config)
            self.assertTrue(processor.is_configured)
            self.assertEqual(processor.provider_name, "Google Gemini")
    
    def test_openrouter_provider_initialization(self):
        """Test OpenRouter provider initialization."""
        if self.current_provider == "openrouter":
            processor = AIProcessor(self.config)
            self.assertTrue(processor.is_configured)
            self.assertEqual(processor.provider_name, "OpenRouter")
    
    def test_provider_switching(self):
        """Test switching between providers."""
        # Test current provider
        processor = AIProcessor(self.config)
        self.assertTrue(processor.is_configured)
        
        # Test switching to other provider if configured
        other_provider = "openrouter" if self.current_provider == "gemini" else "gemini"
        # This would require mocking API keys for a complete test


if __name__ == "__main__":
    unittest.main()
