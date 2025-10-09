#!/usr/bin/env python3
"""Test script for AI providers."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_settings
from src.ai.processor import AIProcessor
from src.utils.logging import get_logger

logger = get_logger("AIProviderTest")


async def test_provider(provider_name: str):
    """Test an AI provider with various prompts."""
    config = get_settings()
    
    # Override provider if specified
    if provider_name:
        config.llm_provider = provider_name
    
    try:
        # Initialize processor
        processor = AIProcessor(config)
        
        if not processor.is_configured:
            print(f"❌ {provider_name} is not configured. Please check your API keys.")
            return False
        
        print(f"\n✅ Testing {processor.provider_name} with model {processor.model_name}")
        
        # Test 1: Simple prompt
        print("\n📝 Test 1: Simple prompt...")
        response = await processor.execute_custom_prompt(
            "سلام! یه جوک فارسی بگو",
            max_tokens=500,
            temperature=0.7
        )
        print(f"Response (first 200 chars): {response[:200]}...")
        
        # Test 2: Translation with phonetics
        print("\n📝 Test 2: Translation...")
        response = await processor.translate_text_with_phonetics(
            "Hello, how are you?",
            target_language="Persian",
            source_language="English"
        )
        print(f"Translation response: {response}")
        
        # Test 3: Small message analysis
        print("\n📝 Test 3: Small message analysis...")
        test_messages = [
            {"timestamp": "2024-01-01T10:00:00Z", "sender_name": "علی", "text": "سلام چطوری؟"},
            {"timestamp": "2024-01-01T10:01:00Z", "sender_name": "محمد", "text": "خوبم مرسی، تو چطوری؟"},
            {"timestamp": "2024-01-01T10:02:00Z", "sender_name": "علی", "text": "منم خوبم. فردا میای؟"},
        ]
        
        response = await processor.analyze_messages(
            messages=[
                {"date": msg["timestamp"], "from_id": i, "text": msg["text"]} 
                for i, msg in enumerate(test_messages)
            ],
            participant_mapping={i: msg["sender_name"] for i, msg in enumerate(test_messages)},
            max_messages=10
        )
        print(f"Analysis response (first 300 chars): {response[:300]}...")
        
        print(f"\n✅ All tests passed for {provider_name}!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing {provider_name}: {e}")
        logger.error(f"Test failed for {provider_name}", exc_info=True)
        return False
    finally:
        if 'processor' in locals():
            await processor.close()


async def main():
    """Main test function."""
    print("🚀 Testing AI Providers...")
    
    config = get_settings()
    current_provider = config.llm_provider
    
    # Test current provider
    print(f"\n=== Testing current provider: {current_provider} ===")
    success = await test_provider(current_provider)
    
    # Optionally test the other provider
    other_provider = "openrouter" if current_provider == "gemini" else "gemini"
    
    response = input(f"\nDo you want to test {other_provider} as well? (y/n): ")
    if response.lower() == 'y':
        print(f"\n=== Testing {other_provider} ===")
        await test_provider(other_provider)
    
    print("\n✨ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())