#!/usr/bin/env python3
"""Test script for LLM providers."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config
from src.ai.processor import AIProcessor


async def test_current_provider():
    """Test the currently configured LLM provider."""
    print("\n" + "="*60)
    print("Testing Currently Configured LLM Provider")
    print("="*60)
    
    try:
        # Load configuration
        config = load_config()
        
        print(f"Provider: {config.llm_provider}")
        
        if config.llm_provider == "gemini":
            print(f"Model: {config.gemini_model}")
            print(f"API Key configured: {bool(config.gemini_api_key)}")
        else:
            print(f"Model: {config.openrouter_model}")
            print(f"API Key configured: {bool(config.openrouter_api_key)}")
        
        print(f"AI Enabled: {config.is_ai_enabled}")
        
        if not config.is_ai_enabled:
            print("\n❌ AI is not properly configured!")
            return False
        
        # Initialize processor
        processor = AIProcessor(config)
        print(f"\n✅ Initialized {processor.provider_name}")
        
        # Test 1: Simple generation
        print("\n📝 Test 1: Simple generation")
        print("Prompt: 'What is 2+2? Reply with just the number.'")
        response = await processor.execute_custom_prompt(
            "What is 2+2? Reply with just the number.",
            max_tokens=10,
            temperature=0.1
        )
        print(f"Response: {response}")
        
        # Test 2: Translation
        print("\n🌐 Test 2: Translation to Persian")
        print("Text: 'Hello friend'")
        translation = await processor.translate_text_with_phonetics(
            "Hello friend",
            "persian"
        )
        print(f"Translation: {translation[:200]}...")
        
        print(f"\n✅ All tests passed for {processor.provider_name}!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def switch_and_test(provider: str):
    """Switch to a different provider and test it."""
    print(f"\n{'='*60}")
    print(f"Switching to {provider.upper()} provider")
    print('='*60)
    
    import os
    os.environ["LLM_PROVIDER"] = provider
    
    # Force reload config
    from src.core import config as config_module
    config_module.settings = None  # Reset cached settings
    
    return await test_current_provider()


async def main():
    """Main test function."""
    print("\n" + "🤖 LLM Provider Test Suite 🤖".center(60))
    
    # Test current provider
    current_success = await test_current_provider()
    
    # Ask if user wants to test the other provider
    print("\n" + "-"*60)
    response = input("\nDo you want to test the other provider? (y/n): ").strip().lower()
    
    if response == 'y':
        config = load_config()
        other_provider = "openrouter" if config.llm_provider == "gemini" else "gemini"
        
        if other_provider == "gemini":
            print("\n⚠️  Note: You need 'google-genai' installed:")
            print("   pip install google-genai")
        
        other_success = await switch_and_test(other_provider)
    else:
        other_success = None
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY".center(60))
    print("="*60)
    
    config = load_config()
    print(f"Current provider ({config.llm_provider}): {'✅ Passed' if current_success else '❌ Failed'}")
    
    if other_success is not None:
        other_name = "openrouter" if config.llm_provider == "gemini" else "gemini"
        print(f"Other provider ({other_name}): {'✅ Passed' if other_success else '❌ Failed'}")


if __name__ == "__main__":
    print("\n⚠️  Prerequisites:")
    print("1. Make sure you have google-genai installed for Gemini:")
    print("   pip install google-genai")
    print("2. Your .env file should have the necessary API keys")
    print("")
    
    asyncio.run(main())