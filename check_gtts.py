# -*- coding: utf-8 -*-
# English comments as per our rules

from gtts.lang import tts_langs
from gtts import gTTS
import os

def check_gtts_languages():
    """Prints supported languages by the installed gTTS and checks for Persian."""
    try:
        supported_langs = tts_langs()
        print("gTTS Supported Languages (according to your installation):")
        if supported_langs: # Check if the dictionary is not empty
            for lang_code, lang_name in supported_langs.items():
                print(f"- {lang_code}: {lang_name}")
            
            if 'fa' in supported_langs:
                print("\nINFO: 'fa' (Persian) IS listed as supported by your gTTS installation.")
            else:
                print("\nWARNING: 'fa' (Persian) IS NOT listed as supported by your gTTS installation.")
        else:
            print("\nERROR: Could not retrieve any supported languages from gTTS. The library might be corrupted.")
            
    except Exception as e:
        print(f"\nERROR: An error occurred while trying to get gTTS languages: {e}")

def direct_gtts_persian_test():
    """Attempts a direct TTS generation in Persian."""
    print("\nAttempting to generate a Persian TTS sample directly with gTTS...")
    test_text = "سلام دنیا، این یک آزمایش است."
    output_file = "test_persian_gtts.mp3"
    try:
        tts = gTTS(text=test_text, lang='fa', slow=False)
        tts.save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"SUCCESS: Successfully created '{output_file}' with Persian text: '{test_text}'")
            print("Please check this file to see if it plays correctly.")
            # os.remove(output_file) # You can uncomment this to auto-delete after test
        else:
            print(f"FAILURE: Failed to create or an empty '{output_file}' was created with Persian text.")
    except ValueError as ve:
        print(f"FAILURE (ValueError): Direct gTTS test for Persian failed: {ve}")
        print("This confirms the 'Language not supported' issue from within gTTS.")
    except Exception as e:
        print(f"FAILURE (Other Error): Direct gTTS test for Persian failed with an unexpected error: {e}")

if __name__ == '__main__':
    print("--- Starting gTTS Diagnostics ---")
    check_gtts_languages()
    direct_gtts_persian_test()
    print("\n--- End of gTTS Diagnostics ---")

