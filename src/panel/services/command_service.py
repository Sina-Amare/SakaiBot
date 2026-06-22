"""Command service: runs the 7 SakaiBot commands and RETURNS the result for the
panel to render. It calls the existing AI core (which returns values) and the
media generators. It NEVER sends/edits/forwards anything to Telegram.

Results envelope:
    {"ok": True, "kind": "text"|"image"|"audio",
     "html": "<rendered html>",            # text/caption
     "text": "raw text",                   # stt transcript
     "media_url": "/api/cmd/result-media/<token>",  # image/audio
     "meta": {...}}                         # model/provider/latency/tokens/...
"""

import asyncio
import secrets
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger
from ..errors import PanelError, PanelNotFound

logger = get_logger(__name__)


class CommandService:
    def __init__(self, state: Any) -> None:
        self.state = state
        self._ffmpeg_ready = False

    # ---------- result media token registry ----------
    def _register_media(self, path: str, mime: str) -> str:
        token = secrets.token_urlsafe(16)
        self.state.result_tokens[token] = {"path": path, "mime": mime}
        return f"/api/cmd/result-media/{token}"

    # ---------- text rendering ----------
    def _render_text(self, result: Any) -> Dict[str, Any]:
        from ...ai.response_metadata import AIResponseMetadata, build_response_parts
        from ...utils.telegram_html import clean_telegram_html

        if isinstance(result, AIResponseMetadata):
            header, footer = build_response_parts(result)
            full = header + (result.response_text or "") + footer
            meta = {
                "model": result.model_used,
                "provider": result.provider_used,
                "latency": result.latency_seconds,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "thinking_applied": result.thinking_applied,
                "web_search_applied": result.web_search_applied,
                "provider_fallback": result.provider_fallback_applied,
            }
        else:
            full = str(result)
            meta = {}
        return {"ok": True, "kind": "text", "html": clean_telegram_html(full), "meta": meta}

    def _ensure_ai(self) -> None:
        if not self.state.ai_processor.is_configured:
            raise PanelError("AI provider is not configured. Check /status.", status_code=503)

    # ---------- prompt ----------
    async def run_prompt(self, text: str, *, think: bool = False, web: bool = False) -> Dict[str, Any]:
        self._ensure_ai()
        from ...utils.validators import InputValidator
        from ...ai.prompts import PROMPT_ADAPTIVE_PROMPT, get_telegram_formatting_guidelines

        text = (text or "").strip()
        if not text:
            raise PanelError("Prompt text is required.")
        try:
            text = InputValidator.validate_prompt(text)
        except ValueError as exc:
            raise PanelError(str(exc))

        guidelines = get_telegram_formatting_guidelines("persian")
        full_prompt = PROMPT_ADAPTIVE_PROMPT.format(user_prompt=text + guidelines)
        result = await self.state.ai_processor.execute_custom_prompt(
            user_prompt=full_prompt,
            max_tokens=32000,
            task_type="prompt",
            use_thinking=think,
            use_web_search=web,
        )
        return self._render_text(result)

    # ---------- translate ----------
    async def run_translate(self, text: str, target_lang: str, source: str = "auto") -> Dict[str, Any]:
        self._ensure_ai()
        from ...utils.validators import InputValidator

        text = (text or "").strip()
        target_lang = (target_lang or "").strip()
        if not text or not target_lang:
            raise PanelError("Both text and target language are required.")
        if not InputValidator.validate_language_code(target_lang):
            raise PanelError(f"'{target_lang}' is not a valid language code.")
        result = await self.state.ai_processor.translate_text_with_phonetics(
            text_to_translate=text, target_language=target_lang, source_language=source or "auto"
        )
        return self._render_text(result)

    # ---------- analyze ----------
    async def run_analyze(
        self,
        entity_id: int,
        *,
        count: int = 100,
        mode: str = "general",
        language: str = "persian",
        think: bool = False,
    ) -> Dict[str, Any]:
        self._ensure_ai()
        messages = await self.state.entity.messages_for_ai(entity_id, count)
        if not messages:
            raise PanelError("No text messages found in that chat to analyze.")
        result = await self.state.ai_processor.analyze_conversation_messages(
            messages_data=messages,
            analysis_mode=mode,
            output_language=language,
            use_thinking=think,
        )
        out = self._render_text(result)
        out["meta"] = {**out.get("meta", {}), "messages": len(messages), "mode": mode}
        return out

    # ---------- tellme ----------
    async def run_tellme(
        self,
        entity_id: int,
        question: str,
        *,
        count: int = 100,
        think: bool = False,
        web: bool = False,
    ) -> Dict[str, Any]:
        self._ensure_ai()
        question = (question or "").strip()
        if not question:
            raise PanelError("A question is required.")
        messages = await self.state.entity.messages_for_ai(entity_id, count)
        if not messages:
            raise PanelError("No text messages found in that chat.")
        result = await self.state.ai_processor.answer_question_from_chat_history(
            messages_data=messages, user_question=question, use_thinking=think, use_web_search=web
        )
        return self._render_text(result)

    # ---------- image ----------
    async def run_image(self, model: str, prompt: str) -> Dict[str, Any]:
        model = (model or "flux").strip().lower()
        prompt = (prompt or "").strip()
        if model not in ("flux", "sdxl"):
            raise PanelError("Model must be 'flux' or 'sdxl'.")
        if not prompt:
            raise PanelError("Image prompt is required.")

        enhanced, model_used = await self.state.prompt_enhancer.enhance_prompt(prompt)
        if model == "flux":
            ok, path, err = await self.state.image_generator.generate_with_flux(enhanced)
        else:
            ok, path, err = await self.state.image_generator.generate_with_sdxl(enhanced)
        if not ok or not path:
            raise PanelError(err or "Image generation failed.", status_code=502)
        url = self._register_media(path, "image/png")
        return {
            "ok": True,
            "kind": "image",
            "media_url": url,
            "meta": {"model": model, "enhanced_prompt": enhanced, "enhancer": model_used},
        }

    # ---------- tts ----------
    async def run_tts(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            raise PanelError("Text to speak is required.")
        kwargs: Dict[str, Any] = {}
        if voice:
            kwargs["voice"] = voice
        path = await self.state.tts_processor.generate_speech_file(text, **kwargs)
        if not path:
            raise PanelError("TTS generation failed.", status_code=502)
        url = self._register_media(path, "audio/wav")
        return {"ok": True, "kind": "audio", "media_url": url, "meta": {"voice": voice}}

    # ---------- stt ----------
    def _ensure_ffmpeg(self) -> None:
        if self._ffmpeg_ready:
            return
        import os

        ff = getattr(self.state.config, "ffmpeg_path_resolved", None)
        if ff and Path(ff).is_file():
            from pydub import AudioSegment

            AudioSegment.converter = ff
            AudioSegment.ffmpeg = ff
            ff_dir = str(Path(ff).parent)
            if ff_dir not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = ff_dir + os.pathsep + os.environ.get("PATH", "")
        self._ffmpeg_ready = True

    @staticmethod
    def _to_wav(src: str, dst: str) -> None:
        """Decode any audio (ogg/opus/mp3/...) to mono 16kHz PCM WAV."""
        from pydub import AudioSegment

        seg = AudioSegment.from_file(src)
        seg = seg.set_channels(1).set_frame_rate(16000)
        seg.export(dst, format="wav")

    async def run_stt(self, entity_id: int, message_id: int) -> Dict[str, Any]:
        client = self.state.client
        if client is None:
            raise PanelError("Telegram client unavailable.", status_code=503)
        self._ensure_ffmpeg()

        msg = await self.state.throttle.tg_read(
            lambda: client.get_messages(int(entity_id), ids=int(message_id))
        )
        if not msg or getattr(msg, "media", None) is None:
            raise PanelNotFound("That message has no media.")
        is_audio = bool(getattr(msg, "voice", None) or getattr(msg, "audio", None))
        if not is_audio:
            doc = getattr(msg, "document", None)
            mime = (getattr(doc, "mime_type", "") or "").lower() if doc else ""
            is_audio = mime.startswith("audio/")
        if not is_audio:
            raise PanelError("That message is not a voice/audio message.")

        tmp_base = Path(tempfile.gettempdir()) / f"panel_stt_{entity_id}_{message_id}_{uuid.uuid4().hex[:6]}"
        downloaded = await self.state.throttle.tg_read(
            lambda: client.download_media(msg.media, file=str(tmp_base)), kind="download"
        )
        if not downloaded:
            raise PanelError("Could not download the voice message.", status_code=502)

        # Telegram voice notes are OGG/Opus; SpeechRecognition only reads PCM
        # WAV/AIFF/FLAC. Convert to mono/16kHz WAV first (off the event loop),
        # mirroring the chat STT handler. Without this, short clips that take
        # the single-chunk path fail with a "not a RIFF file" error.
        wav_path = f"{tmp_base}.stt.wav"
        try:
            await asyncio.to_thread(self._to_wav, str(downloaded), wav_path)
        except Exception as exc:  # noqa: BLE001
            raise PanelError(
                f"Could not decode the audio (is FFmpeg installed?): {exc}",
                status_code=502,
            )

        # Unintelligible / silent audio raises AIProcessorError — that's a
        # normal outcome for a voice note, not a panel failure. Return a
        # graceful empty transcript instead of a 500.
        note = None
        try:
            transcript = await self.state.stt_processor.transcribe_voice_to_text(wav_path)
        except AIProcessorError as exc:
            transcript = ""
            note = str(exc)
        transcript = (transcript or "").strip()

        from ...utils.helpers import clean_temp_files

        clean_temp_files(wav_path)

        from ...utils.telegram_html import clean_telegram_html

        if transcript:
            html = clean_telegram_html(transcript)
        else:
            html = f"<i>({note or 'no speech detected'})</i>"
        result: Dict[str, Any] = {
            "ok": True,
            "kind": "text",
            "text": transcript,
            "html": html,
        }
        try:
            url = self._register_media(str(downloaded), self.state.entity._guess_mime(Path(downloaded)))
            result["media_url"] = url
        except Exception:  # noqa: BLE001 - audio playback is a bonus
            pass
        return result
