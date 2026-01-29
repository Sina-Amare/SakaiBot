"""
Integration Test: Gemini Pro->Flash Fallback with Thinking Mode
Tests the actual SakaiBot code path to ensure thinking mode works when Pro is exhausted.
"""
import asyncio
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


async def test_full_code_path():
    """Test the full code path: GeminiProvider.execute_prompt with use_thinking=True."""
    print("\n" + "="*70)
    print("INTEGRATION TEST: Full Code Path with Thinking Mode")
    print("="*70)
    
    # Import after path setup
    from src.core.config import Config
    from src.ai.providers.gemini import GeminiProvider
    
    # Create config and provider
    config = Config()
    provider = GeminiProvider(config)
    
    print(f"\n[CONFIG]")
    print(f"  Provider configured: {provider.is_configured}")
    print(f"  Pro model: {provider._model_pro}")
    print(f"  Flash model: {provider._model_flash}")
    print(f"  API keys available: {provider._key_manager.num_keys if provider._key_manager else 1}")
    
    # Test prompt
    prompt = "What is the capital of France? Explain briefly."
    
    print(f"\n[TEST] Calling execute_prompt with use_thinking=True")
    print(f"  Prompt: {prompt}")
    print(f"  Task type: 'prompt' (uses Pro model first)")
    print("-" * 50)
    
    try:
        result = await provider.execute_prompt(
            user_prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            task_type="prompt",  # Complex task -> uses Pro first
            use_thinking=True,   # Enable thinking mode
            use_web_search=False
        )
        
        print(f"\n[RESULT]")
        print(f"  Response length: {len(result.response_text)} chars")
        print(f"  Model used: {result.model_used}")
        print(f"  Model fallback applied: {result.model_fallback_applied}")
        print(f"  Model fallback reason: {result.model_fallback_reason}")
        print(f"  Thinking requested: {result.thinking_requested}")
        print(f"  Thinking applied: {result.thinking_applied}")
        print(f"  Thinking summary: {result.thinking_summary[:200] if result.thinking_summary else 'None'}...")
        
        print(f"\n[RESPONSE PREVIEW]")
        print(f"  {result.response_text[:500]}...")
        
        if result.thinking_applied and result.thinking_summary:
            print("\n" + "="*70)
            print("✓ SUCCESS: Thinking mode WORKS with Flash fallback!")
            print("="*70)
        elif result.model_fallback_applied:
            print("\n" + "="*70)
            print("⚠ Flash fallback occurred but thinking NOT applied")
            print("  This indicates the thinking code path is not being reached")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("ℹ Pro model worked (no fallback needed)")
            print("="*70)
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_direct_thinking():
    """Test _execute_with_native_thinking directly."""
    print("\n" + "="*70)
    print("DIRECT TEST: _execute_with_native_thinking method")
    print("="*70)
    
    from src.core.config import Config
    from src.ai.providers.gemini import GeminiProvider
    
    config = Config()
    provider = GeminiProvider(config)
    
    prompt = "What is 5 + 7? Think step by step."
    model = "gemini-2.5-flash"  # Use Flash directly
    
    print(f"\n[TEST] Calling _execute_with_native_thinking directly")
    print(f"  Model: {model}")
    print(f"  Prompt: {prompt}")
    print("-" * 50)
    
    try:
        result = await provider._execute_with_native_thinking(
            prompt=prompt,
            model=model,
            temperature=0.7,
            max_tokens=2000,
            use_web_search=False
        )
        
        print(f"\n[RESULT]")
        print(f"  Response length: {len(result.response_text)} chars")
        print(f"  Thinking applied: {result.thinking_applied}")
        print(f"  Thinking summary length: {len(result.thinking_summary) if result.thinking_summary else 0}")
        
        if result.thinking_summary:
            print(f"\n[THINKING SUMMARY]")
            print(f"  {result.thinking_summary[:300]}...")
        
        print(f"\n[RESPONSE]")
        print(f"  {result.response_text[:300]}...")
        
        if result.thinking_applied and result.thinking_summary:
            print("\n" + "="*70)
            print("✓ SUCCESS: _execute_with_native_thinking works!")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("✗ FAILED: Thinking not applied")
            print("="*70)
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("#  SakaiBot Thinking Mode Integration Test")
    print("#"*70)
    
    # Run tests
    asyncio.run(test_direct_thinking())
    asyncio.run(test_full_code_path())
