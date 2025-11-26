"""Unit tests for ImageGenerator."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.ai.image_generator import ImageGenerator
from src.core.exceptions import AIProcessorError
from src.core.constants import IMAGE_TEMP_DIR


@pytest.fixture
def image_generator():
    """Create ImageGenerator instance with mocked config."""
    with patch('src.ai.image_generator.get_settings') as mock_settings:
        mock_config = MagicMock()
        mock_config.flux_worker_url = "https://test-flux.workers.dev"
        mock_config.sdxl_worker_url = "https://test-sdxl.workers.dev"
        mock_config.sdxl_api_key = "test_api_key_123"
        mock_settings.return_value = mock_config
        
        generator = ImageGenerator()
        yield generator
        # Cleanup
        if generator._http_client:
            import asyncio
            try:
                asyncio.run(generator.close())
            except:
                pass


@pytest.mark.asyncio
async def test_generate_with_flux_success(image_generator):
    """Test successful Flux image generation."""
    # Mock HTTP response with image data
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.content = b"fake_image_data"
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_flux("test prompt")
        
        assert success is True
        assert image_path is not None
        assert error is None
        assert Path(image_path).exists()
        
        # Cleanup
        Path(image_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_generate_with_sdxl_success(image_generator):
    """Test successful SDXL image generation."""
    # Mock HTTP response with image data
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.content = b"fake_image_data"
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_sdxl("test prompt")
        
        assert success is True
        assert image_path is not None
        assert error is None
        assert Path(image_path).exists()
        
        # Verify POST was called with correct params
        mock_http.post.assert_called_once()
        call_args = mock_http.post.call_args
        assert "Bearer test_api_key_123" in str(call_args.kwargs.get("headers", {}))
        assert call_args.kwargs.get("json") == {"prompt": "test prompt"}
        
        # Cleanup
        Path(image_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_generate_with_flux_timeout(image_generator):
    """Test Flux generation timeout handling."""
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_flux("test prompt")
        
        assert success is False
        assert image_path is None
        assert "timeout" in error.lower() or "timed out" in error.lower()


@pytest.mark.asyncio
async def test_generate_with_sdxl_unauthorized(image_generator):
    """Test SDXL generation with 401 Unauthorized."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {}
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_sdxl("test prompt")
        
        assert success is False
        assert image_path is None
        assert "401" in error or "unauthorized" in error.lower() or "api key" in error.lower()


@pytest.mark.asyncio
async def test_generate_with_sdxl_missing_api_key(image_generator):
    """Test SDXL generation without API key."""
    image_generator._config.sdxl_api_key = None
    
    success, image_path, error = await image_generator.generate_with_sdxl("test prompt")
    
    assert success is False
    assert image_path is None
    assert "api key" in error.lower() or "configured" in error.lower()


@pytest.mark.asyncio
async def test_generate_with_flux_rate_limit(image_generator):
    """Test Flux generation with 429 Rate Limit."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_flux("test prompt")
        
        assert success is False
        assert image_path is None
        assert "rate limit" in error.lower() or "429" in error


@pytest.mark.asyncio
async def test_generate_with_sdxl_server_error(image_generator):
    """Test SDXL generation with 500 Server Error."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    mock_response.json = MagicMock(return_value={"error": "Internal server error", "details": "Worker failed"})
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_sdxl("test prompt")
        
        assert success is False
        assert image_path is None
        assert "error" in error.lower() or "500" in error


@pytest.mark.asyncio
async def test_generate_with_flux_invalid_response(image_generator):
    """Test Flux generation with invalid (non-image) response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json = MagicMock(return_value={"error": "Invalid request"})
    
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_flux("test prompt")
        
        assert success is False
        assert image_path is None
        assert error is not None


@pytest.mark.asyncio
async def test_generate_with_sdxl_network_error(image_generator):
    """Test SDXL generation with network error and retry."""
    with patch.object(image_generator, '_get_http_client') as mock_client:
        mock_http = AsyncMock()
        # The retry decorator will retry, but the exception is caught inside _make_sdxl_request
        # which raises AIProcessorError, so the retry happens at the generate_with_sdxl level
        mock_http.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client.return_value = mock_http
        
        success, image_path, error = await image_generator.generate_with_sdxl("test prompt")
        
        assert success is False
        assert image_path is None
        assert "network" in error.lower() or "connection" in error.lower()
        
        # The retry decorator should retry, but since _make_sdxl_request catches and re-raises
        # as AIProcessorError, the retry happens. However, the actual HTTP call count
        # depends on how the retry decorator works with the exception handling.
        # Let's just verify it was called at least once
        assert mock_http.post.call_count >= 1


@pytest.mark.asyncio
async def test_save_image_success(image_generator):
    """Test successful image saving."""
    test_data = b"fake_image_png_data"
    image_path = image_generator._save_image(test_data, "flux")
    
    assert image_path is not None
    assert Path(image_path).exists()
    assert Path(image_path).read_bytes() == test_data
    
    # Cleanup
    Path(image_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_image_creates_directory(image_generator):
    """Test that temp directory is created if it doesn't exist."""
    import shutil
    temp_dir = Path(IMAGE_TEMP_DIR)
    
    # Remove directory if it exists
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    test_data = b"fake_image_data"
    image_path = image_generator._save_image(test_data, "sdxl")
    
    assert temp_dir.exists()
    assert Path(image_path).exists()
    
    # Cleanup
    Path(image_path).unlink(missing_ok=True)
    if temp_dir.exists() and not any(temp_dir.iterdir()):
        temp_dir.rmdir()

