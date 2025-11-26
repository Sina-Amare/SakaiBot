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


@pytest.mark.asyncio
async def test_enhance_prompt_success(prompt_enhancer, mock_ai_processor):
    """Test successful prompt enhancement."""
    user_prompt = "cat"
    enhanced_prompt = "A beautiful orange tabby cat sitting on a windowsill, soft natural lighting, photorealistic style"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=enhanced_prompt)
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result == enhanced_prompt
    mock_ai_processor.execute_custom_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_empty_response(prompt_enhancer, mock_ai_processor):
    """Test fallback to original prompt when LLM returns empty."""
    user_prompt = "sunset"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value="")
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result == user_prompt  # Should return original


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_ai_error(prompt_enhancer, mock_ai_processor):
    """Test fallback to original prompt on AIProcessorError."""
    user_prompt = "mountain"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(
        side_effect=AIProcessorError("API error")
    )
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result == user_prompt  # Should return original


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_not_configured(prompt_enhancer, mock_ai_processor):
    """Test fallback when AI processor is not configured."""
    user_prompt = "dog"
    mock_ai_processor.is_configured = False
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result == user_prompt  # Should return original
    mock_ai_processor.execute_custom_prompt.assert_not_called()


@pytest.mark.asyncio
async def test_enhance_prompt_truncates_long_response(prompt_enhancer, mock_ai_processor):
    """Test that very long enhanced prompts are truncated."""
    user_prompt = "test"
    # Create a prompt longer than MAX_IMAGE_PROMPT_LENGTH
    long_prompt = "word " * 300  # ~1500 characters
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=long_prompt)
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    from src.core.constants import MAX_IMAGE_PROMPT_LENGTH
    assert len(result) <= MAX_IMAGE_PROMPT_LENGTH


@pytest.mark.asyncio
async def test_enhance_prompt_removes_markdown_code_blocks(prompt_enhancer, mock_ai_processor):
    """Test that markdown code blocks are removed from response."""
    user_prompt = "test"
    enhanced_with_markdown = "```\nA beautiful test image\n```"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(return_value=enhanced_with_markdown)
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert "```" not in result
    assert "A beautiful test image" in result


@pytest.mark.asyncio
async def test_enhance_prompt_handles_exception(prompt_enhancer, mock_ai_processor):
    """Test fallback on unexpected exception."""
    user_prompt = "test"
    
    mock_ai_processor.execute_custom_prompt = AsyncMock(
        side_effect=Exception("Unexpected error")
    )
    
    result = await prompt_enhancer.enhance_prompt(user_prompt)
    
    assert result == user_prompt  # Should return original

