"""Unit tests for Text-to-Speech functionality."""

import asyncio
import os
from pathlib import Path
import unittest

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ai.tts import TextToSpeechProcessor

class TestPersianTTS(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        from src.core.config import get_settings
        env_path = Path(__file__).parent.parent / ".env.test"
        self.config = get_settings(dotenv_path=str(env_path))

    @unittest.skip("Skipping TTS test because it requires a valid API key.")
    def test_persian_tts_generation(self):
        """
        Tests that the TextToSpeechProcessor can generate a Persian TTS file.
        """
        async def run_test():
            # 1. Setup
            processor = TextToSpeechProcessor(config=self.config)
            text = "سلام، حال شما چطوره؟"
            output_filename = "test_persian_tts.wav"

            # 2. Execution
            success = await processor.text_to_speech(
                text_to_speak=text,
                voice="Kore",  # Use Gemini-compatible voice
                output_filename=output_filename
            )

            # 3. Assertion
            self.assertTrue(success, "TTS generation failed.")
            self.assertTrue(Path(output_filename).exists(), "Output file was not created.")
            self.assertTrue(Path(output_filename).stat().st_size > 0, "Output file is empty.")

            # 4. Cleanup
            if Path(output_filename).exists():
                os.remove(output_filename)

        # Run the async test
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
