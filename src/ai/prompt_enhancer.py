"""LLM-based prompt enhancement for image generation."""

from typing import Optional, Tuple

from ..core.constants import MAX_IMAGE_PROMPT_LENGTH
from ..core.config import get_settings
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
        Enhance user prompt using LLM.
        Tries OpenRouter first, falls back to Gemini on error.
        
        Args:
            user_prompt: Original user prompt
            
        Returns:
            Tuple of (enhanced_prompt, model_used)
            - enhanced_prompt: Enhanced prompt (or original if all enhancement fails)
            - model_used: "openrouter", "gemini", or "none" (fallback to original)
        """
        if not self._ai_processor.is_configured:
            self._logger.warning("AI processor not configured, using original prompt")
            return (user_prompt, "none")
        
        # Try OpenRouter first
        enhanced, model_used = await self._try_enhance_with_openrouter(user_prompt)
        if enhanced:
            return (enhanced, model_used)
        
        # Fallback to Gemini
        enhanced, model_used = await self._try_enhance_with_gemini(user_prompt)
        if enhanced:
            return (enhanced, model_used)
        
        # All failed, return original
        self._logger.warning("All enhancement methods failed, using original prompt")
        return (user_prompt, "none")
    
    async def _try_enhance_with_openrouter(self, user_prompt: str) -> Tuple[Optional[str], str]:
        """
        Try to enhance prompt using OpenRouter.
        
        Returns:
            Tuple of (enhanced_prompt or None, "openrouter" or "")
        """
        try:
            # Check if OpenRouter is configured (only check API key, not LLM_PROVIDER)
            config = get_settings()
            
            if not config.openrouter_api_key:
                self._logger.info("OpenRouter API key not configured, skipping")
                return (None, "")
            
            self._logger.info(f"Enhancing prompt with OpenRouter: '{user_prompt[:50]}...'")
            
            # Temporarily switch to OpenRouter (similar to Gemini fallback)
            original_provider = config.llm_provider
            config.llm_provider = "openrouter"
            
            try:
                # Format the enhancement prompt
                enhancement_prompt = IMAGE_PROMPT_ENHANCEMENT_PROMPT.format(
                    user_prompt=user_prompt
                )
                
                # Call AI processor to enhance the prompt
                result = await self._ai_processor.execute_custom_prompt(
                    user_prompt=enhancement_prompt,
                    max_tokens=2000,  # Short enhanced prompt
                    task_type="prompt_enhancer"
                )
                enhanced = result.response_text
                
                if not enhanced or not enhanced.strip():
                    self._logger.warning("Empty response from OpenRouter")
                    return (None, "")
                
                # Clean and validate enhanced prompt
                cleaned = self._clean_enhanced_prompt(enhanced)
                if cleaned:
                    self._logger.info(f"Successfully enhanced with OpenRouter: '{cleaned[:100]}...'")
                    return (cleaned, "openrouter")
                
                return (None, "")
            finally:
                # Restore original provider
                config.llm_provider = original_provider
            
        except Exception as e:
            self._logger.warning(f"OpenRouter enhancement failed: {e}, will try Gemini fallback")
            return (None, "")
    
    async def _try_enhance_with_gemini(self, user_prompt: str) -> Tuple[Optional[str], str]:
        """
        Try to enhance prompt using Gemini (fallback).
        
        Returns:
            Tuple of (enhanced_prompt or None, "gemini" or "")
        """
        try:
            # Check if Gemini is configured
            config = get_settings()
            
            if not config.gemini_api_key:
                self._logger.warning("Gemini not configured, cannot use fallback")
                return (None, "")
            
            self._logger.info(f"Enhancing prompt with Gemini (fallback): '{user_prompt[:50]}...'")
            
            # Temporarily switch to Gemini
            original_provider = config.llm_provider
            config.llm_provider = "gemini"
            
            try:
                # Format the enhancement prompt
                enhancement_prompt = IMAGE_PROMPT_ENHANCEMENT_PROMPT.format(
                    user_prompt=user_prompt
                )
                
                # Call AI processor to enhance the prompt
                result = await self._ai_processor.execute_custom_prompt(
                    user_prompt=enhancement_prompt,
                    max_tokens=2000,  # Short enhanced prompt
                    task_type="prompt_enhancer"
                )
                enhanced = result.response_text
                
                if not enhanced or not enhanced.strip():
                    self._logger.warning("Empty response from Gemini")
                    return (None, "")
                
                # Clean and validate enhanced prompt
                cleaned = self._clean_enhanced_prompt(enhanced)
                if cleaned:
                    self._logger.info(f"Successfully enhanced with Gemini: '{cleaned[:100]}...'")
                    return (cleaned, "gemini")
                
                return (None, "")
            finally:
                # Restore original provider
                config.llm_provider = original_provider
                
        except Exception as e:
            self._logger.error(f"Gemini enhancement failed: {e}", exc_info=True)
            return (None, "")
    
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
        
        # Final validation
        if not enhanced or len(enhanced) < 10:
            return None
        
        return enhanced

