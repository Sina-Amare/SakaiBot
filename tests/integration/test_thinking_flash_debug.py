"""
Test: Thinking Mode Flash Fallback Debug

This test simulates and debugs the scenario where:
1. Pro model is exhausted (429)
2. System falls back to Flash
3. Thinking mode should work with Flash but doesn't

Run: python tests/integration/test_thinking_flash_debug.py
"""
import asyncio
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_direct_flash_thinking():
    """
    Test 1: Call _execute_with_native_thinking directly with Flash model.
    
    This bypasses all fallback logic to verify Flash+thinking works.
    """
    print("\n" + "="*70)
    print("TEST 1: Direct Flash Model + Thinking Mode")
    print("="*70)
    
    from src.core.config import Config
    from src.ai.providers.gemini import GeminiProvider
    
    config = Config()
    provider = GeminiProvider(config)
    
    # Force Flash model
    model = provider._model_flash
    prompt = "What is 2+2? Think step by step and explain your reasoning."
    
    print(f"\n[CONFIG]")
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
        print(f"  thinking_requested: {result.thinking_requested}")
        print(f"  thinking_applied: {result.thinking_applied}")
        print(f"  thinking_summary: {result.thinking_summary[:200] if result.thinking_summary else 'None'}...")
        print(f"  response_text length: {len(result.response_text)}")
        print(f"  model_used: {result.model_used}")
        
        if result.thinking_applied and result.thinking_summary:
            print("\n✓ SUCCESS: Flash + Thinking works directly!")
            return True
        else:
            print("\n✗ FAIL: Flash + Thinking did NOT work directly!")
            print("   This means the API is not returning thinking parts")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simulated_fallback():
    """
    Test 2: Simulate Pro exhaustion and fallback to Flash with thinking.
    
    This tests the actual execute_prompt code path.
    """
    print("\n" + "="*70)
    print("TEST 2: Simulated Pro->Flash Fallback with Thinking")
    print("="*70)
    
    from src.core.config import Config
    from src.ai.providers.gemini import GeminiProvider
    
    config = Config()
    provider = GeminiProvider(config)
    
    # Manually mark Pro as exhausted to force Flash fallback
    provider._mark_pro_model_exhausted()
    
    print(f"\n[SETUP]")
    print(f"  _pro_model_exhausted_until: {provider._pro_model_exhausted_until}")
    print(f"  _is_pro_model_exhausted(): {provider._is_pro_model_exhausted()}")
    print(f"  Model for 'prompt' task: {provider.get_model_for_task('prompt')}")
    
    prompt = "What is 5+5? Think carefully and explain."
    
    print(f"\n[TEST]")
    print(f"  Calling execute_prompt with use_thinking=True")
    print(f"  Expected: Flash model with thinking mode applied")
    print("-" * 50)
    
    try:
        result = await provider.execute_prompt(
            user_prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            task_type="prompt",  # Complex task (normally Pro)
            use_thinking=True,
            use_web_search=False
        )
        
        print(f"\n[RESULT]")
        print(f"  thinking_requested: {result.thinking_requested}")
        print(f"  thinking_applied: {result.thinking_applied}")
        print(f"  thinking_summary: {result.thinking_summary[:200] if result.thinking_summary else 'None'}...")
        print(f"  model_used: {result.model_used}")
        print(f"  model_fallback_applied: {result.model_fallback_applied}")
        print(f"  model_fallback_reason: {result.model_fallback_reason}")
        
        if result.thinking_applied and result.thinking_summary:
            print("\n✓ SUCCESS: Simulated fallback with thinking works!")
            return True
        else:
            print("\n✗ FAIL: Simulated fallback did NOT apply thinking!")
            print("   Response received but thinking_applied=False")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_key_reset_behavior():
    """
    Test 3: Verify key reset behavior when switching models.
    
    This tests that reset_for_model_switch() properly resets keys.
    """
    print("\n" + "="*70)
    print("TEST 3: Key Reset Behavior After Model Switch")
    print("="*70)
    
    from src.core.config import Config
    from src.ai.providers.gemini import GeminiProvider
    
    config = Config()
    provider = GeminiProvider(config)
    
    if not provider._key_manager:
        print("  No key manager - single key mode")
        return True
    
    km = provider._key_manager
    
    print(f"\n[INITIAL STATE]")
    print(f"  num_keys: {km.num_keys}")
    print(f"  current_key available: {km.get_current_key() is not None}")
    
    # Simulate exhausting all keys
    print(f"\n[SIMULATING KEY EXHAUSTION]")
    for i in range(km.num_keys):
        km.mark_key_exhausted_for_day()
        print(f"  Key {i+1} marked exhausted")
    
    print(f"\n[AFTER EXHAUSTION]")
    print(f"  all_keys_exhausted: {km.all_keys_exhausted()}")
    print(f"  get_current_key(): {km.get_current_key()}")
    
    # Reset for model switch
    print(f"\n[CALLING reset_for_model_switch()]")
    km.reset_for_model_switch()
    
    print(f"\n[AFTER RESET]")
    print(f"  all_keys_exhausted: {km.all_keys_exhausted()}")
    print(f"  get_current_key(): {km.get_current_key()[:8] if km.get_current_key() else None}...")
    
    if not km.all_keys_exhausted() and km.get_current_key():
        print("\n✓ SUCCESS: Keys reset properly!")
        return True
    else:
        print("\n✗ FAIL: Keys did not reset!")
        return False


async def main():
    print("\n" + "#"*70)
    print("#  THINKING MODE FLASH FALLBACK DEBUG")
    print("#"*70)
    
    results = {}
    
    # Test 1: Direct Flash + Thinking
    results["direct_flash_thinking"] = await test_direct_flash_thinking()
    
    # Test 2: Simulated fallback
    results["simulated_fallback"] = await test_simulated_fallback()
    
    # Test 3: Key reset behavior
    results["key_reset"] = await test_key_reset_behavior()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("="*70))
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - Check logs above for [DEBUG-THINKING] messages")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
