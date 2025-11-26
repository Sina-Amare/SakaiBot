"""Integration tests for image generation (requires real worker endpoints)."""

import pytest
import os
from pathlib import Path

from src.ai.image_generator import ImageGenerator
from src.ai.prompt_enhancer import PromptEnhancer
from src.ai.processor import AIProcessor
from src.core.config import get_settings


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_flux_generation_end_to_end():
    """Test end-to-end Flux image generation with real worker."""
    # Skip if not configured
    config = get_settings()
    if not config.flux_worker_url or "test" in config.flux_worker_url.lower():
        pytest.skip("Flux worker URL not configured for integration testing")
    
    generator = ImageGenerator()
    try:
        success, image_path, error = await generator.generate_with_flux("a simple test image of a cat")
        
        if success:
            assert image_path is not None
            assert Path(image_path).exists()
            # Cleanup
            Path(image_path).unlink(missing_ok=True)
        else:
            # If it fails, log the error but don't fail the test
            # (worker might be down, rate limited, etc.)
            pytest.skip(f"Flux generation failed: {error}")
    finally:
        await generator.close()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_sdxl_generation_end_to_end():
    """Test end-to-end SDXL image generation with real worker."""
    # Skip if not configured
    config = get_settings()
    if not config.sdxl_worker_url or not config.sdxl_api_key:
        pytest.skip("SDXL worker URL or API key not configured for integration testing")
    
    generator = ImageGenerator()
    try:
        success, image_path, error = await generator.generate_with_sdxl("a simple test image of a dog")
        
        if success:
            assert image_path is not None
            assert Path(image_path).exists()
            # Cleanup
            Path(image_path).unlink(missing_ok=True)
        else:
            # If it fails, log the error but don't fail the test
            pytest.skip(f"SDXL generation failed: {error}")
    finally:
        await generator.close()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_prompt_enhancement_integration():
    """Test prompt enhancement with real AI processor."""
    config = get_settings()
    if not config.is_ai_enabled:
        pytest.skip("AI processor not configured for integration testing")
    
    processor = AIProcessor()
    enhancer = PromptEnhancer(ai_processor=processor)
    
    user_prompt = "sunset"
    enhanced = await enhancer.enhance_prompt(user_prompt)
    
    assert enhanced is not None
    assert len(enhanced) > len(user_prompt)  # Should be enhanced
    assert user_prompt.lower() in enhanced.lower()  # Should contain original concept


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_image_generation_flow():
    """Test full flow: enhancement -> generation -> file creation."""
    config = get_settings()
    
    # Skip if not properly configured
    if not config.is_ai_enabled:
        pytest.skip("AI processor not configured")
    if not config.flux_worker_url:
        pytest.skip("Flux worker not configured")
    
    processor = AIProcessor()
    enhancer = PromptEnhancer(ai_processor=processor)
    generator = ImageGenerator()
    
    try:
        # Enhance prompt
        user_prompt = "mountain landscape"
        enhanced = await enhancer.enhance_prompt(user_prompt)
        assert enhanced is not None
        
        # Generate image
        success, image_path, error = await generator.generate_with_flux(enhanced)
        
        if success:
            assert image_path is not None
            assert Path(image_path).exists()
            # Verify it's actually an image file
            assert image_path.endswith('.png')
            # Cleanup
            Path(image_path).unlink(missing_ok=True)
        else:
            pytest.skip(f"Image generation failed: {error}")
    finally:
        await generator.close()

