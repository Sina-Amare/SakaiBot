"""TTS Queue System for handling multiple TTS requests from Telegram replies."""

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .tts import TextToSpeechProcessor
from ..utils.logging import get_logger


class TTSStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TTSRequest:
    """Represents a TTS request from Telegram."""
    request_id: str
    text: str
    chat_id: int
    message_id: int
    voice: Optional[str] = None
    status: TTSStatus = TTSStatus.PENDING
    audio_file: Optional[str] = None
    error_message: Optional[str] = None


class TTSQueue:
    """Manages TTS requests with async queue processing."""
    
    def __init__(self):
        self._queue: asyncio.Queue[TTSRequest] = asyncio.Queue()
        self._requests: Dict[str, TTSRequest] = {}
        self._processor = TextToSpeechProcessor()
        self._logger = get_logger(self.__class__.__name__)
        self._is_processing = False
        self._max_concurrent = 1  # Process one at a time to avoid API rate limits
        
    async def add_request(
        self, 
        text: str, 
        chat_id: int, 
        message_id: int, 
        voice: Optional[str] = None
    ) -> str:
        """Add a TTS request to the queue."""
        request_id = f"tts_{uuid.uuid4().hex}"
        request = TTSRequest(
            request_id=request_id,
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            voice=voice
        )
        
        self._requests[request_id] = request
        await self._queue.put(request)
        
        self._logger.info(f"Added TTS request {request_id} for chat {chat_id}, message {message_id}")
        
        # Start processing if not already running
        if not self._is_processing:
            asyncio.create_task(self._process_queue())
        
        return request_id
    
    async def _process_queue(self):
        """Process TTS requests from the queue."""
        if self._is_processing:
            return
            
        self._is_processing = True
        semaphore = asyncio.Semaphore(self._max_concurrent)
        
        try:
            while True:
                try:
                    request = await asyncio.wait_for(
                        self._queue.get(), 
                        timeout=1.0
                    )
                    
                    async with semaphore:
                        await self._process_single_request(request)
                        
                except asyncio.TimeoutError:
                    # Check if queue is empty and no more items are expected
                    if self._queue.empty():
                        break
                    continue
                except Exception as e:
                    self._logger.error(f"Error processing TTS queue: {e}", exc_info=True)
                    break
        finally:
            self._is_processing = False
    
    async def _process_single_request(self, request: TTSRequest):
        """Process a single TTS request."""
        request_id = request.request_id
        self._logger.info(f"Processing TTS request {request_id}")
        
        try:
            # Update status to processing
            request.status = TTSStatus.PROCESSING
            self._logger.info(f"Generating speech for request {request_id}")
            
            # Generate speech file
            audio_file = await self._processor.generate_speech_file(
                text=request.text,
                voice=request.voice
            )
            
            if audio_file and Path(audio_file).exists():
                request.status = TTSStatus.COMPLETED
                request.audio_file = audio_file
                self._logger.info(f"TTS request {request_id} completed successfully")
            else:
                request.status = TTSStatus.FAILED
                request.error_message = self._processor.last_error or "Failed to generate audio file"
                self._logger.error(f"TTS request {request_id} failed: {request.error_message}")
                
        except Exception as e:
            request.status = TTSStatus.FAILED
            request.error_message = str(e)
            self._logger.error(f"TTS request {request_id} failed with exception: {e}", exc_info=True)
    
    def get_request_status(self, request_id: str) -> Optional[TTSRequest]:
        """Get the status of a TTS request."""
        return self._requests.get(request_id)
    
    def get_completed_audio(self, request_id: str) -> Optional[str]:
        """Get the audio file path for a completed request."""
        request = self._requests.get(request_id)
        if request and request.status == TTSStatus.COMPLETED:
            return request.audio_file
        return None
    
    def cleanup_request(self, request_id: str):
        """Clean up a completed request and its audio file."""
        request = self._requests.get(request_id)
        if request and request.audio_file:
            try:
                audio_path = Path(request.audio_file)
                if audio_path.exists():
                    audio_path.unlink()
            except Exception as e:
                self._logger.error(f"Error cleaning up audio file {request.audio_file}: {e}")
        
        if request_id in self._requests:
            del self._requests[request_id]
    
    @property
    def queue_size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()
    
    @property
    def active_requests(self) -> int:
        """Get the number of active requests."""
        return len([req for req in self._requests.values() 
                   if req.status in [TTSStatus.PENDING, TTSStatus.PROCESSING]])


# Global TTS queue instance
tts_queue = TTSQueue()
