"""Image generation queue system with separate FIFO queues per model."""

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List

from ..utils.logging import get_logger
from ..core.constants import SUPPORTED_IMAGE_MODELS


class ImageStatus(Enum):
    """Status of an image generation request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ImageRequest:
    """Represents an image generation request."""
    request_id: str
    model: str  # "flux" or "sdxl"
    prompt: str
    user_id: int
    status: ImageStatus = ImageStatus.PENDING
    image_path: Optional[str] = None
    error_message: Optional[str] = None


class ImageQueue:
    """Manages image generation requests with separate FIFO queues per model."""
    
    def __init__(self):
        """Initialize ImageQueue with separate queues for each model."""
        self._logger = get_logger(self.__class__.__name__)
        
        # Separate queues for each model
        self._flux_queue: List[ImageRequest] = []
        self._sdxl_queue: List[ImageRequest] = []
        
        # Processing flags
        self._flux_processing = False
        self._sdxl_processing = False
        
        # Request storage by ID
        self._requests: Dict[str, ImageRequest] = {}
    
    def add_request(self, model: str, prompt: str, user_id: int) -> str:
        """
        Add a request to the appropriate model queue.
        
        Args:
            model: Model name ("flux" or "sdxl")
            prompt: Image generation prompt
            user_id: User ID making the request
            
        Returns:
            Request ID
        """
        if model not in SUPPORTED_IMAGE_MODELS:
            raise ValueError(f"Unsupported model: {model}")
        
        request_id = f"img_{uuid.uuid4().hex[:8]}"
        request = ImageRequest(
            request_id=request_id,
            model=model,
            prompt=prompt,
            user_id=user_id
        )
        
        self._requests[request_id] = request
        
        # Add to appropriate queue
        if model == "flux":
            self._flux_queue.append(request)
            self._logger.info(f"Added Flux request {request_id} to queue (position: {len(self._flux_queue)})")
        elif model == "sdxl":
            self._sdxl_queue.append(request)
            self._logger.info(f"Added SDXL request {request_id} to queue (position: {len(self._sdxl_queue)})")
        
        return request_id
    
    def get_queue_position(self, request_id: str, model: str) -> Optional[int]:
        """
        Get the position of a request in its model queue (1-based).
        
        Args:
            request_id: Request ID
            model: Model name
            
        Returns:
            Position in queue (1-based) or None if not pending
        """
        request = self._requests.get(request_id)
        if not request or request.model != model:
            return None
        
        if request.status != ImageStatus.PENDING:
            return None
        
        # Get appropriate queue
        queue = self._flux_queue if model == "flux" else self._sdxl_queue
        
        # Find position (1-based)
        position = 1
        for req in queue:
            if req.request_id == request_id:
                return position
            if req.status == ImageStatus.PENDING:
                position += 1
        
        return None
    
    def get_status(self, request_id: str) -> Optional[str]:
        """
        Get status of a request.
        
        Args:
            request_id: Request ID
            
        Returns:
            Status string or None if not found
        """
        request = self._requests.get(request_id)
        if not request:
            return None
        return request.status.value
    
    def process_next_flux(self) -> Optional[ImageRequest]:
        """
        Get next pending Flux request and mark as processing.
        
        Returns:
            Next Flux request or None if queue is empty or processing
        """
        if self._flux_processing:
            return None
        
        # Find first pending request
        for request in self._flux_queue:
            if request.status == ImageStatus.PENDING:
                request.status = ImageStatus.PROCESSING
                self._flux_processing = True
                self._logger.info(f"Processing Flux request {request.request_id}")
                return request
        
        return None
    
    def process_next_sdxl(self) -> Optional[ImageRequest]:
        """
        Get next pending SDXL request and mark as processing.
        
        Returns:
            Next SDXL request or None if queue is empty or processing
        """
        if self._sdxl_processing:
            return None
        
        # Find first pending request
        for request in self._sdxl_queue:
            if request.status == ImageStatus.PENDING:
                request.status = ImageStatus.PROCESSING
                self._sdxl_processing = True
                self._logger.info(f"Processing SDXL request {request.request_id}")
                return request
        
        return None
    
    def mark_completed(self, request_id: str, image_path: str):
        """
        Mark a request as completed.
        
        Args:
            request_id: Request ID
            image_path: Path to generated image
        """
        request = self._requests.get(request_id)
        if not request:
            return
        
        request.status = ImageStatus.COMPLETED
        request.image_path = image_path
        
        # Reset processing flag for the model
        if request.model == "flux":
            self._flux_processing = False
        elif request.model == "sdxl":
            self._sdxl_processing = False
        
        self._logger.info(f"Request {request_id} completed")
    
    def mark_failed(self, request_id: str, error_message: str):
        """
        Mark a request as failed.
        
        Args:
            request_id: Request ID
            error_message: Error message
        """
        request = self._requests.get(request_id)
        if not request:
            return
        
        request.status = ImageStatus.FAILED
        request.error_message = error_message
        
        # Reset processing flag for the model
        if request.model == "flux":
            self._flux_processing = False
        elif request.model == "sdxl":
            self._sdxl_processing = False
        
        self._logger.error(f"Request {request_id} failed: {error_message}")
    
    def is_flux_processing(self) -> bool:
        """Check if Flux queue is currently processing."""
        return self._flux_processing
    
    def is_sdxl_processing(self) -> bool:
        """Check if SDXL queue is currently processing."""
        return self._sdxl_processing
    
    def get_request(self, request_id: str) -> Optional[ImageRequest]:
        """Get request by ID."""
        return self._requests.get(request_id)
    
    def cleanup_request(self, request_id: str):
        """Remove a request from tracking (after image is sent)."""
        if request_id in self._requests:
            request = self._requests[request_id]
            # Remove from queue
            if request.model == "flux":
                if request in self._flux_queue:
                    self._flux_queue.remove(request)
            elif request.model == "sdxl":
                if request in self._sdxl_queue:
                    self._sdxl_queue.remove(request)
            del self._requests[request_id]
    
    def get_pending_count(self, model: Optional[str] = None) -> int:
        """
        Get number of pending requests.
        
        Args:
            model: Model name (None for total)
            
        Returns:
            Number of pending requests
        """
        if model:
            queue = self._flux_queue if model == "flux" else self._sdxl_queue
            return len([r for r in queue if r.status == ImageStatus.PENDING])
        else:
            return (
                len([r for r in self._flux_queue if r.status == ImageStatus.PENDING]) +
                len([r for r in self._sdxl_queue if r.status == ImageStatus.PENDING])
            )


# Global image queue instance
image_queue = ImageQueue()

