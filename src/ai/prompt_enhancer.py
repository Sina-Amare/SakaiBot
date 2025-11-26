"""LLM-based prompt enhancement for image generation."""

from typing import Optional

from ..core.constants import MAX_IMAGE_PROMPT_LENGTH
from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger
from .processor import AIProcessor
from .prompts import (
    IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE,
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
    
    async def enhance_prompt(self, user_prompt: str) -> str:
        """
        Enhance user prompt using LLM.
        
        Args:
            user_prompt: Original user prompt
            
        Returns:
            Enhanced prompt (or original if enhancement fails)
        """
        if not self._ai_processor.is_configured:
            self._logger.warning("AI processor not configured, using original prompt")
            return user_prompt
        
        try:
            # Format the enhancement prompt
            enhancement_prompt = IMAGE_PROMPT_ENHANCEMENT_PROMPT.format(
                user_prompt=user_prompt
            )
            
            self._logger.info(f"Enhancing prompt: '{user_prompt[:50]}...'")
            
            # Call AI processor to enhance the prompt
            enhanced = await self._ai_processor.execute_custom_prompt(
                user_prompt=enhancement_prompt,
                system_message=IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE
            )
            
            if not enhanced or not enhanced.strip():
                self._logger.warning("Empty response from LLM, using original prompt")
                return user_prompt
            
            # Clean and validate enhanced prompt
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
                    f"Enhanced prompt too long ({len(enhanced)} chars), truncating to {MAX_IMAGE_PROMPT_LENGTH}"
                )
                enhanced = enhanced[:MAX_IMAGE_PROMPT_LENGTH].rsplit(" ", 1)[0]  # Truncate at word boundary
            
            # Sanitize: remove any extra commentary or explanations
            # The LLM should only return the enhanced prompt, but sometimes it adds explanations
            lines = enhanced.split("\n")
            # Take the first substantial line (usually the enhanced prompt)
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and not line.startswith(("Enhanced", "Here", "The")):
                    enhanced = line
                    break
            
            self._logger.info(f"Enhanced prompt: '{enhanced[:100]}...'")
            return enhanced
            
        except AIProcessorError as e:
            self._logger.warning(f"AI processor error during enhancement: {e}, using original prompt")
            return user_prompt
        except Exception as e:
            self._logger.error(f"Unexpected error during prompt enhancement: {e}", exc_info=True)
            return user_prompt

