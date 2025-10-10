"""Group menu handlers for interactive CLI with REAL functionality."""

import asyncio
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import get_settings
from src.core.settings import SettingsManager
from src.utils.logging import get_logger

# Import REAL group command implementations
from src.cli.commands.group import (
    _list_groups, _set_target_group, _list_topics, _manage_mappings
)

console = Console()
logger = get_logger(__name__)

class GroupMenuHandler:
    """Handles group-related menu operations with REAL functionality."""
    
    def __init__(self, menu_state):
        self.state = menu_state
        self.config = get_settings()
        self.settings_manager = SettingsManager()
        
    async def list_groups(self):
        """List groups using REAL list function."""
        try:
            refresh = Prompt.ask("Refresh from Telegram?", choices=["y", "n"], default="n")
            show_all = Prompt.ask("Show all groups (not just admin)?", choices=["y", "n"], default="n")
            
            # Use the REAL list groups function
            await _list_groups(refresh=(refresh == "y"), show_all=(show_all == "y"))
            
        except Exception as e:
            logger.error(f"Error listing groups: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def set_target_group(self):
        """Set target group using REAL set function."""
        try:
            console.print("[cyan]Set Target Group[/cyan]\n")
            console.print("Options:")
            console.print("  [1] Select from list")
            console.print("  [2] Enter group name/ID")
            console.print("  [3] Clear target group")
            console.print("  [0] Cancel")
            
            choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"], default="0")
            
            if choice == "1":
                # Interactive selection (no identifier)
                await _set_target_group(None, clear=False)
            elif choice == "2":
                identifier = Prompt.ask("Enter group name or ID")
                if identifier.strip():
                    await _set_target_group(identifier, clear=False)
            elif choice == "3":
                await _set_target_group(None, clear=True)
                
        except Exception as e:
            logger.error(f"Error setting target group: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def list_topics(self):
        """List forum topics using REAL list topics function."""
        try:
            # Use the REAL list topics function
            await _list_topics()
            
        except Exception as e:
            logger.error(f"Error listing topics: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def manage_command_mappings(self):
        """Manage command mappings using REAL manage mappings function."""
        try:
            while True:
                console.clear()
                console.print("[bold cyan]Command Mappings[/bold cyan]\n")
                
                # Show current mappings first
                await _manage_mappings('list')
                
                console.print("\n[cyan]Options:[/cyan]")
                console.print("  [1] Add new mapping")
                console.print("  [2] Remove mapping")
                console.print("  [3] Clear all mappings")
                console.print("  [0] Back")
                
                choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"], default="0")
                
                if choice == "1":
                    await _manage_mappings('add')
                    input("\nPress Enter to continue...")
                elif choice == "2":
                    await _manage_mappings('remove')
                    input("\nPress Enter to continue...")
                elif choice == "3":
                    await _manage_mappings('clear')
                    input("\nPress Enter to continue...")
                elif choice == "0":
                    break
                    
        except Exception as e:
            logger.error(f"Error managing mappings: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            input("\nPress Enter to continue...")
        
    async def quick_setup_wizard(self):
        """Quick setup wizard for group configuration."""
        try:
            console.print("[bold magenta]🚀 Quick Setup Wizard[/bold magenta]\n")
            console.print("This wizard will help you set up group categorization.\n")
            
            # Step 1: List and select target group
            console.print("[yellow]Step 1:[/yellow] Select target group")
            refresh = Prompt.ask("Refresh group list from Telegram?", choices=["y", "n"], default="y")
            
            if refresh == "y":
                console.print("[dim]Refreshing groups...[/dim]")
                await _list_groups(refresh=True, show_all=False)
            
            console.print("\nNow select your target group:")
            await _set_target_group(None, clear=False)
            
            # Step 2: Check if forum and set up mappings
            settings = self.settings_manager.load_user_settings()
            if settings.get('selected_target_group'):
                console.print("\n[yellow]Step 2:[/yellow] Set up command mappings")
                
                # Check if it's a forum
                from src.utils.cache import CacheManager
                cache_manager = CacheManager()
                groups, _ = cache_manager.load_group_cache()
                
                selected_group = None
                if groups and isinstance(groups, list):
                    for group in groups:
                        if group and isinstance(group, dict) and group.get('id') == settings['selected_target_group']:
                            selected_group = group
                            break
                
                if selected_group and selected_group.get('is_forum'):
                    console.print(f"[green]'{selected_group['title']}' is a forum group![/green]")
                    console.print("You can map commands to specific topics.\n")
                    
                    add_mappings = Prompt.ask("Would you like to add command mappings now?", 
                                             choices=["y", "n"], default="y")
                    if add_mappings == "y":
                        await _manage_mappings('add')
                else:
                    console.print("[yellow]Selected group is not a forum.[/yellow]")
                    console.print("Commands will be sent to the main group chat.")
                
                console.print("\n[green]✓ Setup complete![/green]")
                console.print("You can now start monitoring for commands.")
            else:
                console.print("[yellow]No target group selected. Setup incomplete.[/yellow]")
                
        except Exception as e:
            logger.error(f"Error in setup wizard: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")