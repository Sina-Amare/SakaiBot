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
from ...utils.validators import InputValidator, validate_image_model, validate_image_prompt
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
                "❌ فرمت دستور نامعتبر است.\n"
                "استفاده: `/image=flux/<prompt>` یا `/image=sdxl/<prompt>`\n"
                "مثال: `/image=flux/a beautiful sunset`",
                reply_to=message.id,
                parse_mode='md'
            )
            return
        
        model = parsed["model"]
        prompt = parsed["prompt"]
        
        # Validate model
        if not validate_image_model(model):
            await client.send_message(
                chat_id,
                f"❌ مدل نامعتبر: {model}\n"
                f"مدل‌های مجاز: {', '.join(SUPPORTED_IMAGE_MODELS)}",
                reply_to=message.id
            )
            return
        
        # Validate prompt
        try:
            prompt = validate_image_prompt(prompt)
        except ValueError as e:
            await client.send_message(
                chat_id,
                f"❌ خطا در prompt: {str(e)}",
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
                f"⚠️ محدودیت استفاده\n\n"
                f"شما به حد مجاز درخواست رسیده‌اید.\n"
                f"لطفاً {rate_limiter._window_seconds} ثانیه صبر کنید.\n"
                f"درخواست‌های باقیمانده: {remaining}"
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
        status_text = f"🎨 در حال پردازش درخواست تصویر با {model.upper()}..."
        if queue_position and queue_position > 1:
            status_text += f"\n⏳ در صف {model.upper()}: موقعیت {queue_position}"
        
        thinking_msg = await client.send_message(
            chat_id,
            status_text,
            reply_to=reply_to_id
        )
        
        try:
            # Wait for our turn in the queue
            while True:
                current_request = image_queue.get_request(request_id)
                if not current_request:
                    await client.edit_message(thinking_msg, "❌ درخواست یافت نشد")
                    return
                
                if current_request.status == ImageStatus.PROCESSING:
                    break
                elif current_request.status == ImageStatus.FAILED:
                    await client.edit_message(
                        thinking_msg,
                        f"❌ خطا: {current_request.error_message or 'خطای نامشخص'}"
                    )
                    return
                
                # Update queue position
                position = image_queue.get_queue_position(request_id, model)
                if position and position > 1:
                    await client.edit_message(
                        thinking_msg,
                        f"⏳ در صف {model.upper()}: موقعیت {position}..."
                    )
                
                await asyncio.sleep(2)  # Check every 2 seconds
            
            # Update status: enhancing prompt
            await client.edit_message(
                thinking_msg,
                f"🎨 در حال بهبود prompt با هوش مصنوعی..."
            )
            
            # Enhance prompt
            with TimingContext('image_command.enhancement_duration', tags={'model': model}):
                enhanced_prompt = await self._prompt_enhancer.enhance_prompt(prompt)
            
            # Update status: generating image
            await client.edit_message(
                thinking_msg,
                f"🖼️ در حال تولید تصویر با {model.upper()}..."
            )
            
            # Generate image
            with TimingContext('image_command.generation_duration', tags={'model': model}):
                if model == "flux":
                    success, image_path, error_message = await self._image_generator.generate_with_flux(enhanced_prompt)
                elif model == "sdxl":
                    success, image_path, error_message = await self._image_generator.generate_with_sdxl(enhanced_prompt)
                else:
                    success, image_path, error_message = (False, None, f"مدل نامعتبر: {model}")
            
            if success and image_path:
                # Mark as completed
                image_queue.mark_completed(request_id, image_path)
                
                # Update status: sending
                await client.edit_message(
                    thinking_msg,
                    f"📤 در حال ارسال تصویر..."
                )
                
                # Send image with enhanced prompt as caption
                caption = (
                    f"🎨 تصویر تولید شده با {model.upper()}\n\n"
                    f"**Prompt بهبود یافته:**\n{enhanced_prompt[:500]}{'...' if len(enhanced_prompt) > 500 else ''}"
                )
                
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
                    image_queue.cleanup_request(request_id)
                except Exception as e:
                    self._logger.warning(f"Failed to cleanup image file {image_path}: {e}")
                
                # Track success
                metrics.increment('image_command.success', tags={'model': model})
                self._logger.info(f"Image generation completed for request {request_id}")
            else:
                # Mark as failed
                image_queue.mark_failed(request_id, error_message or "خطای نامشخص")
                
                # Send error message
                error_msg = ErrorHandler.get_user_message(
                    AIProcessorError(error_message or "تولید تصویر ناموفق بود")
                )
                await client.edit_message(thinking_msg, error_msg)
                metrics.increment('image_command.errors', tags={'model': model, 'error': 'generation_failed'})
        
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
        
        # Parse: /image=flux/prompt or /image=sdxl/prompt
        parts = command_text[len("/image="):].strip()
        
        # Find the first slash to separate model and prompt
        if "/" not in parts:
            return None
        
        model_part, prompt_part = parts.split("/", 1)
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

