"""STT (Speech-to-Text) command handler."""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional, List, Set

from telethon import TelegramClient
from telethon.tl.types import Message
from pydub import AudioSegment

from ...ai.stt import SpeechToTextProcessor
from ...ai.processor import AIProcessor
from ...ai.prompts import (
    VOICE_MESSAGE_SUMMARY_PROMPT
)
from ...core.constants import MAX_MESSAGE_LENGTH
from ...core.exceptions import AIProcessorError
from ...utils.helpers import clean_temp_files, split_message
from ...utils.logging import get_logger
from ...utils.message_sender import MessageSender
from .base import BaseHandler


# AI summarization is currently disabled (external API unavailable).
# Flip this to True to re-enable the "🔍 AI Summary & Analysis" message
# after each /stt call. No other code changes are required.
STT_AI_SUMMARY_ENABLED = False


def _md_safe(text: str) -> str:
    """Neutralize Markdown-special characters in untrusted text.

    Transcripts and Telegram display names are embedded into messages sent
    with parse_mode='md'. A stray '*' or '_' could break rendering, so
    those characters are softened to harmless equivalents.
    """
    return (
        text.replace('`', "'")
        .replace('*', '∗')   # asterisk -> ∗ (visually similar)
        .replace('_', '‗')   # underscore -> ‗
        .replace('[', '(')
        .replace(']', ')')
    )


class STTHandler(BaseHandler):
    """Handles STT (Speech-to-Text) commands."""
    
    def __init__(
        self,
        stt_processor: SpeechToTextProcessor,
        ai_processor: AIProcessor,
        ffmpeg_path: Optional[str] = None
    ):
        """
        Initialize STT handler.
        
        Args:
            stt_processor: Speech-to-text processor
            ai_processor: AI processor for summarization
            ffmpeg_path: Optional path to FFmpeg executable
        """
        super().__init__(ffmpeg_path)
        self._stt_processor = stt_processor
        self._ai_processor = ai_processor
    
    async def process_stt_command(
        self,
        original_message: Message,
        replied_voice_message: Message,
        client: TelegramClient,
        command_sender_info: str,
        chunk_filter: Optional[Set[int]] = None,
    ) -> None:
        """Process STT command and provide transcription with AI summary.

        Args:
            chunk_filter: Optional 1-indexed chunk numbers to transcribe; when
                set, runs in "partial" mode and only processes the listed
                chunks. Used for retrying failed chunks from a previous run.
        """
        chat_id = original_message.chat_id
        reply_to_id = original_message.id
        is_partial = chunk_filter is not None and len(chunk_filter) > 0
        
        # Check rate limit first
        from ...utils.rate_limiter import get_ai_rate_limiter
        rate_limiter = get_ai_rate_limiter()
        user_id = original_message.sender_id
        if not await rate_limiter.check_rate_limit(user_id):
            remaining = await rate_limiter.get_remaining_requests(user_id)
            error_msg = (
                f"⚠️ Rate limit exceeded\n\n"
                f"You have reached the request limit.\n"
                f"Please wait {rate_limiter._window_seconds} seconds.\n"
                f"Remaining requests: {remaining}"
            )
            await client.send_message(chat_id, error_msg, reply_to=reply_to_id)
            return
        
        # User-supplied display name embedded into a Markdown message.
        sender_md = _md_safe(command_sender_info)

        if is_partial:
            wanted_list = ", ".join(str(i) for i in sorted(chunk_filter))
            initial_status = (
                f"🎧 **Voice Processing**\n\n"
                f"🔄 Retrying part(s): {wanted_list}\n"
                f"__From {sender_md}__"
            )
        else:
            initial_status = (
                f"🎧 **Voice Processing**\n\n"
                f"🔄 Transcribing...\n"
                f"__From {sender_md}__"
            )

        status_msg = await client.send_message(
            chat_id,
            initial_status,
            reply_to=reply_to_id,
            parse_mode='md'
        )

        downloaded_voice_path = None
        # Use /tmp for Docker (read-only root filesystem) or system temp
        import tempfile
        temp_dir = "/tmp" if os.path.exists("/tmp") and os.access("/tmp", os.W_OK) else tempfile.gettempdir()
        converted_wav_path = os.path.join(temp_dir, f"temp_voice_stt_{original_message.id}_{replied_voice_message.id}.wav")
        path_modified = False
        original_path = ""
        message_sender = MessageSender(client)

        try:
            # Setup FFmpeg path
            path_modified, original_path = await self._setup_ffmpeg_path()

            # Download voice/audio to temp directory
            base_download_name = os.path.join(temp_dir, f"temp_voice_download_stt_{original_message.id}_{replied_voice_message.id}")
            downloaded_voice_path = await client.download_media(
                replied_voice_message.media,
                file=base_download_name
            )

            if not downloaded_voice_path or not Path(downloaded_voice_path).exists():
                raise FileNotFoundError("Downloaded voice file not found or download failed")

            self._logger.info(f"Voice downloaded to '{downloaded_voice_path}'. Converting to WAV (mono/16kHz)...")

            # Convert to mono/16kHz WAV off the event loop (long files would otherwise block).
            try:
                await asyncio.to_thread(self._convert_to_stt_wav, downloaded_voice_path, converted_wav_path)
            except Exception as conv_err:
                self._logger.error(f"Audio decode/conversion failed: {conv_err}", exc_info=True)
                raise AIProcessorError(
                    "Could not decode audio file (unsupported format or corrupt data)"
                ) from conv_err
            self._logger.info(f"Voice converted to '{converted_wav_path}'")

            # Streaming delivery state: send each chunk as its own message as soon as it's ready.
            # First successful chunk REPLACES the status message via edit; later chunks become new sends.
            delivered_first = False
            delivery_lock = asyncio.Lock()
            last_status_edit_at = 0.0
            delivered_indices: set = set()
            last_total = 0

            async def on_progress(current: int, total: int) -> None:
                """Update status only while no chunk has been delivered yet."""
                nonlocal last_status_edit_at, last_total
                last_total = total
                if delivered_first or total <= 1:
                    return
                now = asyncio.get_event_loop().time()
                if current != total and (now - last_status_edit_at) < 2.0:
                    return
                last_status_edit_at = now
                verb = "Retrying" if is_partial else "Transcribing"
                await message_sender.edit_message_safe(
                    status_msg,
                    f"🎧 **Voice Processing**\n\n"
                    f"🔄 {verb} chunk {current}/{total}...\n"
                    f"__From {sender_md}__",
                    parse_mode='md',
                )

            async def on_chunk_text(idx: int, total: int, text: str) -> None:
                """Deliver a single chunk as its own Telegram message."""
                nonlocal delivered_first, last_total
                last_total = total
                delivered_indices.add(idx)

                async with delivery_lock:
                    if total > 1:
                        header = f"📝 **Transcribed Text** — Part {idx}/{total}:\n"
                    else:
                        header = "📝 **Transcribed Text**:\n"

                    # Neutralize Markdown-special chars so the transcript
                    # can't break parse_mode='md'. Rare in Persian speech,
                    # but defensive.
                    safe_text = _md_safe(text)

                    # Defensive: a single chunk's transcript is normally <2 KB,
                    # but split if it would exceed Telegram's per-message limit.
                    body_max = MAX_MESSAGE_LENGTH - len(header) - 4
                    pieces = split_message(safe_text, max_length=body_max)

                    for piece_idx, piece in enumerate(pieces):
                        msg_text = (header + piece) if piece_idx == 0 else piece

                        if not delivered_first:
                            ok = await message_sender.edit_message_safe(
                                status_msg, msg_text, parse_mode='md'
                            )
                            if not ok:
                                await message_sender.send_message_safe(
                                    chat_id, msg_text,
                                    reply_to=reply_to_id, parse_mode='md',
                                )
                            delivered_first = True
                        else:
                            await message_sender.send_message_safe(
                                chat_id, msg_text, parse_mode='md'
                            )
                            # Stay safely under Telegram's ~30 msgs/min self-bot
                            # send-rate limit. Transcription itself already adds
                            # ~3s between consecutive chunks, but this guarantees
                            # a 1s floor so a burst of fast chunks can't trip a
                            # 60s+ FloodWait.
                            await asyncio.sleep(1.0)

            # Transcribe (auto-chunks for long audio); each chunk is streamed as it arrives.
            full_transcript = await self._stt_processor.transcribe_voice_to_text(
                converted_wav_path,
                progress_cb=on_progress,
                on_chunk_text=on_chunk_text,
                chunk_filter=chunk_filter,
            )

            # If no chunk was ever delivered (e.g. transcript came back empty without an error),
            # surface that on the status message rather than leaving it stuck on "Transcribing...".
            if not delivered_first:
                await message_sender.edit_message_safe(
                    status_msg,
                    "⚠️ No speech detected in audio.",
                )

            # Build the post-transcription summary. The "Skipped parts: …" line
            # is parsed by the retry path (see extract_skipped_from_summary),
            # so its format is contract — don't change it without updating
            # that parser too. For single-chunk audio (last_total == 1) the
            # chunk message itself is enough closure — skip the summary.
            if delivered_first and last_total > 1:
                if is_partial:
                    expected = chunk_filter or set()
                    skipped_indices = sorted(expected - delivered_indices)
                    recovered = len(expected) - len(skipped_indices)
                    await asyncio.sleep(0.3)
                    if skipped_indices:
                        summary_lines = [
                            "ℹ️ **Retry complete.**",
                            f"✅ Recovered: {recovered} part(s)",
                            f"⚠️ Skipped parts: {', '.join(map(str, skipped_indices))}",
                            "",
                            "Reply with `/stt` to retry the skipped parts.",
                        ]
                        await message_sender.send_message_safe(
                            chat_id, "\n".join(summary_lines),
                            reply_to=reply_to_id, parse_mode='md',
                        )
                    else:
                        await message_sender.send_message_safe(
                            chat_id,
                            f"✅ **Retry complete:** all {recovered} part(s) recovered.",
                            reply_to=reply_to_id, parse_mode='md',
                        )
                else:
                    expected = set(range(1, last_total + 1))
                    skipped_indices = sorted(expected - delivered_indices)
                    delivered_count = last_total - len(skipped_indices)
                    await asyncio.sleep(0.3)
                    if skipped_indices:
                        summary_lines = [
                            "ℹ️ **Transcription complete.**",
                            f"✅ Delivered: {delivered_count}/{last_total} parts",
                            f"⚠️ Skipped parts: {', '.join(map(str, skipped_indices))}",
                            "",
                            "Reply with `/stt` to retry the skipped parts.",
                        ]
                        await message_sender.send_message_safe(
                            chat_id, "\n".join(summary_lines),
                            reply_to=reply_to_id, parse_mode='md',
                        )
                    else:
                        await message_sender.send_message_safe(
                            chat_id,
                            f"✅ **Transcription complete:** "
                            f"{delivered_count}/{last_total} parts delivered.",
                            reply_to=reply_to_id, parse_mode='md',
                        )

            # AI summary (currently disabled — see STT_AI_SUMMARY_ENABLED at top of module).
            # Skipped in partial/retry mode since the transcript is only a subset.
            if STT_AI_SUMMARY_ENABLED and full_transcript and not is_partial:
                summary_text = await self._build_summary(full_transcript)
                if summary_text:
                    await asyncio.sleep(0.3)
                    await message_sender.send_message_safe(
                        chat_id,
                        f"🔍 **AI Summary & Analysis:**\n{summary_text}",
                        reply_to=reply_to_id,
                        parse_mode='md',
                    )

        except AIProcessorError as e:
            await message_sender.edit_message_safe(status_msg, f"⚠️ STT Error: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error in STT processing: {e}", exc_info=True)
            await message_sender.edit_message_safe(status_msg, f"⚠️ An unexpected error occurred - {e}")

        finally:
            # Restore PATH if modified
            await self._restore_ffmpeg_path(path_modified, original_path)

            # Clean up temporary files
            clean_temp_files(downloaded_voice_path, converted_wav_path)

    @staticmethod
    def _convert_to_stt_wav(src_path: str, dst_path: str) -> None:
        """Convert any audio file to a mono/16kHz WAV suitable for STT."""
        audio = AudioSegment.from_file(src_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(dst_path, format="wav")

    # ------------------------------------------------------------------
    # Chunk-spec / summary helpers (used by the /stt retry path)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_chunk_spec(spec: str) -> Optional[Set[int]]:
        """Parse a user-provided chunk spec into a 1-indexed set.

        Accepted forms (comma-separated, whitespace tolerated):
            "12"          -> {12}
            "12,15"       -> {12, 15}
            "12-15"       -> {12, 13, 14, 15}
            "1-3, 7, 12"  -> {1, 2, 3, 7, 12}

        Returns ``None`` if the spec is empty or malformed.
        """
        if not spec or not spec.strip():
            return None
        result: Set[int] = set()
        try:
            for part in spec.split(','):
                part = part.strip()
                if not part:
                    continue
                if '-' in part:
                    a_str, b_str = part.split('-', 1)
                    a, b = int(a_str.strip()), int(b_str.strip())
                    if a < 1 or b < a:
                        return None
                    result.update(range(a, b + 1))
                else:
                    n = int(part)
                    if n < 1:
                        return None
                    result.add(n)
        except (ValueError, IndexError):
            return None
        return result or None

    @staticmethod
    def looks_like_summary(msg: Optional[Message]) -> bool:
        """Detect whether ``msg`` is one of our /stt skip-summary messages."""
        if msg is None:
            return False
        # Userbot sends are marked .out=True; only consider our own messages.
        if not getattr(msg, "out", False):
            return False
        text = msg.text or ""
        return "Skipped parts:" in text

    @staticmethod
    def extract_skipped_from_summary(text: str) -> Optional[Set[int]]:
        """Extract skipped chunk indices from a previously sent summary."""
        if not text:
            return None
        m = re.search(r"Skipped parts:\s*([0-9,\s\-]+)", text)
        if not m:
            return None
        spec = m.group(1).strip().rstrip('.,')
        return STTHandler.parse_chunk_spec(spec)

    async def process_retry_command(
        self,
        original_message: Message,
        summary_message: Message,
        client: TelegramClient,
        command_sender_info: str,
        chunk_filter_override: Optional[Set[int]] = None,
    ) -> None:
        """Walk the reply chain summary → /stt command → voice, then retry.

        ``chunk_filter_override`` (if given) takes precedence over the indices
        parsed from the summary text — letting users explicitly specify chunks
        when replying to a summary (e.g. ``/stt 21``).
        """
        chat_id = original_message.chat_id
        reply_to_id = original_message.id

        # 1. Determine which chunks to retry.
        if chunk_filter_override:
            chunks_to_retry: Optional[Set[int]] = chunk_filter_override
        else:
            chunks_to_retry = self.extract_skipped_from_summary(
                summary_message.text or ""
            )
            if not chunks_to_retry:
                await client.send_message(
                    chat_id,
                    "❌ Couldn't find any skipped parts in that summary to retry.",
                    reply_to=reply_to_id, parse_mode='md',
                )
                return

        # 2. Walk the reply chain to find the original voice message.
        voice = await self._resolve_voice_from_summary(summary_message, client)
        if voice is None:
            await client.send_message(
                chat_id,
                "❌ Original voice message is no longer available (was the /stt "
                "command or the voice deleted?).",
                reply_to=reply_to_id, parse_mode='md',
            )
            return

        self._logger.info(
            f"Retry: parts {sorted(chunks_to_retry)} from voice "
            f"msg {voice.id}; requested by '{command_sender_info}'"
        )

        await self.process_stt_command(
            original_message=original_message,
            replied_voice_message=voice,
            client=client,
            command_sender_info=command_sender_info,
            chunk_filter=chunks_to_retry,
        )

    async def _resolve_voice_from_summary(
        self,
        summary_message: Message,
        client: TelegramClient,
    ) -> Optional[Message]:
        """Walk summary → original /stt command → original voice message.

        Returns the voice ``Message`` if found and still has media, else None.
        """
        # Step 1: summary's reply target should be the original /stt command.
        reply_obj = getattr(summary_message, "reply_to", None)
        if reply_obj is None:
            return None
        stt_cmd_id = getattr(reply_obj, "reply_to_msg_id", None)
        if not stt_cmd_id:
            return None

        try:
            chat = await summary_message.get_chat()
        except Exception as e:
            self._logger.warning(f"Could not load chat for retry: {e}")
            return None

        try:
            stt_cmd = await client.get_messages(chat, ids=stt_cmd_id)
        except Exception as e:
            self._logger.warning(f"Could not load original /stt command: {e}")
            return None
        if stt_cmd is None:
            return None

        # Step 2: that command's reply target is the voice.
        stt_reply = getattr(stt_cmd, "reply_to", None)
        if stt_reply is None:
            return None
        voice_id = getattr(stt_reply, "reply_to_msg_id", None)
        if not voice_id:
            return None

        try:
            voice = await client.get_messages(chat, ids=voice_id)
        except Exception as e:
            self._logger.warning(f"Could not load original voice message: {e}")
            return None
        if voice is None or not getattr(voice, "media", None):
            return None
        return voice

    async def _build_summary(self, transcribed_text: str) -> str:
        """Generate the Persian summary, with Gemini fallback."""
        summary_prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
            transcribed_text=transcribed_text
        )

        summary_text: Optional[str] = None
        if self._ai_processor.is_configured:
            try:
                result = await self._ai_processor.execute_custom_prompt(
                    user_prompt=summary_prompt,
                    max_tokens=300,
                    temperature=0.5,
                    task_type="voice_summary",
                )
                summary_text = result.response_text
            except AIProcessorError as e:
                self._logger.error(f"AI summarization failed via primary provider: {e}")
                summary_text = await self._generate_persian_summary_with_gemini(transcribed_text)
                if not summary_text:
                    summary_text = f"AI Error: {e}"
        else:
            summary_text = await self._generate_persian_summary_with_gemini(transcribed_text)
            if not summary_text:
                summary_text = "AI features not configured for summarization."

        if not summary_text or summary_text.startswith("AI Error"):
            fallback = await self._generate_persian_summary_with_gemini(transcribed_text)
            if fallback:
                summary_text = fallback
            elif not summary_text:
                summary_text = "No summary available."

        cleaned_lines = [line.strip() for line in summary_text.splitlines() if line.strip()]
        if cleaned_lines:
            summary_text = " ".join(cleaned_lines)
        return self._trim_summary_text(summary_text)

    async def _generate_persian_summary_with_gemini(self, transcribed_text: str) -> Optional[str]:
        """Fallback summarization using Google Gemini if available."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        
        # gemini-1.5 is retired; default to the current free-tier Flash model.
        model_name = os.getenv("GEMINI_SUMMARY_MODEL", "gemini-2.5-flash")
        # Use centralized prompt from prompts.py
        prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
            transcribed_text=transcribed_text
        )
        
        def _call_gemini() -> Optional[str]:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            candidate = getattr(response, "text", None)
            if candidate and candidate.strip():
                return candidate.strip()
            
            parts = getattr(response, "candidates", None)
            if not parts:
                return None
            
            try:
                text_parts = []
                for part in response.candidates:
                    if hasattr(part, "content") and part.content:
                        for item in part.content.parts:
                            text_value = getattr(item, "text", None)
                            if text_value:
                                text_parts.append(text_value)
                combined = " ".join(text_parts).strip()
                return combined or None
            except Exception:
                return None
        
        try:
            result = await asyncio.to_thread(_call_gemini)
            if result:
                return result
        except Exception as exc:
            self._logger.error(f"Gemini fallback summarization failed: {exc}", exc_info=True)
        return None
    
    def _trim_summary_text(self, text: str) -> str:
        """Normalize summary text to two concise Persian sentences."""
        normalized = (
            text.replace("<|begin_of_sentence|>", "")
            .replace("<|end_of_sentence|>", "")
            .replace("<｜begin▁of▁sentence｜>", "")
            .replace("<｜end▁of▁sentence｜>", "")
        ).strip()
        sentences = re.split(r"(?<=[.!؟])\s+", normalized)
        kept: List[str] = []
        blacklist = ("اگر", "خوشحال", "Please wait اطلاعات بیشتر", "اگر نیاز")
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if any(phrase in s for phrase in blacklist):
                continue
            kept.append(s)
            if len(kept) == 2:
                break
        return " ".join(kept) if kept else normalized

