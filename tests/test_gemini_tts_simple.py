"""Simple test file for Gemini TTS using the official snippet.

This test uses the exact code pattern from Google's documentation:
https://ai.google.dev/gemini-api/docs/speech-generation

Tests with Persian text and reads API key from .env file.
"""

import os
import sys
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")
except ImportError:
    pass

from google import genai
from google.genai import types
import wave


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Set up the wave file to save the output."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def main():
    """Test Gemini TTS with Persian text."""
    print("=" * 60)
    print("Gemini TTS Simple Test (Official Snippet)")
    print("=" * 60)
    
    # Get API key from environment (priority: TTS key -> Gemini key -> Google key)
    api_key = (
        os.getenv("GEMINI_API_KEY_TTS") or 
        os.getenv("GEMINI_API_KEY") or 
        os.getenv("GOOGLE_API_KEY")
    )
    
    if not api_key:
        print("❌ ERROR: No API key found!")
        print("Please set one of the following in your .env file:")
        print("  - GEMINI_API_KEY_TTS")
        print("  - GEMINI_API_KEY")
        print("  - GOOGLE_API_KEY")
        sys.exit(1)
    
    print(f"✓ API Key found: {api_key[:10]}... (truncated)")
    print()
    
    # Initialize client with API key
    client = genai.Client(api_key=api_key)
    
    # Persian text for testing
    persian_text = "سلام، این یک تست برای تبدیل متن به گفتار است."
    print(f"Test text (Persian): {persian_text}")
    print("Voice: Kore (default)")
    print("Language: Auto-detect (not set)")
    print()
    
    try:
        print("Calling generate_content...")
        
        # Use the exact pattern from the official documentation
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=persian_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Kore',
                        )
                    )
                ),
            )
        )
        
        print("✓ Response received")
        
        # Extract audio data (exact pattern from snippet)
        print("Extracting audio data...")
        
        # Check response structure
        if not hasattr(response, 'candidates') or not response.candidates:
            print("❌ ERROR: No candidates in response")
            print(f"Response: {response}")
            sys.exit(1)
        
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not candidate.content:
            print("❌ ERROR: No content in candidate")
            print(f"Candidate: {candidate}")
            sys.exit(1)
        
        if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
            print("❌ ERROR: No parts in content")
            print(f"Content: {candidate.content}")
            sys.exit(1)
        
        part = candidate.content.parts[0]
        
        if not hasattr(part, 'inline_data') or not part.inline_data:
            print("❌ ERROR: No inline_data in part")
            print(f"Part: {part}")
            print(f"Part attributes: {dir(part)}")
            sys.exit(1)
        
        if not hasattr(part.inline_data, 'data') or not part.inline_data.data:
            print("❌ ERROR: No data in inline_data")
            print(f"InlineData: {part.inline_data}")
            print(f"InlineData attributes: {dir(part.inline_data)}")
            sys.exit(1)
        
        data = part.inline_data.data
        print(f"✓ Audio data extracted: {len(data)} bytes")
        
        # Save to WAV file
        file_name = 'test_persian_output.wav'
        print(f"Saving to {file_name}...")
        
        wave_file(file_name, data)
        
        # Verify file was created
        if Path(file_name).exists():
            file_size = Path(file_name).stat().st_size
            print(f"✓ File created successfully: {file_name}")
            print(f"✓ File size: {file_size} bytes")
            
            if file_size > 0:
                print()
                print("=" * 60)
                print("✓ Test PASSED!")
                print("=" * 60)
                print(f"Audio file saved: {file_name}")
                return True
            else:
                print("❌ ERROR: File is empty!")
                return False
        else:
            print("❌ ERROR: File was not created!")
            return False
            
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR occurred!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

