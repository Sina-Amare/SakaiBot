#!/usr/bin/env python3
"""Test script for LLM providers."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
from src.ai.processor import AIProcessor


async def test_provider(provider_name: str, api_key: str = None):
    """Test a specific LLM provider."""
    print(f"\n{'='*50}")
    print(f"Testing {provider_name.upper()} Provider")
    print('='*50)
    
    try:
        # Create a test config
        if provider_name == "gemini" and api_key:
            # Override config for testing
            import os
            os.environ["LLM_PROVIDER"] = "gemini"
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GEMINI_MODEL_NAME"] = "gemini-2.0-flash"
        
        # Load config
        from src.core.config import load_config
        config = load_config()
        
        if provider_name == "gemini" and api_key:
            config.llm_provider = "gemini"
            config.gemini_api_key = api_key
            config.gemini_model_name = "gemini-2.0-flash"
        
        print(f"Provider: {config.llm_provider}")
        print(f"AI Enabled: {config.is_ai_enabled}")
        
        if not config.is_ai_enabled:
            print(f"❌ {provider_name} is not configured properly")
            return False
        
        # Initialize AI processor
        processor = AIProcessor(config)
        print(f"✅ Initialized {processor.provider_name}")
        print(f"Model: {processor.model_name}")
        
        # Test 1: Simple prompt
        print("\n📝 Test 1: Simple prompt")
        response = await processor.execute_custom_prompt(
            "What is 2+2? Answer in one word.",
            max_tokens=50,
            temperature=0.1
        )
        print(f"Response: {response[:100]}")
        
        # Test 2: Translation
        print("\n🌐 Test 2: Translation")
        translation = await processor.translate_text_with_phonetics(
            "Hello, how are you?",
            "persian"
        )
        print(f"Translation: {translation[:200]}")
        
        print(f"\n✅ {provider_name.upper()} provider tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing {provider_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("LLM Provider Test Suite")
    print("="*50)
    
    # Test OpenRouter (if configured)
    print("\n1. Testing OpenRouter provider...")
    openrouter_success = await test_provider("openrouter")
    
    # Test Gemini (you'll need to provide API key)
    print("\n2. Testing Gemini provider...")
    print("To test Gemini, you need to provide an API key.")
    print("You can get one from: https://aistudio.google.com/apikey")
    
    gemini_api_key = input("Enter Gemini API key (or press Enter to skip): ").strip()
    
    if gemini_api_key:
        gemini_success = await test_provider("gemini", gemini_api_key)
    else:
        print("Skipping Gemini test (no API key provided)")
        gemini_success = None
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"OpenRouter: {'✅ Passed' if openrouter_success else '❌ Failed'}")
    if gemini_success is not None:
        print(f"Gemini: {'✅ Passed' if gemini_success else '❌ Failed'}")
    else:
        print("Gemini: ⏭️ Skipped")


if __name__ == "__main__":
    asyncio.run(main())