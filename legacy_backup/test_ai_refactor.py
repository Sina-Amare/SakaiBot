#!/usr/bin/env python3
"""Test script for refactored AI modules.

This script validates that the refactored AI modules work correctly
and maintain compatibility with the existing functionality.

Usage:
    python test_ai_refactor.py

Requirements:
    - Virtual environment activated
    - Dependencies installed: pip install -r requirements.txt
    - Valid OpenRouter API key in .env file
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, 'src')

try:
    from src.ai import (
        # New modular interfaces
        AIProcessor, STTProcessor, TTSProcessor,
        AIRequest, TranslationRequest, STTRequest, TTSRequest,
        TranslationPrompts, AnalysisPrompts,
        # Legacy compatibility functions
        execute_custom_prompt, translate_text_with_phonetics,
        transcribe_voice_to_text, text_to_speech_edge
    )
    from src.core.config import get_settings
    from src.core.exceptions import AIError, STTError, TTSError
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure:")
    print("1. Virtual environment is activated")
    print("2. Dependencies are installed: pip install -r requirements.txt")
    print("3. You're running from the project root directory")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIRefactorTester:
    """Test suite for refactored AI modules."""
    
    def __init__(self):
        """Initialize tester."""
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = "deepseek/deepseek-chat"
        self.test_results = []
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result.
        
        Args:
            test_name: Name of the test
            passed: Whether test passed
            details: Additional details
        """
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if details:
            result += f": {details}"
        
        print(result)
        self.test_results.append((test_name, passed, details))
    
    async def test_configuration(self) -> bool:
        """Test configuration loading."""
        try:
            settings = get_settings()
            self.log_test_result("Configuration Loading", True, "Settings loaded successfully")
            return True
        except Exception as e:
            self.log_test_result("Configuration Loading", False, str(e))
            return False
    
    async def test_prompt_templates(self) -> bool:
        """Test prompt template functionality."""
        try:
            # Test translation prompt
            prompt = TranslationPrompts.get_translation_prompt(
                text_to_translate="Hello world",
                target_language="Persian",
                source_language="English"
            )
            
            assert "Hello world" in prompt
            assert "Persian" in prompt
            
            # Test analysis prompt
            analysis_prompt = AnalysisPrompts.get_analysis_prompt(
                messages_text="User1: Hello\nUser2: Hi there",
                num_messages=2,
                num_senders=2,
                duration_minutes=5
            )
            
            assert "2 پیام" in analysis_prompt or "2" in analysis_prompt
            
            self.log_test_result("Prompt Templates", True, "All templates generated correctly")
            return True
            
        except Exception as e:
            self.log_test_result("Prompt Templates", False, str(e))
            return False
    
    async def test_ai_processor_initialization(self) -> bool:
        """Test AI processor initialization."""
        try:
            processor = AIProcessor()
            self.log_test_result("AI Processor Init", True, "Processor initialized")
            return True
        except Exception as e:
            self.log_test_result("AI Processor Init", False, str(e))
            return False
    
    async def test_legacy_compatibility(self) -> bool:
        """Test legacy function compatibility."""
        if not self.api_key or "YOUR_" in self.api_key:
            self.log_test_result(
                "Legacy Compatibility", 
                False, 
                "No valid API key for testing"
            )
            return False
        
        try:
            # Test legacy execute_custom_prompt
            response = await execute_custom_prompt(
                api_key=self.api_key,
                model_name=self.model_name,
                user_text_prompt="Say 'Hello from refactored AI!' in one sentence.",
                max_tokens=50,
                temperature=0.7
            )
            
            success = "AI Error:" not in response and len(response.strip()) > 0
            details = f"Response: {response[:100]}..." if success else response
            
            self.log_test_result("Legacy Compatibility", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("Legacy Compatibility", False, str(e))
            return False
    
    async def test_new_ai_interface(self) -> bool:
        """Test new AI processor interface."""
        if not self.api_key or "YOUR_" in self.api_key:
            self.log_test_result(
                "New AI Interface", 
                False, 
                "No valid API key for testing"
            )
            return False
        
        try:
            processor = AIProcessor()
            
            request = AIRequest(
                prompt="Respond with exactly: 'Refactored AI works!'",
                model_name=self.model_name,
                max_tokens=20,
                temperature=0.1
            )
            
            response = await processor.execute_prompt(request)
            
            success = "Refactored AI works" in response.content
            details = f"Response: {response.content[:100]}..." if success else response.content
            
            self.log_test_result("New AI Interface", success, details)
            return success
            
        except Exception as e:
            self.log_test_result("New AI Interface", False, str(e))
            return False
    
    async def test_tts_functionality(self) -> bool:
        """Test TTS functionality."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            # Test legacy function
            success = await text_to_speech_edge(
                text_to_speak="تست عملکرد TTS",
                voice="fa-IR-DilaraNeural",
                output_filename=temp_path,
                rate="+0%",
                volume="+0%"
            )
            
            # Check if file was created
            file_exists = Path(temp_path).exists()
            
            # Cleanup
            try:
                if file_exists:
                    os.unlink(temp_path)
            except Exception:
                pass
            
            overall_success = success and file_exists
            details = "Audio file generated successfully" if overall_success else "Failed to generate audio"
            
            self.log_test_result("TTS Functionality", overall_success, details)
            return overall_success
            
        except Exception as e:
            self.log_test_result("TTS Functionality", False, str(e))
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling in new modules."""
        try:
            processor = AIProcessor()
            
            # Test invalid request
            try:
                invalid_request = AIRequest(
                    prompt="",  # Empty prompt should fail validation
                    model_name="invalid-model"
                )
                await processor.execute_prompt(invalid_request)
                self.log_test_result("Error Handling", False, "Should have failed with empty prompt")
                return False
            except Exception:
                # Expected to fail
                pass
            
            self.log_test_result("Error Handling", True, "Validation errors handled correctly")
            return True
            
        except Exception as e:
            self.log_test_result("Error Handling", False, str(e))
            return False
    
    async def run_all_tests(self) -> None:
        """Run all tests and display results."""
        print("🚀 Starting AI Refactor Tests...\n")
        
        tests = [
            ("Configuration", self.test_configuration),
            ("Prompt Templates", self.test_prompt_templates),
            ("AI Processor Init", self.test_ai_processor_initialization),
            ("Error Handling", self.test_error_handling),
            ("TTS Functionality", self.test_tts_functionality),
            ("Legacy Compatibility", self.test_legacy_compatibility),
            ("New AI Interface", self.test_new_ai_interface),
        ]
        
        for test_name, test_func in tests:
            print(f"Running {test_name} test...")
            try:
                await test_func()
            except Exception as e:
                self.log_test_result(test_name, False, f"Unexpected error: {e}")
            print()
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test results summary."""
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print("📊 Test Results Summary:")
        print("=" * 50)
        
        for test_name, success, details in self.test_results:
            status_emoji = "✅" if success else "❌"
            print(f"{status_emoji} {test_name}")
            if details and not success:
                print(f"   Details: {details}")
        
        print("=" * 50)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Refactoring is successful.")
        else:
            print(f"⚠️ {total - passed} tests failed. Review the issues above.")
        
        print("\n📝 Next Steps:")
        if passed >= total * 0.8:  # 80% pass rate
            print("1. Update import statements in main.py and event_handlers.py")
            print("2. Remove the old ai_processor.py file")
            print("3. Test the full application")
        else:
            print("1. Fix the failing tests")
            print("2. Check configuration and dependencies")
            print("3. Retry the tests")


def check_environment() -> bool:
    """Check if environment is ready for testing."""
    issues = []
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        issues.append("Not in SakaiBot project directory")
    
    # Check if src directory exists
    if not Path("src").exists():
        issues.append("src directory not found")
    
    # Check if AI modules exist
    ai_modules = ["models.py", "processor.py", "prompts.py", "stt.py", "tts.py"]
    for module in ai_modules:
        if not Path(f"src/ai/{module}").exists():
            issues.append(f"Missing AI module: {module}")
    
    if issues:
        print("❌ Environment Issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Environment looks good!")
    return True


def main():
    """Main test runner."""
    print("🧪 SakaiBot AI Refactor Test Suite")
    print("=" * 50)
    
    # Check environment first
    if not check_environment():
        print("\nPlease fix environment issues before running tests.")
        sys.exit(1)
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or "YOUR_" in api_key:
        print("⚠️ Warning: No valid OpenRouter API key found.")
        print("API-dependent tests will be skipped.")
        print("To test full functionality, set OPENROUTER_API_KEY in .env file.")
        print()
    
    # Run tests
    tester = AIRefactorTester()
    asyncio.run(tester.run_all_tests())


if __name__ == "__main__":
    main()
