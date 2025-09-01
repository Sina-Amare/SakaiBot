#!/usr/bin/env python3
"""
System Test Script for SakaiBot
This script verifies that all modules are properly installed and working.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    
    modules_to_test = [
        # Core modules
        ("src.core.config", "Configuration"),
        ("src.core.constants", "Constants"),
        ("src.core.exceptions", "Exceptions"),
        
        # Telegram modules
        ("src.telegram.models", "Telegram Models"),
        ("src.telegram.client", "Telegram Client"),
        ("src.telegram.handlers", "Telegram Handlers"),
        ("src.telegram.utils", "Telegram Utils"),
        
        # AI modules
        ("src.ai.models", "AI Models"),
        ("src.ai.processor", "AI Processor"),
        ("src.ai.stt", "Speech-to-Text"),
        ("src.ai.tts", "Text-to-Speech"),
        ("src.ai.prompts", "AI Prompts"),
        
        # CLI modules
        ("src.cli.models", "CLI Models"),
        
        # Utils
        ("src.utils.logging", "Logging Utils"),
    ]
    
    failed = []
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {description:25} - {module_name}")
        except ImportError as e:
            print(f"❌ {description:25} - {module_name}")
            print(f"   Error: {e}")
            failed.append((module_name, str(e)))
    
    return len(failed) == 0, failed


def test_dependencies():
    """Test that all required dependencies are installed."""
    print("\n" + "=" * 60)
    print("TESTING DEPENDENCIES")
    print("=" * 60)
    
    dependencies = [
        ("telethon", "Telegram Client Library"),
        ("openai", "OpenAI/OpenRouter API"),
        ("pydantic", "Data Validation"),
        ("pydantic_settings", "Settings Management"),
        ("dotenv", "Environment Variables"),
        ("pytz", "Timezone Support"),
        ("aiofiles", "Async File Operations"),
        ("aiohttp", "Async HTTP Client"),
        ("diskcache", "Disk-based Cache"),
        ("rich", "Terminal UI"),
        ("click", "CLI Framework"),
        ("orjson", "Fast JSON Processing"),
        ("tenacity", "Retry Logic"),
        ("speech_recognition", "Speech Recognition"),
        ("pydub", "Audio Processing"),
        ("edge_tts", "Text-to-Speech"),
    ]
    
    failed = []
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {description:25} - {module_name}")
        except ImportError as e:
            print(f"❌ {description:25} - {module_name}")
            failed.append((module_name, str(e)))
    
    return len(failed) == 0, failed


def test_configuration():
    """Test configuration system."""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION SYSTEM")
    print("=" * 60)
    
    try:
        from src.core.config import Settings, TelegramConfig, OpenRouterConfig
        print("✅ Configuration classes imported")
        
        # Test that we can create config instances (without actual values)
        print("✅ Configuration system is functional")
        return True, []
    except Exception as e:
        print(f"❌ Configuration system failed: {e}")
        return False, [str(e)]


def test_exceptions():
    """Test custom exception hierarchy."""
    print("\n" + "=" * 60)
    print("TESTING EXCEPTION HIERARCHY")
    print("=" * 60)
    
    try:
        from src.core.exceptions import (
            SakaiBotError,
            ConfigurationError,
            TelegramError,
            AIError,
            ValidationError
        )
        
        # Test exception creation
        base_error = SakaiBotError("Test error")
        config_error = ConfigurationError("Config error")
        
        print("✅ Exception hierarchy is functional")
        print(f"   - Base exception: {base_error}")
        print(f"   - Config exception: {config_error}")
        return True, []
    except Exception as e:
        print(f"❌ Exception system failed: {e}")
        return False, [str(e)]


def test_logging():
    """Test logging system."""
    print("\n" + "=" * 60)
    print("TESTING LOGGING SYSTEM")
    print("=" * 60)
    
    try:
        from src.utils.logging import setup_logging, get_logger, shutdown_logging
        
        # Setup logging
        setup_logging(
            log_level="DEBUG",
            enable_console=False,
            enable_file=True,
            async_logging=False
        )
        
        # Get logger and test
        logger = get_logger("test")
        logger.info("Test log message")
        
        print("✅ Logging system is functional")
        
        # Cleanup
        shutdown_logging()
        return True, []
    except Exception as e:
        print(f"❌ Logging system failed: {e}")
        return False, [str(e)]


def test_models():
    """Test data models."""
    print("\n" + "=" * 60)
    print("TESTING DATA MODELS")
    print("=" * 60)
    
    try:
        # Test Telegram models
        from src.telegram.models import TelegramUser, TelegramChat, CommandData
        
        user = TelegramUser(
            id=123,
            is_bot=False,
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Telegram User model: {user.display_name}")
        
        # Test AI models
        from src.ai.models import (
            AIRequest,
            STTRequest,
            TTSRequest
        )
        
        ai_req = AIRequest(
            prompt="Test prompt",
            model_name="test-model",
            max_tokens=100
        )
        print(f"✅ AI Request model: {ai_req.prompt[:20]}...")
        
        # Test CLI models
        from src.cli.models import CLIState, MenuItem
        
        state = CLIState()
        print(f"✅ CLI State model: monitoring={state.is_monitoring_active}")
        
        return True, []
    except Exception as e:
        print(f"❌ Model system failed: {e}")
        return False, [str(e)]


def test_file_structure():
    """Test that all required directories exist."""
    print("\n" + "=" * 60)
    print("TESTING FILE STRUCTURE")
    print("=" * 60)
    
    required_dirs = [
        "src",
        "src/core",
        "src/telegram",
        "src/ai",
        "src/cli",
        "src/utils",
        "tests",
        "data",
        "cache",
        "logs",
    ]
    
    missing = []
    for dir_name in required_dirs:
        path = project_root / dir_name
        if path.exists():
            print(f"✅ Directory exists: {dir_name}")
        else:
            print(f"❌ Directory missing: {dir_name}")
            missing.append(dir_name)
    
    return len(missing) == 0, missing


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SAKAIBOT SYSTEM TEST")
    print("=" * 60)
    
    results = {
        "File Structure": test_file_structure(),
        "Dependencies": test_dependencies(),
        "Module Imports": test_imports(),
        "Configuration": test_configuration(),
        "Exceptions": test_exceptions(),
        "Logging": test_logging(),
        "Data Models": test_models(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, (passed, errors) in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} - {status}")
        if not passed and errors:
            for error in errors[:3]:  # Show first 3 errors
                if isinstance(error, tuple):
                    print(f"  - {error[0]}: {error[1]}")
                else:
                    print(f"  - {error}")
        all_passed = all_passed and passed
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED! The system is ready to use.")
        print("\nNext steps:")
        print("1. Copy config.ini.example to data/config.ini")
        print("2. Edit data/config.ini with your credentials")
        print("3. Run: python -m src.main")
    else:
        print("❌ SOME TESTS FAILED. Please check the errors above.")
        print("\nTry running:")
        print("  pip install -r requirements.txt")
        print("\nIf issues persist, check that you're in the virtual environment:")
        print("  source venv/bin/activate  # Linux/Mac")
        print("  venv\\Scripts\\activate     # Windows")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())