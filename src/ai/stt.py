"""Speech-to-Text processing for SakaiBot."""

import asyncio
import os
from pathlib import Path
from typing import Awaitable, Callable, List, Optional, Set

import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence

from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger


# Google Web Speech API reliably handles audio up to ~60s per request.
# Stay safely under that and split long audio into chunks.
_CHUNK_MS = 55_000
# Small overlap so a fixed cut that lands mid-word can still pick up that word's
# tail on the next chunk. Kept tight (~100ms) to almost always fall inside
# inter-word silence, avoiding duplicated words at chunk seams.
_OVERLAP_MS = 100
_SILENCE_MIN_MS = 700           # gap of >=700ms is considered a sentence boundary
_SILENCE_KEEP_MS = 250          # keep a little silence around each chunk
_SILENCE_SEEK_STEP_MS = 10
_MIN_USEFUL_CHUNK_MS = 1_500    # ignore tiny fragments below this size
_FALLBACK_SILENCE_THRESH = -40  # dBFS, used when audio.dBFS is -inf

# Resilience: Google's free Web Speech endpoint has no SLA and occasionally
# returns an empty response (raised as UnknownValueError) when throttled, or
# transient 5xx/connection errors (RequestError). Retry each chunk a few times
# before giving up, and space requests apart slightly to be polite.
_MAX_CHUNK_ATTEMPTS = 3         # 1 initial + 2 retries
_RETRY_BASE_DELAY_S = 1.5       # exponential backoff: 1.5s, 3s, ...
_INTER_CHUNK_DELAY_S = 0.4      # quiet gap between successive chunk requests

ProgressCallback = Callable[[int, int], Awaitable[None]]
ChunkTextCallback = Callable[[int, int, str], Awaitable[None]]


class SpeechToTextProcessor:
    """Handles speech-to-text conversion using Google Web Speech API.

    Long audio (>~60s) is automatically split into chunks on silence boundaries
    and transcribed sequentially. Individual unintelligible chunks are skipped
    rather than aborting the whole transcription.
    """

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._recognizer = sr.Recognizer()

    async def transcribe_voice_to_text(
        self,
        audio_wav_path: str,
        language: str = "fa-IR",
        progress_cb: Optional[ProgressCallback] = None,
        on_chunk_text: Optional[ChunkTextCallback] = None,
        chunk_filter: Optional[Set[int]] = None,
    ) -> str:
        """Transcribe audio of any length to text.

        Args:
            audio_wav_path: Path to a WAV file (mono/16kHz recommended).
            language: BCP-47 language tag for Google STT.
            progress_cb: Optional async callback invoked as ``(current, total)``
                after each chunk is processed (called regardless of whether the
                chunk produced any text).
            on_chunk_text: Optional async callback invoked as
                ``(chunk_index, total, text)`` after each chunk with non-empty
                transcription. Skipped/unintelligible chunks are not reported.
            chunk_filter: Optional set of 1-indexed chunk numbers to process.
                When set, only listed chunks are transcribed; all others are
                skipped without calling either callback. Used for partial
                retries of failed chunks from an earlier run. Splitting is
                deterministic, so chunk N on retry is the same audio segment
                as chunk N on the original attempt.

        Returns:
            The full transcribed text of processed chunks, joined with spaces.
        """
        audio_path = Path(audio_wav_path)
        if not audio_path.exists():
            self._logger.error(f"Audio file not found at {audio_wav_path}")
            raise AIProcessorError("Audio file not found")

        audio = await asyncio.to_thread(AudioSegment.from_file, str(audio_path))
        duration_ms = len(audio)
        self._logger.info(f"Audio duration: {duration_ms / 1000:.1f}s")

        if duration_ms <= _CHUNK_MS:
            if chunk_filter is not None and 1 not in chunk_filter:
                raise AIProcessorError(
                    f"Audio has only 1 chunk; requested chunks "
                    f"{sorted(chunk_filter)} are out of range"
                )
            try:
                text = await asyncio.to_thread(
                    self._transcribe_file_sync, str(audio_path), language
                )
            except AIProcessorError:
                raise
            if text and on_chunk_text:
                await on_chunk_text(1, 1, text.strip())
            if progress_cb:
                await progress_cb(1, 1)
            return text

        chunks = await asyncio.to_thread(self._split_audio, audio)
        total = len(chunks)

        if chunk_filter is not None:
            out_of_range = sorted(i for i in chunk_filter if i < 1 or i > total)
            if out_of_range:
                raise AIProcessorError(
                    f"Chunk indices {out_of_range} out of range "
                    f"(audio has {total} chunks)"
                )
            self._logger.info(
                f"Split long audio into {total} chunks; "
                f"filter active for {sorted(chunk_filter)}"
            )
        else:
            self._logger.info(f"Split long audio into {total} chunks")

        temp_dir = str(audio_path.parent)
        stem = audio_path.stem
        parts: List[str] = []
        service_failures = 0  # chunks that failed with network/HTTP errors
        silent_failures = 0   # chunks that failed with "unintelligible" / no speech

        for idx, segment in enumerate(chunks, start=1):
            if chunk_filter is not None and idx not in chunk_filter:
                continue

            chunk_path = os.path.join(temp_dir, f"{stem}_chunk_{idx}.wav")
            try:
                await asyncio.to_thread(segment.export, chunk_path, format="wav")
                text, error_kind = await self._transcribe_chunk_with_retry(
                    chunk_path, language, idx, total
                )
                if text:
                    parts.append(text)
                    if on_chunk_text:
                        await on_chunk_text(idx, total, text)
                elif error_kind == "service":
                    service_failures += 1
                else:
                    silent_failures += 1
            finally:
                try:
                    Path(chunk_path).unlink(missing_ok=True)
                except Exception:
                    pass

            if progress_cb:
                await progress_cb(idx, total)

            # Space requests apart so we don't trip Google's free-tier throttle.
            if idx < total:
                await asyncio.sleep(_INTER_CHUNK_DELAY_S)

        self._logger.info(
            f"Transcription complete: {len(parts)}/{total} chunks delivered, "
            f"{service_failures} service failures, {silent_failures} silent/unintelligible"
        )

        if not parts:
            if service_failures and service_failures >= silent_failures:
                raise AIProcessorError(
                    "STT service unavailable — please try again in a moment"
                )
            raise AIProcessorError("Speech was unintelligible")

        return " ".join(parts)

    async def _transcribe_chunk_with_retry(
        self,
        chunk_path: str,
        language: str,
        idx: int,
        total: int,
    ) -> "tuple[Optional[str], Optional[str]]":
        """Transcribe one chunk, retrying transient failures.

        Returns ``(text, error_kind)``:
            * On success: ``(text, None)``.
            * On final failure: ``(None, error_kind)`` where ``error_kind`` is
              ``"service"`` for network/HTTP errors and ``"silent"`` for
              empty / unintelligible responses.

        Truly unintelligible audio and transient throttling both surface as
        ``UnknownValueError`` ("unintelligible") from Google's free endpoint,
        so we retry both — real silence will simply fail again and be
        classified as silent, while throttled chunks usually recover on retry.
        """
        last_error: Optional[Exception] = None
        had_service_error = False

        for attempt in range(1, _MAX_CHUNK_ATTEMPTS + 1):
            try:
                text = await asyncio.to_thread(
                    self._transcribe_file_sync, chunk_path, language
                )
                if text:
                    return text.strip(), None
                # Empty text without exception: treat as a soft miss; retry.
                last_error = AIProcessorError("Empty transcription")
            except AIProcessorError as e:
                last_error = e
                if self._is_service_error(e):
                    had_service_error = True

            if attempt < _MAX_CHUNK_ATTEMPTS:
                delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                self._logger.info(
                    f"Chunk {idx}/{total} attempt {attempt} failed "
                    f"({last_error}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        self._logger.warning(
            f"Chunk {idx}/{total} gave up after {_MAX_CHUNK_ATTEMPTS} "
            f"attempts: {last_error}"
        )
        return None, ("service" if had_service_error else "silent")

    @staticmethod
    def _is_service_error(err: Exception) -> bool:
        """Best-effort detection of network/service-side failures."""
        msg = str(err).lower()
        return any(
            tok in msg
            for tok in ("api request failed", "request failed", "timeout",
                       "connection", "5xx", "503", "502", "429")
        )

    def _split_audio(self, audio: AudioSegment) -> List[AudioSegment]:
        """Split audio on silence, then enforce a max chunk length."""
        silence_thresh = (
            audio.dBFS - 14
            if audio.dBFS != float("-inf")
            else _FALLBACK_SILENCE_THRESH
        )

        try:
            silence_chunks = split_on_silence(
                audio,
                min_silence_len=_SILENCE_MIN_MS,
                silence_thresh=silence_thresh,
                keep_silence=_SILENCE_KEEP_MS,
                seek_step=_SILENCE_SEEK_STEP_MS,
            )
        except Exception as e:
            self._logger.warning(
                f"split_on_silence failed ({e}); falling back to fixed-size chunks"
            )
            silence_chunks = []

        if not silence_chunks:
            return self._fixed_chunks(audio)

        # Pack silence-chunks into <=_CHUNK_MS buckets; sub-split any oversized chunk.
        result: List[AudioSegment] = []
        buffer = AudioSegment.empty()
        for c in silence_chunks:
            if len(c) > _CHUNK_MS:
                if len(buffer) >= _MIN_USEFUL_CHUNK_MS:
                    result.append(buffer)
                    buffer = AudioSegment.empty()
                result.extend(self._fixed_chunks(c))
                continue
            if len(buffer) + len(c) <= _CHUNK_MS:
                buffer += c
            else:
                if len(buffer) >= _MIN_USEFUL_CHUNK_MS:
                    result.append(buffer)
                buffer = c
        if len(buffer) >= _MIN_USEFUL_CHUNK_MS:
            result.append(buffer)

        return result or self._fixed_chunks(audio)

    @staticmethod
    def _fixed_chunks(audio: AudioSegment) -> List[AudioSegment]:
        """Slice audio into fixed ~_CHUNK_MS windows with a small overlap."""
        chunks: List[AudioSegment] = []
        i = 0
        total = len(audio)
        while i < total:
            end = min(i + _CHUNK_MS, total)
            chunks.append(audio[i:end])
            if end == total:
                break
            i = end - _OVERLAP_MS
        return chunks

    def _transcribe_file_sync(self, audio_wav_path: str, language: str) -> str:
        """Synchronously transcribe a single short WAV file."""
        audio_path = Path(audio_wav_path)
        if not audio_path.exists():
            self._logger.error(f"Audio file not found at {audio_wav_path}")
            raise AIProcessorError("Audio file not found")

        try:
            with sr.AudioFile(str(audio_path)) as source:
                audio_data = self._recognizer.record(source)

            text = self._recognizer.recognize_google(audio_data, language=language)
            self._logger.info(f"Transcription successful: '{text[:100]}...'")
            return text

        except sr.WaitTimeoutError:
            self._logger.error("No speech detected (timeout)")
            raise AIProcessorError("No speech detected or timeout")

        except sr.UnknownValueError:
            self._logger.info("Google Web Speech API could not understand audio")
            raise AIProcessorError("Speech was unintelligible")

        except sr.RequestError as e:
            self._logger.error(f"Could not request results from Google Web Speech API: {e}")
            raise AIProcessorError(f"API request failed: {e}. Check internet connection")

        except Exception as e:
            self._logger.error(f"Unexpected error during transcription: {e}", exc_info=True)
            raise AIProcessorError(f"Transcription failed: {e}")
