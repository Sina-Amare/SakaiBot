"""LLM-based prompt enhancement for image generation."""

from typing import Optional, Tuple

from ..core.constants import MAX_IMAGE_PROMPT_LENGTH
from ..utils.logging import get_logger
from .processor import AIProcessor
from .prompts import (
    IMAGE_PROMPT_ENHANCEMENT_PROMPT
)


class PromptEnhancer:
    """Enhances user prompts for better image generation using LLM."""

    def __init__(self, ai_processor: AIProcessor):
        """
        Initialize PromptEnhancer.

        Args:
            ai_processor: AI processor instance for LLM calls
        """
        self._ai_processor = ai_processor
        self._logger = get_logger(self.__class__.__name__)

    async def enhance_prompt(self, user_prompt: str) -> Tuple[str, str]:
        """
        Enhance a user prompt for image generation using the LLM.

        Delegates to ``AIProcessor.execute_custom_prompt``, which already
        performs configured provider fallback internally. (Previously this
        class switched ``config.llm_provider`` at runtime to "force" a
        provider — that was a no-op, because AIProcessor builds its provider
        once at construction and never re-reads config.)

        Args:
            user_prompt: Original user prompt

        Returns:
            Tuple of (enhanced_prompt, model_used)
            - enhanced_prompt: Enhanced prompt, or the original if enhancement
              fails or is unavailable.
            - model_used: "gemini", "openrouter", or "none" (original kept).
        """
        if not self._ai_processor.is_configured:
            self._logger.warning(
                "AI processor not configured, using original prompt"
            )
            return (user_prompt, "none")

        try:
            enhancement_prompt = IMAGE_PROMPT_ENHANCEMENT_PROMPT.format(
                user_prompt=user_prompt
            )
            result = await self._ai_processor.execute_custom_prompt(
                user_prompt=enhancement_prompt,
                max_tokens=2000,  # Short enhanced prompt
                task_type="prompt_enhancer",
            )
            enhanced = result.response_text

            if not enhanced or not enhanced.strip():
                self._logger.warning(
                    "Empty response from LLM, using original prompt"
                )
                return (user_prompt, "none")

            cleaned = self._clean_enhanced_prompt(enhanced)
            if not cleaned:
                self._logger.warning(
                    "Enhanced prompt failed validation, using original prompt"
                )
                return (user_prompt, "none")

            # AIProcessor records provider_used, including when it switched to
            # a configured fallback provider mid-call.
            if getattr(result, "provider_used", ""):
                provider = result.provider_used.lower()
                model_used = "gemini" if "gemini" in provider else "openrouter"
            elif getattr(result, "provider_fallback_applied", False):
                model_used = "fallback"
            else:
                provider = self._ai_processor.provider_name.lower()
                model_used = "gemini" if "gemini" in provider else "openrouter"

            self._logger.info(
                f"Enhanced prompt via {model_used}: '{cleaned[:100]}...'"
            )
            return (cleaned, model_used)

        except Exception as e:
            self._logger.warning(
                f"Prompt enhancement failed ({e}), using original prompt"
            )
            return (user_prompt, "none")

    def _clean_enhanced_prompt(self, enhanced: str) -> Optional[str]:
        """
        Clean and validate enhanced prompt output.

        Args:
            enhanced: Raw LLM output

        Returns:
            Cleaned prompt or None if invalid
        """
        enhanced = enhanced.strip()

        # Remove any markdown formatting that might have been added
        if enhanced.startswith("```"):
            # Remove code block markers
            lines = enhanced.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            enhanced = "\n".join(lines).strip()

        # Validate length
        if len(enhanced) > MAX_IMAGE_PROMPT_LENGTH:
            self._logger.warning(
                f"Enhanced prompt too long ({len(enhanced)} chars), "
                f"truncating to {MAX_IMAGE_PROMPT_LENGTH}"
            )
            # Truncate at word boundary
            enhanced = enhanced[:MAX_IMAGE_PROMPT_LENGTH].rsplit(" ", 1)[0]

        # Sanitize: remove any extra commentary or explanations.
        # The LLM should only return the enhanced prompt, but sometimes it adds
        # explanations.
        lines = enhanced.split("\n")
        # Take the first substantial line (usually the enhanced prompt)
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and not line.startswith(
                ("Enhanced", "Here", "The")
            ):
                enhanced = line
                break

        # Final validation
        if not enhanced or len(enhanced) < 10:
            return None

        return enhanced
