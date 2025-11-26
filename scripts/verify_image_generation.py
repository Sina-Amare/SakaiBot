"""Verification script for image generation with real workers."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import load_config
from src.ai.processor import AIProcessor
from src.ai.image_generator import ImageGenerator
from src.ai.prompt_enhancer import PromptEnhancer
from src.utils.logging import setup_logging


async def test_image_generation():
    """Test image generation with real workers."""
    print("=" * 60)
    print("Image Generation Verification Script")
    print("=" * 60)
    print()
    
    # Setup logging
    import logging
    setup_logging(level=logging.DEBUG, enable_console=True)
    
    # Load configuration
    print("📋 Loading configuration...")
    try:
        config = load_config()
        print(f"   ✓ Configuration loaded")
        print(f"   - Flux Worker URL: {config.flux_worker_url}")
        print(f"   - SDXL Worker URL: {config.sdxl_worker_url}")
        print(f"   - SDXL API Key: {'✓ Set' if config.sdxl_api_key else '✗ Not set'}")
        print(f"   - LLM Provider: {config.llm_provider}")
        print()
    except Exception as e:
        print(f"   ✗ Failed to load configuration: {e}")
        return
    
    # Check if image generation is enabled
    if not config.is_image_generation_enabled:
        print("⚠️  Image generation is not properly configured!")
        print("   Please set FLUX_WORKER_URL and/or SDXL_WORKER_URL in .env")
        return
    
    # Initialize components
    print("🔧 Initializing components...")
    try:
        ai_processor = AIProcessor(config)
        prompt_enhancer = PromptEnhancer(ai_processor)
        image_generator = ImageGenerator()
        print("   ✓ Components initialized")
        print()
    except Exception as e:
        print(f"   ✗ Failed to initialize components: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test prompts
    test_prompts = [
        "a beautiful sunset over mountains",
        "a cyberpunk cityscape at night with neon lights",
        "a serene Japanese garden with cherry blossoms"
    ]
    
    results = []
    
    # Test Flux
    if config.flux_worker_url and config.flux_worker_url != "https://your-flux-worker.workers.dev":
        print("🎨 Testing Flux Worker")
        print("-" * 60)
        
        for i, prompt in enumerate(test_prompts[:2], 1):  # Test first 2 prompts with Flux
            print(f"\n[{i}/2] Testing Flux with prompt: '{prompt}'")
            
            try:
                # Enhance prompt
                print("   → Enhancing prompt...")
                enhanced = await prompt_enhancer.enhance_prompt(prompt)
                print(f"   ✓ Enhanced prompt ({len(enhanced)} chars)")
                print(f"      Preview: {enhanced[:100]}...")
                
                # Generate image
                print("   → Generating image with Flux...")
                success, image_path, error = await image_generator.generate_with_flux(enhanced)
                
                if success and image_path:
                    print(f"   ✓ Image generated successfully!")
                    print(f"      Saved to: {image_path}")
                    file_size = Path(image_path).stat().st_size if Path(image_path).exists() else 0
                    print(f"      File size: {file_size / 1024:.2f} KB")
                    results.append({
                        "model": "flux",
                        "prompt": prompt,
                        "enhanced": enhanced,
                        "image_path": image_path,
                        "success": True
                    })
                else:
                    print(f"   ✗ Image generation failed: {error}")
                    results.append({
                        "model": "flux",
                        "prompt": prompt,
                        "success": False,
                        "error": error
                    })
            except Exception as e:
                print(f"   ✗ Error: {e}")
                results.append({
                    "model": "flux",
                    "prompt": prompt,
                    "success": False,
                    "error": str(e)
                })
            
            print()
        
        print()
    
    # Test SDXL
    if (config.sdxl_worker_url and config.sdxl_worker_url != "https://your-sdxl-worker.workers.dev" and
        config.sdxl_api_key):
        print("🎨 Testing SDXL Worker")
        print("-" * 60)
        
        for i, prompt in enumerate(test_prompts[1:3], 1):  # Test last 2 prompts with SDXL
            print(f"\n[{i}/2] Testing SDXL with prompt: '{prompt}'")
            
            try:
                # Enhance prompt
                print("   → Enhancing prompt...")
                enhanced = await prompt_enhancer.enhance_prompt(prompt)
                print(f"   ✓ Enhanced prompt ({len(enhanced)} chars)")
                print(f"      Preview: {enhanced[:100]}...")
                
                # Generate image
                print("   → Generating image with SDXL...")
                success, image_path, error = await image_generator.generate_with_sdxl(enhanced)
                
                if success and image_path:
                    print(f"   ✓ Image generated successfully!")
                    print(f"      Saved to: {image_path}")
                    file_size = Path(image_path).stat().st_size if Path(image_path).exists() else 0
                    print(f"      File size: {file_size / 1024:.2f} KB")
                    results.append({
                        "model": "sdxl",
                        "prompt": prompt,
                        "enhanced": enhanced,
                        "image_path": image_path,
                        "success": True
                    })
                else:
                    print(f"   ✗ Image generation failed: {error}")
                    results.append({
                        "model": "sdxl",
                        "prompt": prompt,
                        "success": False,
                        "error": error
                    })
            except Exception as e:
                print(f"   ✗ Error: {e}")
                results.append({
                    "model": "sdxl",
                    "prompt": prompt,
                    "success": False,
                    "error": str(e)
                })
            
            print()
    
    # Cleanup
    await image_generator.close()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    print(f"✗ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\n✅ Successful generations:")
        for r in successful:
            print(f"   - {r['model'].upper()}: {r['prompt'][:50]}...")
            print(f"     → {r['image_path']}")
    
    if failed:
        print("\n❌ Failed generations:")
        for r in failed:
            print(f"   - {r['model'].upper()}: {r['prompt'][:50]}...")
            print(f"     → Error: {r.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)
    
    return len(successful) > 0


if __name__ == "__main__":
    try:
        success = asyncio.run(test_image_generation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

