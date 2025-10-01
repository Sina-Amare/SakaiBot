"""AI menu handlers for interactive CLI with REAL functionality."""

import asyncio
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import get_settings
from src.utils.logging import get_logger

# Import REAL AI command implementations
from src.cli.commands.ai import (
    _test_ai, _show_ai_config, _translate_text, _send_prompt
)

console = Console()
logger = get_logger(__name__)

class AIMenuHandler:
    """Handles AI-related menu operations with REAL functionality."""
    
    def __init__(self, menu_state):
        self.state = menu_state
        self.config = get_settings()
        
    async def test_ai_connection(self):
        """Test AI connection using REAL test function."""
        try:
            console.print("[cyan]Testing AI connection...[/cyan]")
            # Use the REAL AI test function
            await _test_ai("Hello, please respond with 'AI is working!'")
        except Exception as e:
            logger.error(f"Error testing AI: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def translate_text(self):
        """Translate text with Persian phonetics using REAL function."""
        try:
            text = Prompt.ask("Enter text to translate")
            if not text.strip():
                return
                
            target_lang = Prompt.ask("Target language (e.g., fa for Persian, en for English)", default="fa")
            
            # Use the REAL translate function with source='auto' as default
            await _translate_text(text, target_lang, source='auto')
            
        except Exception as e:
            logger.error(f"Error translating: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def custom_prompt(self):
        """Send custom prompt using REAL function."""
        try:
            prompt = Prompt.ask("Enter your prompt")
            if not prompt.strip():
                return
                
            # Use the REAL send prompt function
            await _send_prompt(prompt, max_tokens=1500, temperature=0.7)
            
        except Exception as e:
            logger.error(f"Error with custom prompt: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def demo_persian_analysis(self):
        """Demo Persian sarcastic analysis."""
        try:
            console.print("[bold magenta]🎭 Persian Sarcastic Analysis Demo![/bold magenta]")
            console.print("\n[cyan]This feature analyzes conversations with wit and sarcasm:[/cyan]")
            console.print("[dim]Like The Office narrator meets Persian culture![/dim]\n")
            
            sample_prompt = (
                "تحلیل کن که چرا همه جلسات کاری در نهایت به بحث در مورد غذا ختم میشن. "
                "با لحن طنز و کنایه‌آمیز مثل راوی مستندهای مشاهده‌گرانه پاسخ بده."
            )
            
            console.print("[yellow]Sending demo prompt to AI...[/yellow]")
            await _send_prompt(sample_prompt, max_tokens=1500, temperature=0.7)
            
        except Exception as e:
            logger.error(f"Error with demo: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def configure_ai_provider(self):
        """Show AI configuration using REAL function."""
        try:
            # Use the REAL show config function
            await _show_ai_config()
            
            console.print("\n[yellow]To change AI provider:[/yellow]")
            console.print("Edit your .env file and set LLM_PROVIDER to 'gemini' or 'openrouter'")
            console.print("Then restart the bot.")
            
        except Exception as e:
            logger.error(f"Error showing config: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")