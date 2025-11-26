"""Image generation command handler."""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from ...ai.image_generator import ImageGenerator
from ...ai.image_queue import image_queue, ImageStatus
from ...ai.prompt_enhancer import PromptEnhancer
from ...ai.processor import AIProcessor
from ...core.constants import SUPPORTED_IMAGE_MODELS
from ...core.exceptions import AIProcessorError
from ...utils.helpers import clean_temp_files
from ...utils.logging import get_logger
from ...utils.message_sender import MessageSender
from ...utils.rate_limiter import get_ai_rate_limiter
from ...utils.validators import InputValidator
from ...utils.metrics import get_metrics_collector, TimingContext
from ...utils.error_handler import ErrorHandler
from .base import BaseHandler


class ImageHandler(BaseHandler):
    """Handles image generation commands (/image=flux/prompt, /image=sdxl/prompt)."""
    
    def __init__(
        self,
        ai_processor: AIProcessor,
        image_generator: ImageGenerator,
        prompt_enhancer: PromptEnhancer
    ):
        """
        Initialize Image handler.
        
        Args:
            ai_processor: AI processor instance
            image_generator: Image generator instance
            prompt_enhancer: Prompt enhancer instance
        """
        super().__init__()
        self._ai_processor = ai_processor
        self._image_generator = image_generator
        self._prompt_enhancer = prompt_enhancer
    
    async def handle_image_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """
        Handle image generation command.
        
        Args:
            message: Telegram message
            client: Telegram client
            chat_id: Chat ID
            sender_info: Sender information
        """
        # Parse command
        parsed = self._parse_image_command(message)
        if not parsed:
            await client.send_message(
                chat_id,
                "❌ Invalid command format.\n"
                "Usage: `/image=flux=<prompt>` or `/image=sdxl=<prompt>`\n"
                "Example: `/image=flux=a beautiful sunset`",
                reply_to=message.id,
                parse_mode='md'
            )
            return
        
        model = parsed["model"]
        prompt = parsed["prompt"]
        
        # Validate model
        if not InputValidator.validate_image_model(model):
            await client.send_message(
                chat_id,
                f"❌ Invalid model: {model}\n"
                f"Supported models: {', '.join(SUPPORTED_IMAGE_MODELS)}",
                reply_to=message.id
            )
            return
        
        # Validate prompt
        try:
            prompt = InputValidator.validate_image_prompt(prompt)
        except ValueError as e:
            await client.send_message(
                chat_id,
                f"❌ Prompt error: {str(e)}",
                reply_to=message.id
            )
            return
        
        # Check rate limit
        rate_limiter = get_ai_rate_limiter()
        user_id = message.sender_id
        if not await rate_limiter.check_rate_limit(user_id):
            remaining = await rate_limiter.get_remaining_requests(user_id)
            metrics = get_metrics_collector()
            metrics.increment('image_command.rate_limited', tags={'model': model})
            error_msg = (
                f"⚠️ Rate limit exceeded\n\n"
                f"You have reached the request limit.\n"
                f"Please wait {rate_limiter._window_seconds} seconds.\n"
                f"Remaining requests: {remaining}"
            )
            await client.send_message(chat_id, error_msg, reply_to=message.id)
            return
        
        # Create task for async processing
        from ...utils.task_manager import get_task_manager
        task_manager = get_task_manager()
        task_manager.create_task(
            self.process_image_command(message, client, chat_id, sender_info, model, prompt)
        )
    
    async def process_image_command(
        self,
        event_message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str,
        model: str,
        prompt: str
    ) -> None:
        """
        Process image generation command.
        
        Args:
            event_message: Telegram message
            client: Telegram client
            chat_id: Chat ID
            sender_info: Sender information
            model: Model name (flux or sdxl)
            prompt: User prompt
        """
        reply_to_id = event_message.id
        user_id = event_message.sender_id
        
        # Track metrics
        metrics = get_metrics_collector()
        metrics.increment('image_command.requests', tags={'model': model})
        
        # Add to queue
        request_id = image_queue.add_request(model, prompt, user_id)
        
        # Get queue position
        queue_position = image_queue.get_queue_position(request_id, model)
        
        # Send initial status message
        status_text = f"🎨 Processing image request with {model.upper()}..."
        if queue_position and queue_position > 1:
            status_text += f"\n⏳ In {model.upper()} queue: position {queue_position}"
        
        thinking_msg = await client.send_message(
            chat_id,
            status_text,
            reply_to=reply_to_id
        )
        
        try:
            # Wait for our turn and process when ready
            while True:
                current_request = image_queue.get_request(request_id)
                if not current_request:
                    await client.edit_message(thinking_msg, "❌ Request not found")
                    return
                
                # Check if it's our turn to process
                if image_queue.try_start_processing(request_id, model):
                    # It's our turn! Process it
                    break
                
                # Check status
                if current_request.status == ImageStatus.FAILED:
                    await client.edit_message(
                        thinking_msg,
                        f"❌ Error: {current_request.error_message or 'Unknown error'}"
                    )
                    return
                elif current_request.status == ImageStatus.COMPLETED:
                    # Request was completed (shouldn't happen, but handle it)
                    if current_request.image_path:
                        await self._send_image(
                            client, chat_id, reply_to_id, thinking_msg,
                            current_request.image_path, model, prompt
                        )
                    return
                
                # Update queue position
                position = image_queue.get_queue_position(request_id, model)
                if position and position > 1:
                    await client.edit_message(
                        thinking_msg,
                        f"⏳ In {model.upper()} queue: position {position}..."
                    )
                
                await asyncio.sleep(2)  # Check every 2 seconds
            
            # Process the request now that it's our turn
            await self._process_single_request(
                request_id, client, chat_id, reply_to_id, thinking_msg, model, prompt
            )
        
        except Exception as e:
            # Mark as failed
            image_queue.mark_failed(request_id, str(e))
            
            # Log and send error
            metrics.increment('image_command.errors', tags={'model': model, 'error_type': type(e).__name__})
            ErrorHandler.log_error(e, context=f"Image generation {model}")
            user_message = ErrorHandler.get_user_message(e)
            try:
                await client.edit_message(thinking_msg, user_message)
            except Exception:
                try:
                    await client.send_message(chat_id, user_message, reply_to=reply_to_id)
                except Exception:
                    pass
    
    def _parse_image_command(self, message: Message) -> Optional[Dict[str, Any]]:
        """
        Parse image generation command.
        
        Args:
            message: Telegram message
            
        Returns:
            Dict with 'model' and 'prompt' or None if invalid
        """
        if not message.text:
            return None
        
        command_text = message.text.strip()
        
        # Check if it's an image command
        if not command_text.lower().startswith("/image="):
            return None
        
        # Parse: /image=flux=prompt or /image=sdxl=prompt
        parts = command_text[len("/image="):].strip()
        
        # Find the second equals sign to separate model and prompt
        if "=" not in parts:
            return None
        
        model_part, prompt_part = parts.split("=", 1)
        model = model_part.strip().lower()
        prompt = prompt_part.strip()
        
        if not model or not prompt:
            return None
        
        # Validate model
        if model not in SUPPORTED_IMAGE_MODELS:
            return None
        
        return {
            "model": model,
            "prompt": prompt
        }
    
    async def _process_single_request(
        self,
        request_id: str,
        client: TelegramClient,
        chat_id: int,
        reply_to_id: int,
        thinking_msg: Message,
        model: str,
        prompt: str
    ):
        """
        Process a single image generation request.
        
        Args:
            request_id: Request ID
            client: Telegram client
            chat_id: Chat ID
            reply_to_id: Message ID to reply to
            thinking_msg: Status message to update
            model: Model name
            prompt: Original prompt
        """
        metrics = get_metrics_collector()
        
        try:
            # Update status: enhancing prompt
            await client.edit_message(
                thinking_msg,
                f"🎨 Enhancing prompt with AI..."
            )
            
            # Enhance prompt
            with TimingContext('image_command.enhancement_duration', tags={'model': model}):
                enhanced_prompt = await self._prompt_enhancer.enhance_prompt(prompt)
            
            # Update status: generating image
            await client.edit_message(
                thinking_msg,
                f"🖼️ Generating image with {model.upper()}..."
            )
            
            # Generate image
            with TimingContext('image_command.generation_duration', tags={'model': model}):
                if model == "flux":
                    success, image_path, error_message = await self._image_generator.generate_with_flux(enhanced_prompt)
                elif model == "sdxl":
                    success, image_path, error_message = await self._image_generator.generate_with_sdxl(enhanced_prompt)
                else:
                    success, image_path, error_message = (False, None, f"Invalid model: {model}")
            
            if success and image_path:
                # Mark as completed
                image_queue.mark_completed(request_id, image_path)
                
                # Send image
                await self._send_image(
                    client, chat_id, reply_to_id, thinking_msg,
                    image_path, model, enhanced_prompt
                )
                
                # Track success
                metrics.increment('image_command.success', tags={'model': model})
                self._logger.info(f"Image generation completed for request {request_id}")
            else:
                # Mark as failed
                image_queue.mark_failed(request_id, error_message or "Unknown error")
                
                # Send error message
                error_msg = ErrorHandler.get_user_message(
                    AIProcessorError(error_message or "Image generation failed")
                )
                await client.edit_message(thinking_msg, error_msg)
                metrics.increment('image_command.errors', tags={'model': model, 'error': 'generation_failed'})
        except Exception as e:
            image_queue.mark_failed(request_id, str(e))
            raise
    
    async def _send_image(
        self,
        client: TelegramClient,
        chat_id: int,
        reply_to_id: int,
        thinking_msg: Message,
        image_path: str,
        model: str,
        enhanced_prompt: str
    ):
        """
        Send generated image to Telegram.
        
        Args:
            client: Telegram client
            chat_id: Chat ID
            reply_to_id: Message ID to reply to
            thinking_msg: Status message to delete
            image_path: Path to image file
            model: Model name
            enhanced_prompt: Enhanced prompt for caption
        """
        # Update status: sending
        await client.edit_message(
            thinking_msg,
            f"📤 Sending image..."
        )
        
        # Send image with enhanced prompt as caption
        # Telegram photo caption limit is 1024 characters
        # Use full prompt, only truncate if it exceeds Telegram's limit
        header = f"🎨 Image generated with {model.upper()}\n\n**Enhanced prompt:**\n"
        max_caption_length = 1024
        max_prompt_length = max_caption_length - len(header)
        
        if len(enhanced_prompt) > max_prompt_length:
            # Only truncate if it exceeds Telegram's limit
            truncated_prompt = enhanced_prompt[:max_prompt_length - 3] + "..."
            self._logger.warning(f"Enhanced prompt truncated for caption (original: {len(enhanced_prompt)} chars)")
        else:
            truncated_prompt = enhanced_prompt
        
        caption = f"{header}{truncated_prompt}"
        
        await client.send_file(
            chat_id,
            image_path,
            caption=caption,
            reply_to=reply_to_id,
            parse_mode='md'
        )
        
        # Delete status message
        await thinking_msg.delete()
        
        # Clean up temp file
        try:
            Path(image_path).unlink(missing_ok=True)
        except Exception as e:
            self._logger.warning(f"Failed to cleanup image file {image_path}: {e}")

