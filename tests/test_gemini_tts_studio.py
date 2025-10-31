"""Test file for Google Gemini Studio TTS functionality.

This test file isolates and verifies the TTS functionality independently.
Run this to verify that the API key configuration and TTS synthesis work correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env before importing modules
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

from src.ai.providers.tts_gemini import synthesize_speech
from src.core.tts_config import GOOGLE_API_KEY


def test_api_key_detection():
    """Test that API key is detected from environment variables."""
    print("\n=== Testing API Key Detection ===")
    
    # Check all three possible keys
    tts_key = os.getenv("GEMINI_API_KEY_TTS")
    gemini_key = os.getenv("GEMINI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    print(f"GEMINI_API_KEY_TTS: {'✓ Found' if tts_key else '✗ Not found'}")
    print(f"GEMINI_API_KEY: {'✓ Found' if gemini_key else '✗ Not found'}")
    print(f"GOOGLE_API_KEY: {'✓ Found' if google_key else '✗ Not found'}")
    print(f"Resolved GOOGLE_API_KEY (from config): {'✓ Found' if GOOGLE_API_KEY else '✗ Not found'}")
    
    if not GOOGLE_API_KEY:
        print("\n❌ ERROR: No valid API key found!")
        print("Please set one of the following in your .env file:")
        print("  - GEMINI_API_KEY_TTS (preferred for TTS)")
        print("  - GEMINI_API_KEY (general Gemini key)")
        print("  - GOOGLE_API_KEY (legacy name)")
        return False
    
    print(f"\n✓ API Key found! Using key: {GOOGLE_API_KEY[:10]}... (truncated)")
    return True


def test_tts_synthesis():
    """Test direct TTS synthesis with a simple text."""
    print("\n=== Testing TTS Synthesis ===")
    
    if not GOOGLE_API_KEY:
        print("❌ Skipping TTS test - no API key configured")
        return False
    
    # Test parameters
    test_text = "Hello, world! This is a test of Google Gemini TTS."
    output_file = "test_gemini_tts_output.wav"
    
    print(f"Test text: {test_text}")
    print(f"Output file: {output_file}")
    print(f"Voice: Kore (default)")
    
    try:
        # Call the synthesis function directly
        print("\nCalling synthesize_speech...")
        success, error_msg = synthesize_speech(
            text=test_text,
            output_file=output_file,
            voice_name="Kore"
        )
        
        if success:
            print("✓ TTS synthesis successful!")
            
            # Verify file was created
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                print(f"✓ Audio file created: {output_file} ({file_size} bytes)")
                
                if file_size > 0:
                    print("✓ File is not empty")
                    
                    # Cleanup
                    try:
                        Path(output_file).unlink()
                        print("✓ Test file cleaned up")
                    except Exception as e:
                        print(f"⚠ Warning: Could not delete test file: {e}")
                    
                    return True
                else:
                    print("❌ ERROR: File is empty!")
                    return False
            else:
                print("❌ ERROR: File was not created!")
                return False
        else:
            print(f"❌ TTS synthesis failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during TTS synthesis: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Google Gemini Studio TTS Test")
    print("=" * 60)
    
    # Test 1: API Key Detection
    if not test_api_key_detection():
        print("\n❌ API Key detection failed. Cannot proceed with TTS test.")
        sys.exit(1)
    
    # Test 2: TTS Synthesis
    if test_tts_synthesis():
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ TTS synthesis test failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

