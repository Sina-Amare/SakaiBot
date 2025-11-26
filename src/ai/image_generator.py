"""Image generation service for Flux and SDXL Cloudflare Workers."""

import asyncio
import httpx
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

from ..core.config import get_settings
from ..core.constants import (
    IMAGE_GENERATION_TIMEOUT,
    IMAGE_GENERATION_CONNECT_TIMEOUT,
    IMAGE_TEMP_DIR
)
from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger
from ..utils.retry import retry_with_backoff


class ImageGenerator:
    """Handles image generation via Cloudflare Workers (Flux and SDXL)."""
    
    def __init__(self):
        """Initialize ImageGenerator with configuration."""
        self._logger = get_logger(self.__class__.__name__)
        self._config = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create httpx AsyncClient."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=IMAGE_GENERATION_CONNECT_TIMEOUT,
                    read=IMAGE_GENERATION_TIMEOUT
                ),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                follow_redirects=True
            )
            self._logger.info("Initialized httpx client for image generation")
        return self._http_client
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _save_image(self, response_content: bytes, model_name: str) -> str:
        """
        Save image to temporary file.
        
        Args:
            response_content: Image bytes
            model_name: Model name (flux or sdxl)
            
        Returns:
            Path to saved image file
            
        Raises:
            AIProcessorError: If file I/O fails
        """
        # Create temp directory if it doesn't exist
        temp_dir = Path(IMAGE_TEMP_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        request_id = str(uuid.uuid4())[:8]
        timestamp = int(asyncio.get_event_loop().time())
        filename = f"image_{model_name}_{request_id}_{timestamp}.png"
        filepath = temp_dir / filename
        
        try:
            # Write image bytes to file
            with open(filepath, 'wb') as f:
                f.write(response_content)
            
            self._logger.info(f"Saved image to {filepath} ({len(response_content)} bytes)")
            return str(filepath)
        except Exception as e:
            self._logger.error(f"Failed to save image: {e}")
            raise AIProcessorError(f"Failed to save image: {e}")
    
    async def _make_flux_request(self, prompt: str) -> httpx.Response:
        """
        Make GET request to Flux worker.
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            HTTP response
            
        Raises:
            AIProcessorError: If request fails
        """
        client = self._get_http_client()
        url = f"{self._config.flux_worker_url}?prompt={quote(prompt)}"
        
        try:
            self._logger.info(f"Making Flux request: {url[:100]}...")
            response = await client.get(url)
            return response
        except httpx.TimeoutException as e:
            self._logger.error(f"Flux request timeout: {e}")
            raise AIProcessorError("Image generation request timed out")
        except httpx.RequestError as e:
            self._logger.error(f"Flux request error: {e}")
            raise AIProcessorError(f"Network error during image generation: {e}")
    
    async def _make_sdxl_request(self, prompt: str) -> httpx.Response:
        """
        Make POST request to SDXL worker with Bearer auth.
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            HTTP response
            
        Raises:
            AIProcessorError: If request fails or auth is invalid
        """
        if not self._config.sdxl_api_key:
            raise AIProcessorError("SDXL API key not configured")
        
        client = self._get_http_client()
        url = self._config.sdxl_worker_url
        headers = {
            "Authorization": f"Bearer {self._config.sdxl_api_key}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}
        
        try:
            self._logger.info(f"Making SDXL request to {url}")
            response = await client.post(url, json=payload, headers=headers)
            return response
        except httpx.TimeoutException as e:
            self._logger.error(f"SDXL request timeout: {e}")
            raise AIProcessorError("Image generation request timed out")
        except httpx.RequestError as e:
            self._logger.error(f"SDXL request error: {e}")
            raise AIProcessorError(f"Network error during image generation: {e}")
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def generate_with_flux(self, enhanced_prompt: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate image using Flux worker.
        
        Args:
            enhanced_prompt: Enhanced prompt for image generation
            
        Returns:
            Tuple of (success, image_path, error_message)
        """
        try:
            response = await self._make_flux_request(enhanced_prompt)
            
            # Handle HTTP errors
            if response.status_code == 429:
                return (False, None, "Rate limit exceeded. Please try again later.")
            elif response.status_code == 400:
                return (False, None, "Invalid prompt or request format.")
            elif response.status_code >= 500:
                return (False, None, "Image generation service error. Please try again later.")
            elif response.status_code != 200:
                return (False, None, f"Image generation failed with status {response.status_code}")
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                self._logger.warning(f"Unexpected content type: {content_type}")
                # Try to parse as JSON error
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Unknown error")
                    return (False, None, f"Image generation failed: {error_msg}")
                except:
                    return (False, None, "Invalid response from image generation service")
            
            # Save image
            image_path = self._save_image(response.content, "flux")
            return (True, image_path, None)
            
        except AIProcessorError as e:
            return (False, None, str(e))
        except Exception as e:
            self._logger.error(f"Unexpected error in Flux generation: {e}", exc_info=True)
            return (False, None, f"Unexpected error: {e}")
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def generate_with_sdxl(self, enhanced_prompt: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate image using SDXL worker.
        
        Args:
            enhanced_prompt: Enhanced prompt for image generation
            
        Returns:
            Tuple of (success, image_path, error_message)
        """
        try:
            response = await self._make_sdxl_request(enhanced_prompt)
            
            # Handle HTTP errors
            if response.status_code == 401:
                return (False, None, "SDXL API key invalid or missing")
            elif response.status_code == 405:
                return (False, None, "Invalid request method")
            elif response.status_code == 400:
                # Try to parse error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Invalid prompt or request format")
                    return (False, None, f"Invalid request: {error_msg}")
                except:
                    return (False, None, "Invalid prompt or request format")
            elif response.status_code == 429:
                return (False, None, "Rate limit exceeded. Please try again later.")
            elif response.status_code >= 500:
                # Try to parse error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Image generation service error")
                    details = error_data.get("details", "")
                    if details:
                        return (False, None, f"Service error: {error_msg} - {details}")
                    return (False, None, f"Service error: {error_msg}")
                except:
                    return (False, None, "Image generation service error. Please try again later.")
            elif response.status_code != 200:
                return (False, None, f"Image generation failed with status {response.status_code}")
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                self._logger.warning(f"Unexpected content type: {content_type}")
                # Try to parse as JSON error
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Unknown error")
                    return (False, None, f"Image generation failed: {error_msg}")
                except:
                    return (False, None, "Invalid response from image generation service")
            
            # Save image
            image_path = self._save_image(response.content, "sdxl")
            return (True, image_path, None)
            
        except AIProcessorError as e:
            return (False, None, str(e))
        except Exception as e:
            self._logger.error(f"Unexpected error in SDXL generation: {e}", exc_info=True)
            return (False, None, f"Unexpected error: {e}")

