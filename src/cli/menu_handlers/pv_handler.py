"""PV menu handlers for interactive CLI."""

import asyncio
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import get_settings
from src.core.settings import SettingsManager
from src.utils.logging import get_logger

# Import REAL PV command implementations
from src.cli.commands.pv import (
    _list_pvs, _refresh_pvs, _search_pvs, 
    _set_context, _show_context
)

console = Console()
logger = get_logger(__name__)

class PVMenuHandler:
    """Handles PV-related menu operations."""
    
    def __init__(self, menu_state):
        self.state = menu_state
        self.config = get_settings()
        self.settings_manager = SettingsManager()
        
    async def list_pvs(self, limit: int = 50):
        """List private chats using REAL PV listing function."""
        try:
            # Use the REAL list PVs function from commands
            await _list_pvs(limit=limit, refresh=False)
        except Exception as e:
            logger.error(f"Error listing PVs: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def refresh_pvs(self):
        """Refresh PV list from Telegram using REAL refresh function."""
        try:
            # Use the REAL refresh PVs function
            await _refresh_pvs(fetch_limit=200)
        except Exception as e:
            logger.error(f"Error refreshing PVs: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            
        input("\nPress Enter to continue...")
        
    async def search_pvs(self):
        """Search through cached PVs using REAL search function."""
        try:
            search_term = Prompt.ask("Enter search term (name, username, or ID)")
            if search_term.strip():
                # Use the REAL search PVs function
                await _search_pvs(search_term, limit=10)
        except Exception as e:
            logger.error(f"Error searching PVs: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            
        input("\nPress Enter to continue...")
        
    async def pv_actions_menu(self, pv: Dict[str, Any]):
        """Show actions menu for a specific PV."""
        display_name = pv.get('display_name', 'Unknown')
        username = pv.get('username', 'N/A')
        user_id = pv.get('user_id', 'Unknown')
        
        panel = Panel(
            f"[bold cyan]{display_name}[/bold cyan]\n"
            f"Username: {username}\n"
            f"User ID: {user_id}",
            title="Selected PV",
            border_style="cyan"
        )
        console.print(panel)
        
        console.print("\n[cyan]Available Actions:[/cyan]")
        console.print("  [1] Set as default context PV")
        console.print("  [2] Analyze messages (Persian sarcasm! 😏)")
        console.print("  [3] Add to authorized users")
        console.print("  [0] Back to search results")
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3"], default="0")
        
        if choice == "1":
            await self.set_default_pv_context(pv)
        elif choice == "2":
            await self.analyze_pv_messages(pv)
        elif choice == "3":
            await self.add_to_authorized(pv)
            
    async def set_default_pv_context(self, pv: Dict[str, Any] = None):
        """Set default PV context using REAL set context function."""
        try:
            # First show current context
            await _show_context()
            console.print("\n[cyan]Set new default context:[/cyan]")
            identifier = Prompt.ask("Enter username, user ID, or display name (or press Enter to skip)")
            if identifier.strip():
                # Use the REAL set context function
                await _set_context(identifier, clear=False)
            else:
                console.print("[yellow]No changes made[/yellow]")
        except Exception as e:
            logger.error(f"Error setting default PV: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            
        input("\nPress Enter to continue...")
        
    async def analyze_pv_messages(self, pv: Dict[str, Any] = None):
        """Analyze PV messages with Persian sarcasm using AI."""
        try:
            # Import AI command for prompts
            from src.cli.commands.ai import _send_prompt
            
            console.print("[bold magenta]🎭 Persian Sarcastic Message Analysis[/bold magenta]")
            console.print("[dim]This will analyze conversations with wit and sarcasm![/dim]\n")
            
            # Create a sarcastic analysis prompt
            if pv:
                context = f"Analyzing messages from {pv.get('display_name', 'Unknown')}"
            else:
                context = "Analyzing recent messages"
                
            prompt = (
                f"{context}. "
                "تحلیل مکالمات با لحن طنز و کنایه‌آمیز مثل راوی The Office. "
                "نکات جالب، الگوهای رفتاری، و اتفاقات خنده‌دار رو با دید طنز بررسی کن. "
                "مثل یک ناظر بی‌طرف که همه چیز رو می‌بینه و با کنایه توضیح میده."
            )
            
            console.print(f"[yellow]Generating sarcastic analysis...[/yellow]")
            await _send_prompt(prompt, max_tokens=1500, temperature=0.8)
            
        except Exception as e:
            logger.error(f"Error analyzing messages: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def add_to_authorized(self, pv: Dict[str, Any]):
        """Add PV to authorized users list."""
        try:
            settings = self.settings_manager.load_user_settings()
            authorized_pvs = settings.get('directly_authorized_pvs', [])
            
            user_id = pv.get('user_id')
            if user_id in [auth_pv.get('user_id') for auth_pv in authorized_pvs]:
                console.print("[yellow]This user is already authorized.[/yellow]")
            else:
                authorized_pvs.append(pv)
                settings['directly_authorized_pvs'] = authorized_pvs
                self.settings_manager.save_user_settings(settings)
                
                display_name = pv.get('display_name', 'Unknown')
                console.print(f"[green]✓ Added '{display_name}' to authorized users[/green]")
                
        except Exception as e:
            logger.error(f"Error adding to authorized: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            
        input("\nPress Enter to continue...")