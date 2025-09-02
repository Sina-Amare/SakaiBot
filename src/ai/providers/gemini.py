"""Google Gemini LLM provider implementation."""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from ..llm_interface import LLMProvider
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger


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
                
                # Set API key in environment if not already set
                if not os.environ.get("GEMINI_API_KEY"):
                    os.environ["GEMINI_API_KEY"] = self._api_key
                
                # Create client
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
        """Execute a prompt using Google Gemini."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        try:
            client = self._get_client()
            
            # Combine system message and user prompt if needed
            if system_message and system_message.strip():
                full_prompt = f"{system_message}\n\n{user_prompt}"
                self._logger.debug(f"Using system message with prompt")
            else:
                full_prompt = user_prompt
            
            self._logger.info(
                f"Sending prompt to Gemini model '{self._model}'. "
                f"Prompt preview: '{user_prompt[:100]}...'"
            )
            
            # Generate content using Gemini
            # Note: google-genai uses synchronous API, but we wrap it for consistency
            response = client.models.generate_content(
                model=self._model,
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            
            response_text = response.text.strip()
            self._logger.info(
                f"Gemini model '{self._model}' responded successfully"
            )
            return response_text
        
        except Exception as e:
            self._logger.error(
                f"Error calling Gemini API with model '{self._model}': {e}",
                exc_info=True
            )
            raise AIProcessorError(f"Could not get response from Gemini: {e}")
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text using Google Gemini."""
        if not text:
            raise AIProcessorError("No text provided for translation")
        
        # Build translation prompt
        if target_language.lower() in ["fa", "farsi", "persian"]:
            prompt = f"""Translate the following text to Persian (Farsi).
Provide the translation in this format:
Persian: [translation]
Phonetic: [pronunciation in English letters]

Text to translate: {text}"""
        else:
            source_part = f"from {source_language} " if source_language != "auto" else ""
            prompt = f"Translate the following text {source_part}to {target_language}:\n\n{text}"
        
        # Use lower temperature for translation accuracy
        return await self.execute_prompt(prompt, temperature=0.3)
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "summary"
    ) -> str:
        """Analyze messages using Google Gemini."""
        if not messages:
            raise AIProcessorError("No messages provided for analysis")
        
        # Format messages for analysis
        formatted_messages = []
        tehran_tz = pytz.timezone('Asia/Tehran')
        
        for msg in messages[-100:]:  # Limit to last 100 messages
            timestamp_str = ""
            if 'timestamp' in msg:
                try:
                    if isinstance(msg['timestamp'], str):
                        timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    else:
                        timestamp = msg['timestamp']
                    
                    if timestamp.tzinfo is None:
                        timestamp = pytz.utc.localize(timestamp)
                    
                    tehran_time = timestamp.astimezone(tehran_tz)
                    timestamp_str = tehran_time.strftime('%Y-%m-%d %H:%M:%S Tehran')
                except Exception as e:
                    self._logger.warning(f"Could not parse timestamp: {e}")
                    timestamp_str = str(msg.get('timestamp', ''))
            
            sender_name = msg.get('sender_name', 'Unknown')
            message_text = msg.get('text', '[No text]')
            
            formatted_messages.append(f"[{timestamp_str}] {sender_name}: {message_text}")
        
        messages_text = "\n".join(formatted_messages)
        
        # Build analysis prompt based on type
        if analysis_type == "summary":
            prompt = f"""Please analyze and summarize the following chat messages.
Provide a comprehensive summary including:
1. Main topics discussed
2. Key participants and their contributions
3. Important decisions or conclusions
4. Overall sentiment

Messages:
{messages_text}"""
        else:
            prompt = f"""Analyze the following chat messages:

{messages_text}

Provide a detailed analysis."""
        
        # Use lower temperature for analysis accuracy
        return await self.execute_prompt(prompt, max_tokens=2000, temperature=0.5)
    
    async def close(self) -> None:
        """Clean up Gemini client."""
        self._client = None