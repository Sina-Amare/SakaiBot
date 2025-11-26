"""Unit tests for ImageQueue."""

import pytest
from src.ai.image_queue import ImageQueue, ImageStatus, ImageRequest


@pytest.fixture
def image_queue():
    """Create fresh ImageQueue instance."""
    from src.ai.image_queue import ImageQueue
    return ImageQueue()


def test_add_request_flux(image_queue):
    """Test adding Flux request to queue."""
    request_id = image_queue.add_request("flux", "test prompt", user_id=123)
    
    assert request_id is not None
    assert request_id.startswith("img_")
    
    request = image_queue.get_request(request_id)
    assert request is not None
    assert request.model == "flux"
    assert request.prompt == "test prompt"
    assert request.user_id == 123
    assert request.status == ImageStatus.PENDING


def test_add_request_sdxl(image_queue):
    """Test adding SDXL request to queue."""
    request_id = image_queue.add_request("sdxl", "another prompt", user_id=456)
    
    request = image_queue.get_request(request_id)
    assert request.model == "sdxl"
    assert request.prompt == "another prompt"
    assert request.user_id == 456


def test_separate_queues_per_model(image_queue):
    """Test that Flux and SDXL have separate queues."""
    flux_id1 = image_queue.add_request("flux", "prompt1", user_id=1)
    sdxl_id1 = image_queue.add_request("sdxl", "prompt2", user_id=2)
    flux_id2 = image_queue.add_request("flux", "prompt3", user_id=3)
    
    # Flux queue should have 2 requests
    assert image_queue.get_pending_count("flux") == 2
    # SDXL queue should have 1 request
    assert image_queue.get_pending_count("sdxl") == 1


def test_queue_position_flux(image_queue):
    """Test queue position tracking for Flux."""
    id1 = image_queue.add_request("flux", "prompt1", user_id=1)
    id2 = image_queue.add_request("flux", "prompt2", user_id=2)
    id3 = image_queue.add_request("flux", "prompt3", user_id=3)
    
    assert image_queue.get_queue_position(id1, "flux") == 1
    assert image_queue.get_queue_position(id2, "flux") == 2
    assert image_queue.get_queue_position(id3, "flux") == 3


def test_queue_position_sdxl(image_queue):
    """Test queue position tracking for SDXL."""
    id1 = image_queue.add_request("sdxl", "prompt1", user_id=1)
    id2 = image_queue.add_request("sdxl", "prompt2", user_id=2)
    
    assert image_queue.get_queue_position(id1, "sdxl") == 1
    assert image_queue.get_queue_position(id2, "sdxl") == 2


def test_try_start_processing_flux(image_queue):
    """Test starting processing for Flux request."""
    id1 = image_queue.add_request("flux", "prompt1", user_id=1)
    id2 = image_queue.add_request("flux", "prompt2", user_id=2)
    
    # First request should start processing
    assert image_queue.try_start_processing(id1, "flux") is True
    assert image_queue.is_flux_processing() is True
    
    # Second request should not start (first is processing)
    assert image_queue.try_start_processing(id2, "flux") is False
    
    request = image_queue.get_request(id1)
    assert request.status == ImageStatus.PROCESSING


def test_try_start_processing_sdxl(image_queue):
    """Test starting processing for SDXL request."""
    id1 = image_queue.add_request("sdxl", "prompt1", user_id=1)
    
    assert image_queue.try_start_processing(id1, "sdxl") is True
    assert image_queue.is_sdxl_processing() is True


def test_concurrent_processing_different_models(image_queue):
    """Test that Flux and SDXL can process concurrently."""
    flux_id = image_queue.add_request("flux", "prompt1", user_id=1)
    sdxl_id = image_queue.add_request("sdxl", "prompt2", user_id=2)
    
    # Both should be able to start processing
    assert image_queue.try_start_processing(flux_id, "flux") is True
    assert image_queue.try_start_processing(sdxl_id, "sdxl") is True
    
    assert image_queue.is_flux_processing() is True
    assert image_queue.is_sdxl_processing() is True


def test_mark_completed(image_queue):
    """Test marking request as completed."""
    request_id = image_queue.add_request("flux", "prompt", user_id=1)
    image_queue.try_start_processing(request_id, "flux")
    
    image_queue.mark_completed(request_id, "/path/to/image.png")
    
    request = image_queue.get_request(request_id)
    assert request.status == ImageStatus.COMPLETED
    assert request.image_path == "/path/to/image.png"
    assert image_queue.is_flux_processing() is False


def test_mark_failed(image_queue):
    """Test marking request as failed."""
    request_id = image_queue.add_request("sdxl", "prompt", user_id=1)
    image_queue.try_start_processing(request_id, "sdxl")
    
    image_queue.mark_failed(request_id, "Generation failed")
    
    request = image_queue.get_request(request_id)
    assert request.status == ImageStatus.FAILED
    assert request.error_message == "Generation failed"
    assert image_queue.is_sdxl_processing() is False


def test_get_status(image_queue):
    """Test getting request status."""
    request_id = image_queue.add_request("flux", "prompt", user_id=1)
    
    assert image_queue.get_status(request_id) == "pending"
    
    image_queue.try_start_processing(request_id, "flux")
    assert image_queue.get_status(request_id) == "processing"
    
    image_queue.mark_completed(request_id, "/path/to/image.png")
    assert image_queue.get_status(request_id) == "completed"


def test_cleanup_request(image_queue):
    """Test cleaning up completed request."""
    request_id = image_queue.add_request("flux", "prompt", user_id=1)
    image_queue.mark_completed(request_id, "/path/to/image.png")
    
    image_queue.cleanup_request(request_id)
    
    assert image_queue.get_request(request_id) is None
    assert image_queue.get_pending_count("flux") == 0


def test_get_pending_count(image_queue):
    """Test getting pending count."""
    assert image_queue.get_pending_count() == 0
    
    image_queue.add_request("flux", "prompt1", user_id=1)
    image_queue.add_request("flux", "prompt2", user_id=2)
    image_queue.add_request("sdxl", "prompt3", user_id=3)
    
    assert image_queue.get_pending_count() == 3
    assert image_queue.get_pending_count("flux") == 2
    assert image_queue.get_pending_count("sdxl") == 1

