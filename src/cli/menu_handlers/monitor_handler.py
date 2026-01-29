"""Monitor menu handlers for interactive CLI with REAL functionality."""

import asyncio
from rich.console import Console
# from rich.prompt import Prompt
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import get_settings
from src.core.settings import SettingsManager
from src.utils.logging import get_logger

# Import REAL monitor command implementations
from src.cli.commands.monitor import _start_monitoring, _show_monitoring_status
# from src.cli.commands.auth import _list_authorized, _add_authorized, _remove_authorized

console = Console()
logger = get_logger(__name__)

class MonitorMenuHandler:
    """Handles monitoring menu operations with REAL functionality."""
    
    def __init__(self, menu_state):
        self.state = menu_state
        self.config = get_settings()
        self.settings_manager = SettingsManager()
        
    async def toggle_monitoring(self):
        """Toggle monitoring on/off using REAL functions."""
        try:
            settings = self.settings_manager.load_user_settings()
            is_active = settings.get('is_monitoring_active', False)
            
            if is_active:
                console.print("[yellow]Monitoring is currently active.[/yellow]")
                console.print("[red]Note: Stop monitoring from command line with 'sakaibot monitor stop'[/red]")
                console.print("[dim]The interactive menu cannot stop an already running monitor process.[/dim]")
            else:
                console.print("[yellow]Starting monitoring...[/yellow]")
                await _start_monitoring(verbose=True)
                
        except Exception as e:
            logger.error(f"Error viewing status: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")

    async def manage_authorized_users(self):
        """Manage authorized users - Deprecated in CLI."""
        console.clear()
        console.print("[bold cyan]Manage Authorized Users[/bold cyan]\n")
        console.print("[yellow]This feature has been moved to Telegram commands.[/yellow]")
        console.print("Please use the following commands in Telegram:")
        console.print("  • /auth list - List authorized users")
        console.print("  • /auth add @username - Add authorized user")
        console.print("  • /auth remove @username - Remove authorized user")
        
        input("\nPress Enter to continue...")

    async def view_monitor_status(self):
        """View monitoring status using REAL function."""
        try:
            # Use the REAL show monitoring status function
            await _show_monitoring_status()
        except Exception as e:
            logger.error(f"Error viewing status: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def configure_monitor_settings(self):
        """Configure monitor settings."""
        try:
            from src.cli.utils import normalize_selected_group
            
            settings = self.settings_manager.load_user_settings()
            
            console.print("[bold cyan]Monitor Settings[/bold cyan]\n")
            
            # Show current settings
            console.print(f"[cyan]Current Settings:[/cyan]")
            console.print(f"  Monitoring Active: {settings.get('is_monitoring_active', False)}")
            console.print(f"  Authorized Users: {len(settings.get('directly_authorized_pvs', []))}")
            
            # Handle both old format (int) and new format (dict) for selected_target_group
            target_group = normalize_selected_group(settings.get('selected_target_group'))
            if target_group:
                target_title = target_group.get('title', f"Group {target_group.get('id')}")
            else:
                target_title = 'None'
            console.print(f"  Target Group: {target_title}")
            
            console.print("\n[yellow]To modify settings:[/yellow]")
            console.print("  • Use 'Manage Authorized Users' to add/remove users")
            console.print("  • Use 'Groups' menu to set target group")
            console.print("  • Use 'Start/Stop Monitoring' to toggle monitoring")
            
        except Exception as e:
            logger.error(f"Error configuring settings: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")