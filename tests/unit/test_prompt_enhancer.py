"""Unit tests for PromptEnhancer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.prompt_enhancer import PromptEnhancer
from src.ai.processor import AIProcessor
from src.core.exceptions import AIProcessorError


@pytest.fixture
def mock_ai_processor():
    """Create mocked AIProcessor."""
    processor = MagicMock(spec=AIProcessor)
    processor.is_configured = True
    return processor


@pytest.fixture
def prompt_enhancer(mock_ai_processor):
    """Create PromptEnhancer with mocked AIProcessor."""
    return PromptEnhancer(ai_processor=mock_ai_processor)


@pytest.fixture
def mock_config_openrouter():
    """Mock config with OpenRouter settings."""
    with patch('src.ai.prompt_enhancer.get_settings') as mock_settings:
        config = MagicMock()
        config.llm_provider = "openrouter"
        config.openrouter_api_key = "test_key"
        config.gemini_api_key = "gemini_key"
        mock_settings.return_value = config
        yield config


@pytest.mark.asyncio
async def test_enhance_prompt_success_openrouter(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test successful prompt enhancement using OpenRouter."""
    user_prompt = "cat"
    enhanced_prompt = "A beautiful orange tabby cat sitting on a windowsill, soft natural lighting, photorealistic style"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=enhanced_prompt)
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result_prompt == enhanced_prompt
    assert model_used == "openrouter"
    mock_ai_processor.execute_custom_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_to_gemini(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test fallback to Gemini when OpenRouter fails."""
    user_prompt = "sunset"
    enhanced_prompt = "Stunning sunset over ocean with warm colors"
    
    # First call (OpenRouter) fails, second call (Gemini) succeeds
    mock_ai_processor.execute_custom_prompt = AsyncMock(
        side_effect=[Exception("OpenRouter failed"), enhanced_prompt]
    )
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result_prompt == enhanced_prompt
    assert model_used == "gemini"
    assert mock_ai_processor.execute_custom_prompt.call_count == 2


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_empty_response(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test fallback to original prompt when all LLMs return empty."""
    user_prompt = "mountain"
    
    # Both OpenRouter and Gemini return empty
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value="")
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result_prompt == user_prompt  # Should return original
    assert model_used == "none"


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_not_configured(prompt_enhancer, mock_ai_processor):
    """Test fallback when AI processor is not configured."""
    user_prompt = "dog"
    mock_ai_processor.is_configured = False
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result_prompt == user_prompt  # Should return original
    assert model_used == "none"
    mock_ai_processor.execute_custom_prompt.assert_not_called()


@pytest.mark.asyncio
async def test_enhance_prompt_truncates_long_response(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test that very long enhanced prompts are truncated."""
    user_prompt = "test"
    # Create a prompt longer than MAX_IMAGE_PROMPT_LENGTH
    long_prompt = "word " * 300  # ~1500 characters
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=long_prompt)
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    from src.core.constants import MAX_IMAGE_PROMPT_LENGTH
    assert len(result_prompt) <= MAX_IMAGE_PROMPT_LENGTH
    assert model_used == "openrouter"


@pytest.mark.asyncio
async def test_enhance_prompt_removes_markdown_code_blocks(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test that markdown code blocks are removed from response."""
    user_prompt = "test"
    enhanced_with_markdown = "```\nA beautiful test image\n```"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=enhanced_with_markdown)
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert "```" not in result_prompt
    assert "A beautiful test image" in result_prompt
    assert model_used == "openrouter"


@pytest.mark.asyncio
async def test_enhance_prompt_handles_all_failures(prompt_enhancer, mock_ai_processor, mock_config_openrouter):
    """Test fallback to original when both OpenRouter and Gemini fail."""
    user_prompt = "test"
    
    # Both fail
    mock_ai_processor.execute_custom_prompt = AsyncMock(
        side_effect=[Exception("OpenRouter error"), Exception("Gemini error")]
    )
    
    result_prompt, model_used = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result_prompt == user_prompt  # Should return original
    assert model_used == "none"

