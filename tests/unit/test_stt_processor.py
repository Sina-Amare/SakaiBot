"""Tests for speech-to-text request handling."""

import pytest
from pydub import AudioSegment

from src.ai import stt as stt_module
from src.ai.stt import SpeechToTextProcessor
from src.core.exceptions import AIProcessorError


@pytest.mark.asyncio
async def test_single_clip_bad_request_is_retried_and_hidden(
    tmp_path,
    monkeypatch,
) -> None:
    wav_path = tmp_path / "voice.wav"
    AudioSegment.silent(duration=1000).export(wav_path, format="wav")

    attempts = 0

    def fail_with_google_bad_request(self, audio_wav_path, language):
        nonlocal attempts
        attempts += 1
        raise AIProcessorError(
            "API request failed: recognition request failed: Bad Request"
        )

    monkeypatch.setattr(stt_module, "_RETRY_BASE_DELAY_S", 0)
    monkeypatch.setattr(
        SpeechToTextProcessor,
        "_transcribe_file_sync",
        fail_with_google_bad_request,
    )

    processor = SpeechToTextProcessor()
    with pytest.raises(AIProcessorError) as exc_info:
        await processor.transcribe_voice_to_text(str(wav_path))

    assert attempts == stt_module._MAX_CHUNK_ATTEMPTS
    assert str(exc_info.value) == (
        "STT service unavailable — please try again in a moment"
    )


def test_bad_request_is_classified_as_service_error() -> None:
    err = AIProcessorError(
        "API request failed: recognition request failed: Bad Request"
    )

    assert SpeechToTextProcessor._is_service_error(err) is True
