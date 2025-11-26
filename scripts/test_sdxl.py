"""Quick SDXL test script."""

import asyncio
import sys
import os
from pathlib import Path

# Set SDXL API key in environment
os.environ['SDXL_API_KEY'] = '95XSpGFuIyFzfpCO9kVmn531M4L2AuEM'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import load_config
from src.ai.processor import AIProcessor
from src.ai.image_generator import ImageGenerator
from src.ai.prompt_enhancer import PromptEnhancer
from src.utils.logging import setup_logging
import logging


async def test_sdxl():
    """Test SDXL image generation."""
    print("=" * 60)
    print("SDXL Image Generation Test")
    print("=" * 60)
    print()
    
    # Setup logging
    setup_logging(level=logging.INFO, enable_console=True)
    
    # Load configuration
    print("📋 Loading configuration...")
    try:
        config = load_config()
        # Override SDXL API key
        config.sdxl_api_key = '95XSpGFuIyFzfpCO9kVmn531M4L2AuEM'
        print(f"   ✓ Configuration loaded")
        print(f"   - SDXL Worker URL: {config.sdxl_worker_url}")
        print(f"   - SDXL API Key: {'✓ Set' if config.sdxl_api_key else '✗ Not set'}")
        print()
    except Exception as e:
        print(f"   ✗ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Initialize components
    print("🔧 Initializing components...")
    try:
        ai_processor = AIProcessor(config)
        prompt_enhancer = PromptEnhancer(ai_processor)
        image_generator = ImageGenerator()
        # Override config in image generator
        image_generator._config.sdxl_api_key = '95XSpGFuIyFzfpCO9kVmn531M4L2AuEM'
        print("   ✓ Components initialized")
        print()
    except Exception as e:
        print(f"   ✗ Failed to initialize components: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test prompt
    test_prompt = "a serene Japanese garden with cherry blossoms"
    
    print("🎨 Testing SDXL Worker")
    print("-" * 60)
    print(f"\nTesting SDXL with prompt: '{test_prompt}'")
    
    try:
        # Enhance prompt
        print("   → Enhancing prompt...")
        enhanced = await prompt_enhancer.enhance_prompt(test_prompt)
        print(f"   ✓ Enhanced prompt ({len(enhanced)} chars)")
        print(f"      Preview: {enhanced[:100]}...")
        
        # Generate image
        print("   → Generating image with SDXL...")
        success, image_path, error = await image_generator.generate_with_sdxl(enhanced)
        
        if success and image_path:
            print(f"   ✓ Image generated successfully!")
            print(f"      Saved to: {image_path}")
            if Path(image_path).exists():
                file_size = Path(image_path).stat().st_size
                print(f"      File size: {file_size / 1024:.2f} KB")
            return True
        else:
            print(f"   ✗ Image generation failed: {error}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await image_generator.close()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        success = asyncio.run(test_sdxl())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

