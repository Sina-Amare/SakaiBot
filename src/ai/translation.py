"""
Translation module for Persian language support.

This module handles translation of English analysis to Persian using Gemini 2.5 Flash,
with tone-specific prompting for FUN, ROMANCE, and GENERAL analysis types.
"""

import asyncio
from typing import Literal
from datetime import datetime

import google.generativeai as genai

from ..utils.logging import get_logger

logger = get_logger(__name__)

AnalysisType = Literal["fun", "romance", "general"]
OutputLanguage = Literal["english", "persian"]


class TranslationError(Exception):
    """Raised when translation fails after all retries."""
    pass


async def translate_analysis(
    english_analysis: str,
    analysis_type: AnalysisType,
    output_language: OutputLanguage = "persian",
    gemini_api_key: str = None,
) -> str:
    """
    Translate English analysis to Persian using Gemini 2.5 Flash.
    
    This function uses tone-specific translation prompts to ensure
    the Persian translation matches the style of each analysis type:
    - FUN: Casual, friendly Persian (خودمونی)
    - ROMANCE: Semi-formal, emotionally intelligent
    - GENERAL: Professional, clear Persian
    
    Args:
        english_analysis: English analysis text (with HTML formatting)
        analysis_type: Type of analysis (fun/romance/general)
        output_language: Target language ('english' or 'persian')
        gemini_api_key: Gemini API key (required if not configured globally)
    
    Returns:
        Translated Persian text with HTML preserved, or original English if output_language='english'
    
    Raises:
        TranslationError: If translation fails after all retries
        ValueError: If invalid analysis_type or missing API key
    
    Examples:
        >>> result = await translate_analysis(
        ...     "This conversation is hilarious...",
        ...     "fun",
        ...     "persian"
        ... )
        >>> assert "است" in result  # Persian text
        
        >>> english_result = await translate_analysis(
        ...     "This conversation is...",
        ...     "fun",
        ...     "english"
        ... )
        >>> assert english_result == "This conversation is..."  # Unchanged
    """
    # Validate inputs
    if analysis_type not in ["fun", "romance", "general"]:
        raise ValueError(f"Invalid analysis_type: {analysis_type}. Must be 'fun', 'romance', or 'general'")
    
    # Skip translation if English requested
    if output_language == "english":
        logger.info(f"Skipping translation: English output requested for {analysis_type} analysis")
        return english_analysis
    
    # Import translation prompts (will be added in Commit 2)
    try:
        from ..ai.prompts import (
            FUN_TRANSLATION_PROMPT,
            ROMANCE_TRANSLATION_PROMPT,
            GENERAL_TRANSLATION_PROMPT,
        )
    except ImportError:
        logger.error("Translation prompts not found in prompts.py. Please add translation prompts.")
        raise TranslationError("Translation prompts not configured")
    
    # Select appropriate translation prompt
    prompt_map = {
        "fun": FUN_TRANSLATION_PROMPT,
        "romance": ROMANCE_TRANSLATION_PROMPT,
        "general": GENERAL_TRANSLATION_PROMPT,
    }
    
    translation_prompt = prompt_map[analysis_type]
    formatted_prompt = translation_prompt.format(english_analysis=english_analysis)
    
    # Configure Gemini API
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
    
    # Initialize Gemini 2.5 Flash model
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",  # Stable version, not experimental
        generation_config={
            "temperature": 0.3,  # Low temperature for consistency
            "top_p": 0.9,
            "max_output_tokens": 16000,
        },
    )
    
    # Retry logic with exponential backoff
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            start_time = datetime.now()
            
            logger.info(f"Translating {analysis_type} analysis to Persian (attempt {attempt + 1}/{max_attempts})")
            
            # Generate translation with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    formatted_prompt
                ),
                timeout=45.0  # 45-second timeout for longer analyses
            )
            
            latency = (datetime.now() - start_time).total_seconds()
            persian = response.text
            
            # Basic validation
            if not persian or len(persian) < 100:
                logger.warning(f"Translation output too short: {len(persian)} chars")
                raise TranslationError("Translation output too short")
            
            # Check for Persian characters
            if not _contains_persian_script(persian):
                logger.warning("Translation output contains no Persian characters")
                raise TranslationError("No Persian text detected in translation")
            
            # Success - log metrics
            logger.info(
                f"Translation successful: {analysis_type}, "
                f"latency={latency:.2f}s, "
                f"input={len(english_analysis)} chars, "
                f"output={len(persian)} chars"
            )
            
            return persian
            
        except asyncio.TimeoutError:
            logger.error(f"Translation timeout after 45s (attempt {attempt + 1}/{max_attempts})")
            if attempt == max_attempts - 1:
                raise TranslationError("Translation timeout after all retries")
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)
            
        except Exception as e:
            logger.error(f"Translation error (attempt {attempt + 1}/{max_attempts}): {e}")
            if attempt == max_attempts - 1:
                raise TranslationError(f"Translation failed: {e}") from e
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)
    
    # Should not reach here
    raise TranslationError("Translation failed after all retries")


def _contains_persian_script(text: str) -> bool:
    """
    Check if text contains Persian/Arabic script characters.
    
    Uses Unicode range U+0600-U+06FF which covers:
    - Basic Arabic script (used by Persian, Arabic, Urdu)
    - Persian-specific letters (گ چ پ ژ)
    
    Args:
        text: Text to check
    
    Returns:
        True if Persian/Arabic characters found, False otherwise
    
    Examples:
        >>> _contains_persian_script("Hello World")
        False
        >>> _contains_persian_script("سلام دنیا")
        True
        >>> _contains_persian_script("Mixed: سلام and hello")
        True
    """
    import re
    
    # Persian/Arabic Unicode range
    PERSIAN_PATTERN = re.compile(r'[\u0600-\u06FF]+')
    return bool(PERSIAN_PATTERN.search(text))
