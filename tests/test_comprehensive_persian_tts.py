#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive test script for Persian TTS functionality"""

import asyncio
import os
from pathlib import Path

import sys
import os
# Add the project root to the path so we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.tts import TextToSpeechProcessor


async def test_comprehensive_persian_tts():
    """Test the Persian TTS functionality with various scenarios."""
    print("Testing comprehensive Persian TTS functionality...")
    
    # Create TTS processor instance
    tts_processor = TextToSpeechProcessor()
    
    # Test 1: Short Persian text
    print("\n1. Testing short Persian text...")
    short_text = "سلام، این یک تست فارسی است."
    output_file = "test_short_persian_tts.mp3"
    
    result1 = await tts_processor.text_to_speech(
        text_to_speak=short_text,
        output_filename=output_file
    )
    
    print(f"   Short text success: {result1}")
    print(f"   Provider used: {tts_processor._last_provider}")
    if Path(output_file).exists():
        print(f"   File size: {Path(output_file).stat().st_size} bytes")
        Path(output_file).unlink()  # Clean up
    
    # Test 2: Longer Persian text
    print("\n2. Testing longer Persian text...")
    long_text = ("سلام، این یک متن فارسی طولانی‌تر برای تست تبدیل متن به گفتار است. " 
                 "ما در حال تست قابلیت تولید گفتار فارسی در ربات سکای هستیم. " 
                 "امیدواریم که این پیاده‌سازی به درستی کار کند و بتواند متن فارسی را به گفتار تبدیل کند.")
    output_file = "test_long_persian_tts.mp3"
    
    result2 = await tts_processor.text_to_speech(
        text_to_speak=long_text,
        output_filename=output_file
    )
    
    print(f"   Long text success: {result2}")
    print(f"   Provider used: {tts_processor._last_provider}")
    if Path(output_file).exists():
        print(f"   File size: {Path(output_file).stat().st_size} bytes")
        Path(output_file).unlink()  # Clean up
    
    # Test 3: Persian text with numbers and punctuation
    print("\n3. Testing Persian text with numbers and punctuation...")
    complex_text = "ساعت ۳:۳۰ بعد از ظهر، در تاریخ ۱۴۰۲/۰۷/۲۰، جلسه برگزار خواهد شد."
    output_file = "test_complex_persian_tts.mp3"
    
    result3 = await tts_processor.text_to_speech(
        text_to_speak=complex_text,
        output_filename=output_file
    )
    
    print(f"   Complex text success: {result3}")
    print(f"   Provider used: {tts_processor._last_provider}")
    if Path(output_file).exists():
        print(f"   File size: {Path(output_file).stat().st_size} bytes")
        Path(output_file).unlink()  # Clean up
    
    # Test 4: Empty text
    print("\n4. Testing empty text...")
    result4 = await tts_processor.text_to_speech(
        text_to_speak="",
        output_filename="test_empty_tts.mp3"
    )
    
    print(f"   Empty text success: {result4}")
    
    # Summary
    print(f"\nSummary:")
    print(f"  Short text: {'✓' if result1 else '✗'}")
    print(f"  Long text: {'✓' if result2 else '✗'}")
    print(f"  Complex text: {'✓' if result3 else '✗'}")
    print(f"  Empty text handled: {'✓' if not result4 else '✗'}")
    
    all_tests_passed = result1 and result2 and result3 and not result4
    print(f"\nAll tests passed: {all_tests_passed}")
    
    return all_tests_passed


if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_persian_tts())
    print(f"\nComprehensive test completed. Success: {success}")