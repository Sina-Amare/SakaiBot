"""Google Gemini LLM provider implementation."""

import os
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from ..llm_interface import LLMProvider
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger
from ..persian_prompts import (
    TRANSLATION_PHONETIC_INSTRUCTION,
    TRANSLATION_SYSTEM_MESSAGE,
    CONVERSATION_ANALYSIS_PROMPT,
    CONVERSATION_ANALYSIS_SYSTEM_MESSAGE,
    QUESTION_ANSWER_PROMPT,
    QUESTION_ANSWER_SYSTEM_MESSAGE,
    VOICE_MESSAGE_SUMMARY_PROMPT
)


class GeminiProvider(LLMProvider):
    """Google Gemini provider for LLM operations."""
    
    def __init__(self, config: Any) -> None:
        """Initialize Gemini provider."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client = None
        self._api_key = config.gemini_api_key
        self._model = config.gemini_model
    
    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(
            self._api_key
            and "YOUR_GEMINI_API_KEY_HERE" not in (self._api_key or "")
            and len(self._api_key or "") > 10
        )
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "Google Gemini"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model
    
    def _get_client(self):
        """Get or create Gemini client."""
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        if self._client is None:
            try:
                from google import genai
                
                # Create client with API key
                self._client = genai.Client(api_key=self._api_key)
                
                self._logger.info(f"Initialized Gemini client with model: {self._model}")
                
            except ImportError:
                raise AIProcessorError(
                    "Google GenAI library not installed. Run: pip install google-genai"
                )
            except Exception as e:
                raise AIProcessorError(f"Failed to initialize Gemini client: {e}")
        
        return self._client
    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Execute a prompt using Google Gemini with retry logic."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        # Combine system message and user prompt if needed
        if system_message and system_message.strip():
            full_prompt = f"{system_message}\n\n{user_prompt}"
            self._logger.debug(f"Using system message with prompt")
        else:
            full_prompt = user_prompt
        
        # Log the exact prompt being sent for debugging
        self._logger.debug(f"Sending prompt to Gemini: '{full_prompt[:100]}...'")
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                
                self._logger.info(
                    f"Attempt {attempt + 1}: Sending prompt to Gemini '{self._model}'. "
                    f"Prompt length: {len(full_prompt)} chars"
                )
                
                # Use asyncio to run the synchronous call with proper config and timeout
                loop = asyncio.get_event_loop()
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: client.models.generate_content(
                                model=self._model,
                                contents=full_prompt,
                                config={
                                    "temperature": temperature,
                                    "top_p": 0.95,
                                    "top_k": 40,
                                }
                            )
                        ),
                        timeout=300  # 5 minute timeout for LLM response
                    )
                except asyncio.TimeoutError:
                    self._logger.error(f"LLM response timed out after 5 minutes for model '{self._model}'")
                    raise AIProcessorError("Request timed out. The LLM did not respond within the expected time. Try again later or with a shorter prompt.")
                
                # Debug log the response
                self._logger.debug(f"Response type: {type(response)}")
                
                # Extract text from response
                response_text = None
                
                # First try direct text attribute
                try:
                    if response and response.text:
                        response_text = response.text.strip()
                        self._logger.info(f"Got response text directly: {len(response_text)} chars")
                except Exception as e:
                    self._logger.warning(f"Could not get text directly: {e}")
                
                # If no text, check candidates
                if not response_text and response:
                    try:
                        if hasattr(response, 'candidates') and response.candidates:
                            for candidate in response.candidates:
                                # Check if candidate has content and content is not None
                                if hasattr(candidate, 'content') and candidate.content is not None:
                                    # Check if content has parts attribute and it's not None
                                    if hasattr(candidate.content, 'parts') and candidate.content.parts is not None:
                                        # Check if parts is iterable before trying to iterate
                                        try:
                                            # Verify that candidate.content.parts is iterable and not None
                                            if candidate.content.parts is not None and hasattr(candidate.content.parts, '__iter__'):
                                                for part in candidate.content.parts:
                                                    if hasattr(part, 'text') and part.text:
                                                        response_text = part.text.strip()
                                                        self._logger.info(f"Got text from candidate part: {len(response_text)} chars")
                                                        break
                                            else:
                                                self._logger.warning(f"candidate.content.parts is not iterable: {type(candidate.content.parts)}")
                                        except TypeError as e:
                                            # If parts is not iterable, it might be None or another non-iterable type
                                            self._logger.warning(f"Content parts is not iterable: {e}, likely filtered by safety policies or technical issue")
                                            # Check if this is a technical issue vs content filtering
                                            if "NoneType" in str(e) or "not iterable" in str(e).lower():
                                                # This is a technical issue, not content filtering
                                                self._logger.error(f"Technical error in response processing: {e}")
                                                # Continue to allow retry logic instead of raising content filtering error
                                                continue
                                            else:
                                                raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                                elif hasattr(candidate, 'finish_reason'):
                                    # Check if the candidate was blocked for safety reasons
                                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                                        finish_reason = str(candidate.finish_reason).lower()
                                        if 'safety' in finish_reason or 'blocked' in finish_reason:
                                            self._logger.warning(f"Response blocked by safety filters: {candidate.finish_reason}")
                                            raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                                
                                if response_text:
                                    break
                            
                            # If no response text was found but there were candidates, check if it's a technical issue vs content filtering
                            if not response_text and response.candidates:
                                # Check if any candidate was blocked for safety reasons
                                for candidate in response.candidates:
                                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                                        finish_reason = str(candidate.finish_reason).lower()
                                        if 'safety' in finish_reason or 'blocked' in finish_reason or 'finish_reason_safety' in finish_reason:
                                            self._logger.warning(f"Response was filtered by safety policies: {candidate.finish_reason}")
                                            raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                        
                        # Fallback: Check if response has other attributes that might contain text
                        if not response_text:
                            # Try alternative extraction methods
                            if hasattr(response, 'candidates') and response.candidates:
                                for candidate in response.candidates:
                                    # Handle case where content might be None but other fields exist
                                    if hasattr(candidate, 'content') and candidate.content is None:
                                        # This might be a safety block - check the candidate's finish reason
                                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                                            finish_reason = str(candidate.finish_reason).lower()
                                            if 'safety' in finish_reason or 'blocked' in finish_reason:
                                                self._logger.warning(f"Response blocked by safety filters: {candidate.finish_reason}")
                                                raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                                        else:
                                            # If content is None but no safety block, it's likely a technical issue
                                            self._logger.warning(f"No content in candidate and no safety block detected - possible technical issue")
                                            continue
                                    # Handle case where content exists but has no parts
                                    elif hasattr(candidate, 'content') and candidate.content is not None:
                                        # Check if content has text attribute directly
                                        if hasattr(candidate.content, 'text') and candidate.content.text:
                                            response_text = candidate.content.text.strip()
                                            self._logger.info(f"Got text from candidate content directly: {len(response_text)} chars")
                                            break
                                        # Try alternative access methods for content
                                        elif hasattr(candidate.content, 'parts') and candidate.content.parts is not None:
                                            # If parts exists but wasn't iterable earlier, try a different approach
                                            try:
                                                # Try to access parts as a list-like object
                                                if isinstance(candidate.content.parts, (list, tuple)):
                                                    for part in candidate.content.parts:
                                                        if hasattr(part, 'text') and part.text:
                                                            response_text = part.text.strip()
                                                            self._logger.info(f"Got text from candidate parts list: {len(response_text)} chars")
                                                            break
                                            except Exception:
                                                # If still failing, check for other possible structures
                                                pass
                    except TypeError as e:
                        # Check if this is a safety/content filtering issue vs technical error
                        error_str = str(e).lower()
                        if "none" in error_str and ("content" in error_str or "parts" in error_str):
                            # This is likely a technical issue accessing None content
                            self._logger.warning(f"Technical error accessing response content: {e}")
                            if attempt < max_retries - 1:
                                self._logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                # Provide clearer error message for technical issues
                                raise AIProcessorError(f"Technical error occurred while processing the response: {str(e)}. This appears to be a technical issue rather than content filtering.")
                        elif "safety" in error_str or "filter" in error_str or "blocked" in error_str:
                            # This is a content filtering issue
                            self._logger.warning(f"Content filtered by AI provider - response was blocked: {e}")
                            raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                        else:
                            self._logger.warning(f"Error extracting from candidates: {e}")
                            # If this is not the last attempt, retry
                            if attempt < max_retries - 1:
                                self._logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                raise AIProcessorError(f"Failed to extract response from AI provider: {e}")
                    except Exception as e:
                        self._logger.warning(f"Error extracting from candidates: {e}")
                        # Log the actual response structure for debugging
                        self._logger.debug(f"Full response structure: {dir(response) if response else 'None'}")
                        if hasattr(response, '__dict__'):
                            self._logger.debug(f"Response attributes: {response.__dict__}")
                        
                        # Check if this is a technical issue vs content filtering
                        error_str = str(e).lower()
                        if "safety" in error_str or "filter" in error_str or "blocked" in error_str or "finish_reason_safety" in error_str:
                            # This is a content filtering issue
                            self._logger.warning(f"Content was filtered by AI provider: {e}")
                            raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
                        else:
                            # This is likely a technical issue, not content filtering
                            self._logger.error(f"Technical error in response processing: {e}")
                            if attempt < max_retries - 1:
                                self._logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                # Provide clearer error message for technical issues
                                raise AIProcessorError(f"Technical error occurred while processing the response: {str(e)}. This appears to be a technical issue rather than content filtering.")
                
                # Check for safety blocks or other issues
                if not response_text:
                    if hasattr(response, 'prompt_feedback'):
                        feedback = response.prompt_feedback
                        self._logger.error(f"Prompt feedback: {feedback}")
                        if 'block_reason' in str(feedback).lower():
                            raise AIProcessorError("Content was blocked by safety filters. Try rephrasing.")
                    
                    # If this is not the last attempt, retry
                    if attempt < max_retries - 1:
                        self._logger.warning(f"No response on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Last attempt failed
                        response_text = "من درخواست شما رو دریافت کردم ولی نتونستم جواب مناسبی بدم. ممکنه مشکل از API باشه یا محتوا فیلتر شده. دوباره امتحان کن."
                
                if response_text:
                    self._logger.info(
                        f"Gemini '{self._model}' completed successfully. Response: {len(response_text)} chars"
                    )
                    return response_text
                
            except Exception as e:
                self._logger.error(
                    f"Attempt {attempt + 1} failed for Gemini '{self._model}': {e}",
                    exc_info=True
                )
                
                # If this is not the last attempt, retry
                if attempt < max_retries - 1:
                    self._logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    # All attempts failed
                    raise AIProcessorError(f"Failed after {max_retries} attempts: {e}")
        
        # Should not reach here
        raise AIProcessorError("Unexpected error in Gemini execution")
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text using Google Gemini with Persian phonetic support."""
        if not text:
            raise AIProcessorError("No text provided for translation")
        
        # Log the exact text being translated for debugging purposes
        self._logger.debug(f"Translation request - Text: '{text[:100]}...', Target: {target_language}, Source: {source_language}")
        
        # Build a clean translation prompt without sarcastic commentary
        if source_language.lower() == "auto":
            prompt = (
                f"Detect the language of the following text and then translate it to '{target_language}'.\n"
                f"Provide the Persian phonetic pronunciation for the translated text.\n\n"
                f"Text to translate:\n\"{text}\"\n\n"
                f"Output format:\n"
                f"[translated text] ([Persian phonetic pronunciation])\n\n"
                f"Example: Hello (هِلو)"
            )
        else:
            prompt = (
                f"Translate the following text from '{source_language}' to '{target_language}'.\n"
                f"Provide the Persian phonetic pronunciation for the translated text.\n\n"
                f"Text to translate:\n\"{text}\"\n\n"
                f"Output format:\n"
                f"[translated text] ([Persian phonetic pronunciation])\n\n"
                f"Example: Hello (هِلو)"
            )
        
        self._logger.info(
            f"Requesting translation for '{text[:50]}...' to {target_language} with phonetics."
        )
        
        # Use lower temperature for translation accuracy
        # No max_tokens limit to allow full translation
        raw_response = await self.execute_prompt(
            prompt,
            temperature=0.2,
            system_message="You are a precise translation assistant. Provide only the translation and phonetic pronunciation in the requested format. No commentary or additional text."
        )
        
        # Clean the response to ensure it follows the format: "translated text (persian pronunciation)"
        # Remove any extra text that might have been added
        import re
        # First, look for the pattern "translated text (pronunciation)" in the response
        match = re.search(r'(.+?)\s*\(\s*(.+?)\s*\)', raw_response.strip(), re.DOTALL)
        if match:
            translated_text = match.group(1).strip()
            pronunciation = match.group(2).strip()
            # Extract just the content without prefixes like "Translation:", "Phonetic:", etc.
            # Look for the actual translated text part
            translation_match = re.search(r'Translation:\s*(.+?)(?:\s*\n|$)', raw_response)
            phonetic_match = re.search(r'Phonetic:\s*\((.+?)\)', raw_response)
            
            if translation_match and phonetic_match:
                clean_translation = translation_match.group(1).strip()
                clean_pronunciation = phonetic_match.group(1).strip()
                return f"{clean_translation} ({clean_pronunciation})"
            else:
                # If we have the match from the general pattern, return that
                return f"{translated_text} ({pronunciation})"
        else:
            # If the response doesn't match the expected format, return it as is
            # but try to extract the most relevant part
            lines = raw_response.split('\n')
            for line in lines:
                line = line.strip()
                if '(' in line and ')' in line and line.count('(') == line.count(')'):
                    # This line likely contains the translation and pronunciation
                    return line
        
        # If no proper format found, return the raw response
        return raw_response
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "summary"
    ) -> str:
        """Analyze messages using Google Gemini with Persian analysis."""
        if not messages:
            raise AIProcessorError("No messages provided for analysis")
        
        # Format messages for analysis
        formatted_messages = []
        tehran_tz = pytz.timezone('Asia/Tehran')
        timestamps = []
        senders = set()
        
        for msg in messages:  # Process ALL messages (up to 10000)
            timestamp_str = ""
            if 'timestamp' in msg:
                try:
                    if isinstance(msg['timestamp'], str):
                        timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    else:
                        timestamp = msg['timestamp']
                    
                    if timestamp.tzinfo is None:
                        timestamp = pytz.utc.localize(timestamp)
                    
                    timestamps.append(timestamp)
                    tehran_time = timestamp.astimezone(tehran_tz)
                    timestamp_str = tehran_time.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    self._logger.warning(f"Could not parse timestamp: {e}")
                    timestamp_str = str(msg.get('timestamp', ''))
            
            sender_name = msg.get('sender_name', 'Unknown')
            senders.add(sender_name)
            message_text = msg.get('text', '[No text]')
            
            formatted_messages.append(f"[{timestamp_str}] {sender_name}: {message_text}")
        
        messages_text = "\n".join(formatted_messages)
        num_messages = len(formatted_messages)
        num_senders = len(senders)
        
        # Calculate duration
        duration_minutes = 0
        if len(timestamps) >= 2:
            duration = max(timestamps) - min(timestamps)
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Build analysis prompt based on type
        if analysis_type == "persian_detailed":
            # Use the detailed Persian analysis prompt
            prompt = CONVERSATION_ANALYSIS_PROMPT.format(
                num_messages=num_messages,
                num_senders=num_senders,
                duration_minutes=duration_minutes,
                actual_chat_messages=messages_text
            )
            system_message = CONVERSATION_ANALYSIS_SYSTEM_MESSAGE
        elif analysis_type == "voice_summary":
            # Summary for voice messages
            prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
                transcribed_text=messages_text
            )
            system_message = None
        else:
            # Default summary
            prompt = f"""Please analyze and summarize the following chat messages.
Provide a comprehensive summary including:
1. Main topics discussed
2. Key participants and their contributions
3. Important decisions or conclusions
4. Overall sentiment

Messages:
{messages_text}"""
            system_message = None
        
        self._logger.info(
            f"Sending conversation ({num_messages} messages) for {analysis_type} analysis"
        )
        
        # Use lower temperature for analysis accuracy
        return await self.execute_prompt(
            prompt, 
            max_tokens=100000, 
            temperature=0.4,
            system_message=system_message
        )
    
    async def answer_question_from_history(
        self,
        messages: List[Dict[str, Any]],
        question: str
    ) -> str:
        """Answer a question based on chat history using Persian prompts."""
        if not messages:
            raise AIProcessorError("No messages provided for question answering")
        
        if not question:
            raise AIProcessorError("No question provided")
        
        # Format messages for context
        formatted_messages = []
        for msg in messages:  # Process ALL messages for full context
            sender = msg.get('sender_name', 'Unknown')
            text = msg.get('text', '')
            if text:
                formatted_messages.append(f"{sender}: {text}")
        
        if not formatted_messages:
            return "هیچ پیام متنی در تاریخچه ارائه شده یافت نشد."
        
        combined_history = "\n".join(formatted_messages)
        
        # Build Persian question-answering prompt
        prompt = QUESTION_ANSWER_PROMPT.format(
            combined_history_text=combined_history,
            user_question=question
        )
        
        self._logger.info(
            f"Answering question '{question[:50]}...' based on {len(formatted_messages)} messages"
        )
        
        return await self.execute_prompt(
            prompt,
            max_tokens=100000,
            temperature=0.5,
            system_message=QUESTION_ANSWER_SYSTEM_MESSAGE
        )
    
    async def close(self) -> None:
        """Clean up Gemini client."""
        self._client = None