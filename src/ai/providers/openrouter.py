"""OpenRouter LLM provider implementation."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from openai import AsyncOpenAI

from ..llm_interface import LLMProvider
from ...core.constants import OPENROUTER_HEADERS
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider for LLM operations."""
    
    def __init__(self, config: Any) -> None:
        """Initialize OpenRouter provider."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[AsyncOpenAI] = None
        self._api_key = config.openrouter_api_key
        self._model = config.openrouter_model
    
    @property
    def is_configured(self) -> bool:
        """Check if OpenRouter is properly configured."""
        return bool(
            self._api_key
            and "YOUR_OPENROUTER_API_KEY_HERE" not in (self._api_key or "")
            and len(self._api_key or "") > 10
        )
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "OpenRouter"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client for OpenRouter."""
        if not self.is_configured:
            raise AIProcessorError("OpenRouter API key not configured or invalid")
        
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self._api_key,
            )
        
        return self._client
    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Execute a prompt using OpenRouter."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("OpenRouter API key not configured or invalid")
        
        try:
            client = self._get_client()
            
            messages = []
            if system_message and system_message.strip():
                self._logger.debug(f"Using system message: '{system_message}'")
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": user_prompt})
            
            self._logger.info(
                f"Sending prompt to OpenRouter model '{self._model}'. "
                f"System message: {'Yes' if system_message else 'No'}. "
                f"Prompt preview: '{user_prompt[:100]}...'"
            )
            
            completion = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_headers=OPENROUTER_HEADERS
            )
            
            response_text = completion.choices[0].message.content.strip()
            self._logger.info(
                f"OpenRouter model '{self._model}' responded successfully"
            )
            return response_text
        
        except Exception as e:
            self._logger.error(
                f"Error calling OpenRouter API with model '{self._model}': {e}",
                exc_info=True
            )
            raise AIProcessorError(f"Could not get response from OpenRouter: {e}")
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text using OpenRouter."""
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
        
        return await self.execute_prompt(prompt, temperature=0.3)
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "summary"
    ) -> str:
        """Analyze messages using OpenRouter."""
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
        
        return await self.execute_prompt(prompt, max_tokens=2000, temperature=0.5)
    
    async def close(self) -> None:
        """Clean up OpenRouter client."""
        self._client = None