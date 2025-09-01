# -*- coding: utf-8 -*-
"""
gTTS Diagnostics Script
- Lists supported languages
- Tests Persian TTS generation
"""

from gtts.lang import tts_langs
from gtts import gTTS
import os


def check_gtts_languages():
    """Print supported languages and verify Persian ('fa') availability."""
    try:
        supported_langs = tts_langs()
        print("✅ gTTS Supported Languages:")

        if supported_langs:
            for code, name in supported_langs.items():
                print(f"- {code}: {name}")

            if 'fa' in supported_langs:
                print("\n✅ 'fa' (Persian) is supported.")
            else:
                print("\n⚠️  'fa' (Persian) is NOT supported.")
        else:
            print("\n❌ Failed to fetch supported languages (empty result).")
    except Exception as e:
        print(f"\n❌ Error retrieving gTTS languages: {e}")


def direct_gtts_persian_test():
    """Try generating a Persian TTS file directly."""
    print("\n🔊 Testing Persian TTS generation...")
    test_text = "سلام دنیا، این یک آزمایش است."
    output_file = "test_persian_gtts.mp3"

    try:
        tts = gTTS(text=test_text, lang='fa', slow=False)
        tts.save(output_file)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"✅ File created: '{output_file}' with text: '{test_text}'")
            print("Please play it manually to verify.")
            # os.remove(output_file)  # Uncomment to auto-clean
        else:
            print(f"❌ File '{output_file}' was not created or is empty.")
    except ValueError as ve:
        print(f"❌ ValueError: {ve}")
        print("Likely due to unsupported language code 'fa'.")
    except Exception as e:
        print(f"❌ Unexpected error during TTS generation: {e}")


if __name__ == '__main__':
    print("=== gTTS Diagnostics ===")
    check_gtts_languages()
    direct_gtts_persian_test()
    print("=== Diagnostics Complete ===")
