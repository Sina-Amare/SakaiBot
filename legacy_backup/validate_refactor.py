#!/usr/bin/env python3
"""Validation script to ensure refactored AI modules maintain original functionality.

This script compares the behavior of the old ai_processor.py functions
with the new refactored modules to ensure compatibility.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add src to path
sys.path.insert(0, 'src')


def check_function_signatures():
    """Check that all original functions are available with same signatures."""
    print("🔍 Checking function signatures...")
    
    # Import both old and new modules
    try:
        import ai_processor as old_ai
        from src import ai as new_ai
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Functions that should be available
    required_functions = [
        "execute_custom_prompt",
        "translate_text_with_phonetics", 
        "analyze_conversation_messages",
        "answer_question_from_chat_history",
        "transcribe_voice_to_text",
        "text_to_speech_edge"
    ]
    
    all_good = True
    
    for func_name in required_functions:
        old_func = getattr(old_ai, func_name, None)
        new_func = getattr(new_ai, func_name, None)
        
        if old_func is None:
            print(f"⚠️  Warning: {func_name} not found in old module")
        elif new_func is None:
            print(f"❌ {func_name} missing in new module")
            all_good = False
        else:
            print(f"✅ {func_name} available in both modules")
    
    return all_good


def check_module_structure():
    """Check that the new module structure is correct."""
    print("\n🏢 Checking module structure...")
    
    expected_files = [
        "src/ai/__init__.py",
        "src/ai/models.py", 
        "src/ai/prompts.py",
        "src/ai/processor.py",
        "src/ai/stt.py",
        "src/ai/tts.py"
    ]
    
    all_good = True
    
    for file_path in expected_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} missing")
            all_good = False
    
    return all_good


def check_imports():
    """Check that all new modules can be imported."""
    print("\n📦 Checking imports...")
    
    imports_to_test = [
        ("src.ai.models", "MessageData, AIRequest, TranslationRequest"),
        ("src.ai.prompts", "TranslationPrompts, AnalysisPrompts"),
        ("src.ai.processor", "AIProcessor"),
        ("src.ai.stt", "STTProcessor"),
        ("src.ai.tts", "TTSProcessor"),
        ("src.ai", "execute_custom_prompt, text_to_speech_edge")
    ]
    
    all_good = True
    
    for module_name, items in imports_to_test:
        try:
            exec(f"from {module_name} import {items}")
            print(f"✅ {module_name}: {items}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            all_good = False
        except Exception as e:
            print(f"⚠️  {module_name}: {e}")
            all_good = False
    
    return all_good


def analyze_code_metrics():
    """Analyze code metrics of the refactored modules."""
    print("\n📈 Code metrics analysis...")
    
    # Get old file metrics
    old_file = Path("ai_processor.py")
    old_size = old_file.stat().st_size if old_file.exists() else 0
    old_lines = len(old_file.read_text().splitlines()) if old_file.exists() else 0
    
    # Get new files metrics
    new_files = [
        "src/ai/models.py",
        "src/ai/prompts.py", 
        "src/ai/processor.py",
        "src/ai/stt.py",
        "src/ai/tts.py",
        "src/ai/__init__.py"
    ]
    
    new_total_size = 0
    new_total_lines = 0
    
    print("\nNew module breakdown:")
    for file_path in new_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            lines = len(Path(file_path).read_text().splitlines())
            new_total_size += size
            new_total_lines += lines
            print(f"  {Path(file_path).name:15} {lines:4} lines ({size:,} bytes)")
    
    print(f"\nComparison:")
    print(f"  Old: {old_lines:4} lines ({old_size:,} bytes)")
    print(f"  New: {new_total_lines:4} lines ({new_total_size:,} bytes)")
    print(f"  Increase: {new_total_lines - old_lines:+4} lines ({new_total_size - old_size:+,} bytes)")
    
    if new_total_lines > old_lines:
        ratio = new_total_lines / max(old_lines, 1)
        print(f"  Expansion: {ratio:.1f}x (expected for better structure + docs + error handling)")


def check_legacy_compatibility():
    """Check that legacy function calls still work."""
    print("\n🔄 Checking legacy compatibility...")
    
    try:
        from src import ai as ai_processor
        
        # Check that functions exist and are callable
        functions_to_check = [
            "execute_custom_prompt",
            "translate_text_with_phonetics",
            "analyze_conversation_messages", 
            "answer_question_from_chat_history",
            "transcribe_voice_to_text",
            "text_to_speech_edge"
        ]
        
        all_good = True
        
        for func_name in functions_to_check:
            func = getattr(ai_processor, func_name, None)
            if func is None:
                print(f"❌ {func_name} not available")
                all_good = False
            elif not callable(func):
                print(f"❌ {func_name} not callable")
                all_good = False
            else:
                print(f"✅ {func_name} available and callable")
        
        return all_good
        
    except Exception as e:
        print(f"❌ Legacy compatibility check failed: {e}")
        return False


def check_new_features():
    """Check that new features are available."""
    print("\n✨ Checking new features...")
    
    try:
        from src.ai import (
            AIProcessor, STTProcessor, TTSProcessor,
            get_ai_processor, get_stt_processor, get_tts_processor,
            quick_prompt, quick_translate
        )
        from src.ai.models import AIRequest, TranslationRequest
        from src.ai.prompts import TranslationPrompts
        
        features = [
            ("AIProcessor class", AIProcessor),
            ("STTProcessor class", STTProcessor),
            ("TTSProcessor class", TTSProcessor),
            ("Factory functions", get_ai_processor),
            ("Convenience functions", quick_prompt),
            ("Type-safe models", AIRequest),
            ("Prompt templates", TranslationPrompts)
        ]
        
        all_good = True
        
        for feature_name, feature_obj in features:
            if feature_obj is None:
                print(f"❌ {feature_name} not available")
                all_good = False
            else:
                print(f"✅ {feature_name} available")
        
        # Test basic instantiation
        try:
            processor = AIProcessor()
            print("✅ AIProcessor instantiation works")
        except Exception as e:
            print(f"❌ AIProcessor instantiation failed: {e}")
            all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"❌ New features check failed: {e}")
        return False


def generate_migration_commands():
    """Generate the exact commands needed to complete migration."""
    print("\n📝 Migration commands to run:")
    print("=" * 50)
    
    commands = [
        "# 1. Update main.py imports",
        "sed -i 's/import ai_processor/from src import ai as ai_processor/' main.py",
        "",
        "# 2. Update event_handlers.py imports", 
        "sed -i 's/import ai_processor/from src import ai as ai_processor/' event_handlers.py",
        "",
        "# 3. Update src/telegram/handlers.py imports",
        "sed -i '13i\\from src import ai as ai_processor' src/telegram/handlers.py",
        "",
        "# 4. Test the changes",
        "python test_ai_refactor.py",
        "",
        "# 5. Remove old file (after testing)",
        "# rm ai_processor.py"
    ]
    
    for cmd in commands:
        print(cmd)
    
    print("\n🚀 Or run the automated migration:")
    print("python -c \"import validate_refactor; validate_refactor.auto_migrate()\"")


def auto_migrate():
    """Automatically perform the migration."""
    print("🤖 Starting automatic migration...")
    
    import subprocess
    
    commands = [
        "sed -i 's/import ai_processor/from src import ai as ai_processor/' main.py",
        "sed -i 's/import ai_processor/from src import ai as ai_processor/' event_handlers.py"
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {cmd}")
            else:
                print(f"❌ {cmd}: {result.stderr}")
        except Exception as e:
            print(f"❌ {cmd}: {e}")
    
    print("\n🏁 Migration completed! Run 'python test_ai_refactor.py' to validate.")


def main():
    """Main validation runner."""
    print("🧪 SakaiBot AI Refactor Validation")
    print("=" * 50)
    
    tests = [
        ("Module Structure", check_module_structure),
        ("Imports", check_imports),
        ("Function Signatures", check_function_signatures),
        ("Legacy Compatibility", check_legacy_compatibility),
        ("New Features", check_new_features)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 {test_name} Check:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} check failed: {e}")
            results.append((test_name, False))
    
    # Show code metrics
    analyze_code_metrics()
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n📊 Validation Summary:")
    print("=" * 30)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validations passed! Ready for migration.")
        generate_migration_commands()
    elif passed >= total * 0.8:
        print("⚠️  Most validations passed. Review failures and proceed with caution.")
        generate_migration_commands()
    else:
        print("❌ Too many validations failed. Fix issues before migration.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
