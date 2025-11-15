"""Unit tests for LLM interface."""

import unittest
from abc import ABC

from src.ai.llm_interface import LLMProvider


class TestLLMInterface(unittest.TestCase):
    """Test LLMProvider interface."""
    
    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider is an abstract base class."""
        self.assertTrue(issubclass(LLMProvider, ABC))
    
    def test_llm_provider_has_required_methods(self):
        """Test that LLMProvider has required abstract methods."""
        # Check that required methods exist
        self.assertTrue(hasattr(LLMProvider, 'execute_prompt'))
        self.assertTrue(hasattr(LLMProvider, 'is_configured'))
        self.assertTrue(hasattr(LLMProvider, 'provider_name'))
        self.assertTrue(hasattr(LLMProvider, 'model_name'))
    
    def test_cannot_instantiate_llm_provider(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            LLMProvider()


if __name__ == "__main__":
    unittest.main()

