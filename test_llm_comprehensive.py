#!/usr/bin/env python3
"""Comprehensive LLM Provider Testing Script."""

import asyncio
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_settings
from src.ai.processor import AIProcessor
from src.utils.logging import get_logger, setup_logging

# Setup logging
setup_logging(enable_console=True)
logger = get_logger("LLMTest")


class LLMProviderTester:
    """Comprehensive LLM provider testing."""
    
    def __init__(self):
        self.config = get_settings()
        self.results = {
            "gemini": {"status": "not_tested", "tests": {}},
            "openrouter": {"status": "not_tested", "tests": {}}
        }
        
    async def test_provider(self, provider_name: str) -> bool:
        """Test a specific provider comprehensively."""
        print(f"\n{'='*60}")
        print(f"Testing {provider_name.upper()} Provider")
        print(f"{'='*60}")
        
        # Update config for this provider
        original_provider = self.config.llm_provider
        self.config.llm_provider = provider_name
        
        try:
            processor = AIProcessor(self.config)
            
            if not processor.is_configured:
                print(f"❌ {provider_name} is not configured. Skipping...")
                self.results[provider_name]["status"] = "not_configured"
                return False
            
            print(f"✅ Provider: {processor.provider_name}")
            print(f"✅ Model: {processor.model_name}")
            print(f"✅ Configured: {processor.is_configured}")
            
            # Run all tests
            all_passed = True
            
            # Test 1: Simple Persian prompt
            test_name = "simple_persian"
            print(f"\n📝 Test 1: Simple Persian prompt...")
            try:
                start = time.time()
                response = await processor.execute_custom_prompt(
                    "یه جوک کوتاه فارسی بگو",
                    max_tokens=200,
                    temperature=0.7
                )
                elapsed = time.time() - start
                
                if response and len(response) > 10:
                    print(f"✅ Response received ({len(response)} chars in {elapsed:.2f}s)")
                    print(f"   Preview: {response[:100]}...")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response)
                    }
                else:
                    print(f"❌ Empty or invalid response")
                    self.results[provider_name]["tests"][test_name] = {"passed": False, "error": "Empty response"}
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Test 2: Translation with phonetics
            test_name = "translation"
            print(f"\n📝 Test 2: Translation with phonetics...")
            try:
                start = time.time()
                response = await processor.translate_text_with_phonetics(
                    "Good morning, how are you today?",
                    target_language="Persian",
                    source_language="English"
                )
                elapsed = time.time() - start
                
                if response and "Translation:" in response:
                    print(f"✅ Translation received ({len(response)} chars in {elapsed:.2f}s)")
                    print(f"   Response: {response}")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response)
                    }
                else:
                    print(f"❌ Invalid translation response")
                    self.results[provider_name]["tests"][test_name] = {"passed": False, "error": "Invalid format"}
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Test 3: Small message analysis (10 messages)
            test_name = "small_analysis"
            print(f"\n📝 Test 3: Small message analysis (10 messages)...")
            try:
                messages = []
                participants = {}
                for i in range(10):
                    messages.append({
                        "date": f"2024-01-01T10:{i:02d}:00Z",
                        "from_id": i % 3,
                        "text": f"پیام تست شماره {i+1} از کاربر {(i % 3) + 1}"
                    })
                    participants[i % 3] = f"کاربر_{(i % 3) + 1}"
                
                start = time.time()
                response = await processor.analyze_messages(
                    messages=messages,
                    participant_mapping=participants,
                    max_messages=10
                )
                elapsed = time.time() - start
                
                if response and len(response) > 50:
                    print(f"✅ Analysis received ({len(response)} chars in {elapsed:.2f}s)")
                    print(f"   Preview: {response[:200]}...")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response),
                        "message_count": 10
                    }
                else:
                    print(f"❌ Invalid analysis response")
                    self.results[provider_name]["tests"][test_name] = {"passed": False, "error": "Too short"}
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Test 4: Medium message analysis (100 messages)
            test_name = "medium_analysis"
            print(f"\n📝 Test 4: Medium message analysis (100 messages)...")
            try:
                messages = []
                participants = {}
                for i in range(100):
                    hour = 10 + (i // 60)
                    minute = i % 60
                    messages.append({
                        "date": f"2024-01-01T{hour:02d}:{minute:02d}:00Z",
                        "from_id": i % 5,
                        "text": f"این پیام شماره {i+1} است. موضوع: {'کار' if i % 3 == 0 else 'تفریح' if i % 3 == 1 else 'خانواده'}"
                    })
                    participants[i % 5] = f"شخص_{(i % 5) + 1}"
                
                start = time.time()
                response = await processor.analyze_messages(
                    messages=messages,
                    participant_mapping=participants,
                    max_messages=100
                )
                elapsed = time.time() - start
                
                if response and len(response) > 100:
                    print(f"✅ Analysis received ({len(response)} chars in {elapsed:.2f}s)")
                    print(f"   Preview: {response[:200]}...")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response),
                        "message_count": 100
                    }
                else:
                    print(f"❌ Invalid analysis response")
                    self.results[provider_name]["tests"][test_name] = {"passed": False, "error": "Too short"}
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Test 5: Large prompt (1000 messages - stress test)
            test_name = "large_analysis"
            print(f"\n📝 Test 5: Large message analysis (1000 messages - stress test)...")
            try:
                messages = []
                participants = {}
                topics = ["کار", "تفریح", "ورزش", "سینما", "موسیقی", "غذا", "سفر", "تکنولوژی"]
                
                for i in range(1000):
                    day = 1 + (i // 500)
                    hour = 8 + ((i % 500) // 60)
                    minute = i % 60
                    topic = topics[i % len(topics)]
                    user_id = i % 10
                    
                    messages.append({
                        "date": f"2024-01-{day:02d}T{hour:02d}:{minute:02d}:00Z",
                        "from_id": user_id,
                        "text": f"پیام {i+1}: در مورد {topic} صحبت می‌کنیم. {'سوال دارم' if i % 5 == 0 else 'نظر من اینه که' if i % 3 == 0 else 'موافقم'}"
                    })
                    participants[user_id] = f"کاربر_{user_id + 1}"
                
                start = time.time()
                response = await processor.analyze_messages(
                    messages=messages,
                    participant_mapping=participants,
                    max_messages=1000
                )
                elapsed = time.time() - start
                
                if response and len(response) > 200:
                    print(f"✅ Analysis received ({len(response)} chars in {elapsed:.2f}s)")
                    print(f"   Preview: {response[:300]}...")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response),
                        "message_count": 1000
                    }
                else:
                    print(f"❌ Invalid analysis response")
                    self.results[provider_name]["tests"][test_name] = {"passed": False, "error": "Too short"}
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Test 6: Verify Persian response (Bill Burr style check)
            test_name = "persian_style"
            print(f"\n📝 Test 6: Persian comedian style check...")
            try:
                start = time.time()
                response = await processor.execute_custom_prompt(
                    "چرا آدما انقدر به گوشیشون وابسته شدن؟",
                    max_tokens=500,
                    temperature=0.8,
                    system_message="You are a Persian standup comedian like Bill Burr. ALWAYS respond in Persian/Farsi."
                )
                elapsed = time.time() - start
                
                # Check if response is in Persian and has humor indicators
                persian_chars = sum(1 for c in response if '\u0600' <= c <= '\u06FF')
                persian_ratio = persian_chars / len(response) if response else 0
                
                if response and persian_ratio > 0.5:
                    print(f"✅ Persian response received ({len(response)} chars, {persian_ratio:.1%} Persian)")
                    print(f"   Time: {elapsed:.2f}s")
                    print(f"   Preview: {response[:200]}...")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": True,
                        "time": elapsed,
                        "response_length": len(response),
                        "persian_ratio": persian_ratio
                    }
                else:
                    print(f"❌ Response not in Persian (ratio: {persian_ratio:.1%})")
                    self.results[provider_name]["tests"][test_name] = {
                        "passed": False,
                        "error": f"Not Persian (ratio: {persian_ratio:.1%})"
                    }
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.results[provider_name]["tests"][test_name] = {"passed": False, "error": str(e)}
                all_passed = False
            
            # Final result
            self.results[provider_name]["status"] = "passed" if all_passed else "failed"
            
            print(f"\n{'='*60}")
            if all_passed:
                print(f"✅ ALL TESTS PASSED for {provider_name}!")
            else:
                failed_tests = [k for k, v in self.results[provider_name]["tests"].items() if not v.get("passed")]
                print(f"❌ Some tests failed for {provider_name}: {', '.join(failed_tests)}")
            
            await processor.close()
            return all_passed
            
        except Exception as e:
            print(f"❌ Fatal error testing {provider_name}: {e}")
            logger.error(f"Fatal error in {provider_name}", exc_info=True)
            self.results[provider_name]["status"] = "error"
            self.results[provider_name]["error"] = str(e)
            return False
        finally:
            # Restore original provider
            self.config.llm_provider = original_provider
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("FINAL TEST SUMMARY")
        print(f"{'='*60}")
        
        for provider, data in self.results.items():
            status_icon = "✅" if data["status"] == "passed" else "❌" if data["status"] == "failed" else "⚠️"
            print(f"\n{status_icon} {provider.upper()}: {data['status']}")
            
            if data["tests"]:
                passed = sum(1 for t in data["tests"].values() if t.get("passed"))
                total = len(data["tests"])
                print(f"   Tests: {passed}/{total} passed")
                
                for test_name, test_data in data["tests"].items():
                    if test_data.get("passed"):
                        time_str = f"{test_data.get('time', 0):.2f}s" if 'time' in test_data else "N/A"
                        print(f"   ✅ {test_name}: {time_str}")
                    else:
                        error = test_data.get("error", "Unknown error")[:50]
                        print(f"   ❌ {test_name}: {error}")
        
        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n📊 Detailed results saved to: {results_file}")
        
        # Overall verdict
        all_passed = all(
            data["status"] == "passed" 
            for data in self.results.values() 
            if data["status"] != "not_tested"
        )
        
        if all_passed:
            print(f"\n🎉 SUCCESS: All configured providers are working correctly!")
            return True
        else:
            print(f"\n⚠️ WARNING: Some providers have issues. Check the details above.")
            return False


async def main():
    """Main test runner."""
    print("🚀 Comprehensive LLM Provider Testing")
    print("This will test both Gemini and OpenRouter providers thoroughly.")
    print("-" * 60)
    
    tester = LLMProviderTester()
    
    # Test both providers
    providers_to_test = ["gemini", "openrouter"]
    
    for provider in providers_to_test:
        await tester.test_provider(provider)
        # Small delay between providers
        await asyncio.sleep(1)
    
    # Print summary
    success = tester.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error("Fatal error in test runner", exc_info=True)
        sys.exit(1)