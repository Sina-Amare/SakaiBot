"""Unit tests for AI processor."""

import unittest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock

from src.core.config import Config
from src.core.exceptions import AIProcessorError
from src.ai.processor import AIProcessor


class TestAIProcessor(unittest.TestCase):
    """Test AIProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.llm_provider = "openrouter"
        self.mock_config.openrouter_api_key = "sk-test12345678901234567890"
        self.mock_config.gemini_api_key = None
    
    @patch('src.ai.processor.OpenRouterProvider')
    def test_initialize_openrouter_provider(self, mock_provider_class):
        """Test initializing OpenRouter provider."""
        mock_provider = Mock()
        type(mock_provider).is_configured = PropertyMock(return_value=True)
        type(mock_provider).provider_name = PropertyMock(return_value="OpenRouter")
        type(mock_provider).model_name = PropertyMock(return_value="test-model")
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        
        self.assertEqual(processor.provider_name, "OpenRouter")
        mock_provider_class.assert_called_once_with(self.mock_config)
    
    @patch('src.ai.processor.GeminiProvider')
    def test_initialize_gemini_provider(self, mock_provider_class):
        """Test initializing Gemini provider."""
        self.mock_config.llm_provider = "gemini"
        self.mock_config.gemini_api_key = "AIzaTest12345678901234567890"
        self.mock_config.openrouter_api_key = None
        
        mock_provider = Mock()
        type(mock_provider).is_configured = PropertyMock(return_value=True)
        type(mock_provider).provider_name = PropertyMock(return_value="Google Gemini")
        type(mock_provider).model_name = PropertyMock(return_value="test-model")
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        
        self.assertEqual(processor.provider_name, "Google Gemini")
        mock_provider_class.assert_called_once_with(self.mock_config)
    
    def test_initialize_invalid_provider(self):
        """Test initializing with invalid provider."""
        self.mock_config.llm_provider = "invalid"
        
        with self.assertRaises(AIProcessorError):
            AIProcessor(self.mock_config)
    
    @patch('src.ai.processor.OpenRouterProvider')
    def test_is_configured_true(self, mock_provider_class):
        """Test is_configured when provider is configured."""
        mock_provider = Mock()
        mock_provider.is_configured = True
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        self.assertTrue(processor.is_configured)
    
    @patch('src.ai.processor.OpenRouterProvider')
    def test_is_configured_false(self, mock_provider_class):
        """Test is_configured when provider is not configured."""
        mock_provider = Mock()
        mock_provider.is_configured = False
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        self.assertFalse(processor.is_configured)
    
    @patch('src.ai.processor.OpenRouterProvider')
    def test_provider_name(self, mock_provider_class):
        """Test getting provider name."""
        mock_provider = Mock()
        mock_provider.provider_name = "TestProvider"
        mock_provider.is_configured = True
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        self.assertEqual(processor.provider_name, "TestProvider")
    
    @patch('src.ai.processor.OpenRouterProvider')
    def test_model_name(self, mock_provider_class):
        """Test getting model name."""
        mock_provider = Mock()
        mock_provider.model_name = "test-model"
        mock_provider.is_configured = True
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        self.assertEqual(processor.model_name, "test-model")


class TestAIProcessorAsync(unittest.IsolatedAsyncioTestCase):
    """Test AIProcessor async methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.llm_provider = "openrouter"
        self.mock_config.openrouter_api_key = "sk-test12345678901234567890"
    
    @patch('src.ai.processor.OpenRouterProvider')
    async def test_execute_custom_prompt(self, mock_provider_class):
        """Test executing custom prompt."""
        mock_provider = AsyncMock()
        mock_provider.is_configured = True
        mock_provider.execute_prompt.return_value = "Test response"
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        result = await processor.execute_custom_prompt("Test prompt")
        
        self.assertEqual(result, "Test response")
        mock_provider.execute_prompt.assert_called_once()
    
    @patch('src.ai.processor.OpenRouterProvider')
    async def test_execute_custom_prompt_not_configured(self, mock_provider_class):
        """Test executing prompt when not configured."""
        mock_provider = Mock()
        mock_provider.is_configured = False
        mock_provider_class.return_value = mock_provider
        
        processor = AIProcessor(self.mock_config)
        
        with self.assertRaises(AIProcessorError):
            await processor.execute_custom_prompt("Test prompt")


if __name__ == "__main__":
    unittest.main()

