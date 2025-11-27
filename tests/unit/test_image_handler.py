"""Unit tests for ImageHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon.tl.types import Message as TelethonMessage

from src.telegram.handlers.image_handler import ImageHandler
from src.ai.processor import AIProcessor
from src.ai.image_generator import ImageGenerator
from src.ai.prompt_enhancer import PromptEnhancer


@pytest.fixture
def mock_ai_processor():
    """Create mocked AIProcessor."""
    processor = MagicMock(spec=AIProcessor)
    processor.is_configured = True
    return processor


@pytest.fixture
def mock_image_generator():
    """Create mocked ImageGenerator."""
    generator = MagicMock(spec=ImageGenerator)
    return generator


@pytest.fixture
def mock_prompt_enhancer():
    """Create mocked PromptEnhancer."""
    enhancer = MagicMock(spec=PromptEnhancer)
    return enhancer


@pytest.fixture
def image_handler(mock_ai_processor, mock_image_generator, mock_prompt_enhancer):
    """Create ImageHandler with mocked dependencies."""
    return ImageHandler(
        ai_processor=mock_ai_processor,
        image_generator=mock_image_generator,
        prompt_enhancer=mock_prompt_enhancer
    )


@pytest.fixture
def mock_message():
    """Create mocked Telegram message."""
    message = MagicMock(spec=TelethonMessage)
    message.id = 12345
    message.chat_id = 67890
    message.sender_id = 11111
    message.text = "/image=flux=a beautiful sunset"
    message.is_reply = False
    return message


@pytest.fixture
def mock_client():
    """Create mocked Telegram client."""
    client = AsyncMock()
    client.send_message = AsyncMock()
    client.send_file = AsyncMock()
    client.edit_message = AsyncMock()
    return client


def test_parse_image_command_flux(image_handler, mock_message):
    """Test parsing Flux image command."""
    result = image_handler._parse_image_command(mock_message)
    
    assert result is not None
    assert result["model"] == "flux"
    assert result["prompt"] == "a beautiful sunset"


def test_parse_image_command_sdxl(image_handler, mock_message):
    """Test parsing SDXL image command."""
    mock_message.text = "/image=sdxl=futuristic city"
    result = image_handler._parse_image_command(mock_message)
    
    assert result is not None
    assert result["model"] == "sdxl"
    assert result["prompt"] == "futuristic city"


def test_parse_image_command_invalid_model(image_handler, mock_message):
    """Test parsing command with invalid model."""
    mock_message.text = "/image=invalid=prompt"
    result = image_handler._parse_image_command(mock_message)
    
    assert result is None


def test_parse_image_command_missing_prompt(image_handler, mock_message):
    """Test parsing command without prompt."""
    mock_message.text = "/image=flux"
    result = image_handler._parse_image_command(mock_message)
    
    assert result is None


def test_parse_image_command_wrong_format(image_handler, mock_message):
    """Test parsing non-image command."""
    mock_message.text = "/prompt=test"
    result = image_handler._parse_image_command(mock_message)
    
    assert result is None


@pytest.mark.asyncio
async def test_handle_image_command_invalid_format(image_handler, mock_message, mock_client):
    """Test handling invalid command format."""
    mock_message.text = "/image=invalid"
    
    await image_handler.handle_image_command(
        mock_message, mock_client, 67890, "Test User"
    )
    
    mock_client.send_message.assert_called_once()
    call_args = mock_client.send_message.call_args
    assert "فرمت دستور نامعتبر" in call_args[0][1] or "invalid" in call_args[0][1].lower()


@pytest.mark.asyncio
async def test_handle_image_command_rate_limited(image_handler, mock_message, mock_client):
    """Test handling rate-limited request."""
    from src.utils.rate_limiter import get_ai_rate_limiter
    
    # Exhaust rate limit
    rate_limiter = get_ai_rate_limiter()
    for _ in range(15):  # More than limit
        await rate_limiter.check_rate_limit(mock_message.sender_id)
    
    await image_handler.handle_image_command(
        mock_message, mock_client, 67890, "Test User"
    )
    
    # Should send rate limit message
    mock_client.send_message.assert_called_once()
    call_args = mock_client.send_message.call_args
    assert "rate limit" in call_args[0][1].lower()


@pytest.mark.asyncio
async def test_process_image_command_success_flux(
    image_handler, mock_message, mock_client, mock_prompt_enhancer, mock_image_generator
):
    """Test successful Flux image generation flow."""
    from pathlib import Path
    from src.ai.image_queue import image_queue
    from src.ai.image_queue import ImageRequest, ImageStatus
    
    # Clear queue state before test
    image_queue._flux_queue.clear()
    image_queue._sdxl_queue.clear()
    image_queue._requests.clear()
    image_queue._flux_processing = False
    image_queue._sdxl_processing = False
    
    # Setup mocks
    mock_prompt_enhancer.enhance_prompt = AsyncMock(return_value=("enhanced prompt", "openrouter"))
    mock_image_generator.generate_with_flux = AsyncMock(
        return_value=(True, "/tmp/test_image.png", None)
    )
    
    # Mock file operations
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.unlink'):
            # Create a mock thinking message
            thinking_msg = MagicMock()
            mock_client.send_message = AsyncMock(return_value=thinking_msg)
            mock_client.edit_message = AsyncMock()
            mock_client.send_file = AsyncMock()
            
            # Process the command (it will add the request itself)
            # The queue should be empty, so try_start_processing should return True immediately
            await image_handler.process_image_command(
                mock_message, mock_client, 67890, "Test User", "flux", "test prompt"
            )
            
            # Verify prompt was enhanced
            mock_prompt_enhancer.enhance_prompt.assert_called_once_with("test prompt")
            
            # Verify image was generated
            mock_image_generator.generate_with_flux.assert_called_once_with("enhanced prompt")
            
            # Verify image was sent
            mock_client.send_file.assert_called_once()


@pytest.mark.asyncio
async def test_process_image_command_generation_failure(
    image_handler, mock_message, mock_client, mock_prompt_enhancer, mock_image_generator
):
    """Test handling image generation failure."""
    from src.ai.image_queue import image_queue
    
    # Clear queue state before test
    image_queue._flux_queue.clear()
    image_queue._sdxl_queue.clear()
    image_queue._requests.clear()
    image_queue._flux_processing = False
    image_queue._sdxl_processing = False
    
    mock_prompt_enhancer.enhance_prompt = AsyncMock(return_value=("enhanced prompt", "openrouter"))
    mock_image_generator.generate_with_flux = AsyncMock(
        return_value=(False, None, "Generation failed")
    )
    
    thinking_msg = MagicMock()
    mock_client.send_message = AsyncMock(return_value=thinking_msg)
    mock_client.edit_message = AsyncMock()
    
    await image_handler.process_image_command(
        mock_message, mock_client, 67890, "Test User", "flux", "test prompt"
    )
    
    # Should edit message with error
    mock_client.edit_message.assert_called()
    # Should not send file
    mock_client.send_file.assert_not_called()

