"""Script to apply all critical fixes to image generation implementation."""

import re
from pathlib import Path


def fix_image_handler():
    """Fix ImageHandler to handle prompt enhancer tuple return and pass model_used."""
    file_path = Path("src/telegram/handlers/image_handler.py")
    content = file_path.read_text()
    
    # Fix 1: Update enhance_prompt call to unpack tuple
    content = content.replace(
        "enhanced_prompt = await self._prompt_enhancer.enhance_prompt(prompt)",
        "enhanced_prompt, model_used = await self._prompt_enhancer.enhance_prompt(prompt)"
    )
    
    # Fix 2: Update _send_image signature
    content = content.replace(
        "image_path, model, enhanced_prompt\n                )",
        "image_path, model, enhanced_prompt, model_used\n                )"
    )
    
    # Fix 3: Update _send_image method signature
    old_sig = """    async def _send_image(
        self,
        client: TelegramClient,
        chat_id: int,
        reply_to_id: int,
        thinking_msg: Message,
        image_path: str,
        model: str,
        enhanced_prompt: str
    ):"""
    
    new_sig = """    async def _send_image(
        self,
        client: TelegramClient,
        chat_id: int,
        reply_to_id: int,
        thinking_msg: Message,
        image_path: str,
        model: str,
        enhanced_prompt: str,
        model_used: str
    ):"""
    
    content = content.replace(old_sig, new_sig)
    
    # Fix 4: Update docstring
    content = content.replace(
        """            image_path: Path to image file
            model: Model name
            enhanced_prompt: Enhanced prompt for caption
        \"\"\"""",
        """            image_path: Path to image file
            model: Model name
            enhanced_prompt: Enhanced prompt for caption
            model_used: Model used for enhancement (\"openrouter\", \"gemini\", or \"none\")
        \"\"\"""
    )
    
    # Fix 5: Update caption with model attribution
    old_caption = '''        header = f"🎨 Image generated with {model.upper()}\\n\\n**Enhanced prompt:**\\n"'''
    new_caption = '''        # Model enhancement attribution
        if model_used == "openrouter":
            enhancement_note = "✨ Enhanced by OpenRouter"
        elif model_used == "gemini":
            enhancement_note = "✨ Enhanced by Gemini"
        else:
            enhancement_note = "⚡ Original prompt (no enhancement)"
        
        header = f"🎨 Image generated with {model.upper()}\\n{enhancement_note}\\n\\n**Enhanced prompt:**\\n"'''
    
    content = content.replace(old_caption, new_caption)
    
    file_path.write_text(content)
    print("✅ Fixed ImageHandler")


def integrate_handler_into_main():
    """Integrate ImageHandler into main handlers.py"""
    file_path = Path("src/telegram/handlers.py")
    content = file_path.read_text()
    
    if "from .handlers.image_handler import ImageHandler" in content:
        print("⏭️  ImageHandler already integrated")
        return
    
    # Add import after other handler imports
    import_line = "from .handlers.tts_handler import TTSHandler"
    new_import = f"{import_line}\nfrom .handlers.image_handler import ImageHandler"
    content = content.replace(import_line, new_import)
    
    # Initialize handler in __init__
    init_pattern = r"(self\._categorization_handler = Cat.*?\n)"
    replacement = r"\1\n        # Image Handler\n        from ...ai.image_generator import ImageGenerator\n        from ...ai.prompt_enhancer import PromptEnhancer\n        self._image_handler = ImageHandler(\n            ai_processor=ai_processor,\n            image_generator=ImageGenerator(),\n            prompt_enhancer=PromptEnhancer(ai_processor)\n        )\n"
    content = re.sub(init_pattern, replacement, content)
    
    # Add route in process_command_logic
    route_pattern = r"(# Handle /stt or /tts.*?\n)"
    route_addition = r'''\1
        # Handle /image commands
        if command_text_lower.startswith("/image="):
            await self._image_handler.handle_image_command(
                message_to_process, client, current_chat_id_for_response, command_sender_info
            )
            if is_confirm_flow and your_confirm_message:
                await your_confirm_message.delete()
            return
'''
    content = re.sub(route_pattern, route_addition, content)
    
    file_path.write_text(content)
    print("✅ Integrated ImageHandler into handlers.py")


def add_config_validation():
    """Add URL validation to config.py"""
    file_path = Path("src/core/config.py")
    content = file_path.read_text()
    
    if "validate_worker_url" in content:
        print("⏭️  Config validation already added")
        return
    
    # Add import
    content = content.replace(
        "from pydantic import BaseModel, Field, field_validator",
        "from pydantic import BaseModel, Field, field_validator\nfrom urllib.parse import urlparse"
    )
    
    # Add validator method before last method
    validator_code = '''
    @field_validator("flux_worker_url", "sdxl_worker_url")
    @classmethod
    def validate_worker_url(cls, v: str) -> str:
        """Validate worker URL format."""
        if not v:
            return v
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid worker URL format: {v}")
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"Worker URL must use HTTP or HTTPS: {v}")
        return v
    
    @property
    def is_image_generation_enabled(self) -> bool:
        """Check if image generation is properly configured."""
        flux_ok = bool(self.flux_worker_url and self.flux_worker_url.startswith("http"))
        sdxl_ok = bool(
            self.sdxl_worker_url 
            and self.sdxl_worker_url.startswith("http")
            and self.sdxl_api_key
            and len(self.sdxl_api_key) > 10
        )
        return flux_ok or sdxl_ok
'''
    
    # Find the last method and insert before it
    content = content.replace(
        "\n    def get_env_vars",
        f"{validator_code}\n    def get_env_vars"
    )
    
    file_path.write_text(content)
    print("✅ Added config validation and helper property")


def add_cleanup_utility():
    """Add temp file cleanup utility"""
    file_path = Path("src/utils/helpers.py")
    
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text('')
    
    content = file_path.read_text()
    
    if "cleanup_old_temp_images" in content:
        print("⏭️  Cleanup utility already added")
        return
    
    cleanup_code = '''

import time
from pathlib import Path
from ..core.constants import IMAGE_TEMP_DIR
from .logging import get_logger

logger = get_logger(__name__)


def cleanup_old_temp_images(max_age_seconds: int = 3600):
    """
    Remove temp images older than max_age_seconds.
    
    Args:
        max_age_seconds: Maximum age in seconds (default: 1 hour)
    """
    try:
        temp_dir = Path(IMAGE_TEMP_DIR)
        if not temp_dir.exists():
            return
        
        now = time.time()
        removed_count = 0
        
        for file in temp_dir.glob("image_*.png"):
            try:
                if now - file.stat().st_mtime > max_age_seconds:
                    file.unlink()
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove old temp file {file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old temp image files")
    except Exception as e:
        logger.error(f"Error during temp image cleanup: {e}")
'''
    
    content += cleanup_code
    file_path.write_text(content)
    print("✅ Added cleanup utility")


def main():
    """Apply all fixes."""
    print("🔧 Applying all critical fixes...\n")
    
    try:
        fix_image_handler()
        integrate_handler_into_main()
        add_config_validation()
        add_cleanup_utility()
        
        print("\n✨ All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Update .env with API keys")
        print("2. Run tests")
        print("3. Test end-to-end")
        
    except Exception as e:
        print(f"\n❌ Error during fixes: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
