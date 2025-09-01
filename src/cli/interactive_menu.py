"""Interactive CLI menu for SakaiBot.

This module provides the interactive menu interface that runs alongside the bot.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from ..core.config import Settings
from ..telegram.client import SakaiBotTelegramClient
from ..utils.cache import CacheManager
# from .state import StateManager  # Will use simple dict instead

logger = logging.getLogger(__name__)
console = Console()


class InteractiveCLI:
    """Interactive CLI menu for bot control and configuration."""
    
    def __init__(self, client: SakaiBotTelegramClient, settings: Settings):
        """Initialize the interactive CLI.
        
        Args:
            client: Telegram client instance
            settings: Application settings
        """
        self.client = client
        self.settings = settings
        self.state = {}  # Simple dict for state management
        self.cache = CacheManager(
            Path(settings.paths.cache_dir),
            default_ttl=3600
        )
        self.running = True
        
    async def async_input(self, prompt: str) -> str:
        """Get user input asynchronously.
        
        Args:
            prompt: Prompt to display
            
        Returns:
            User input string
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, input, prompt)
    
    async def get_choice(self, prompt: str = "Enter your choice: ", expect_int: bool = True) -> Any:
        """Get user choice with validation.
        
        Args:
            prompt: Prompt to display
            expect_int: Whether to expect integer input
            
        Returns:
            User choice (int or str)
        """
        while True:
            try:
                choice_str = await self.async_input(prompt)
                if not choice_str.strip() and expect_int:
                    console.print("[yellow]Input cannot be empty. Please enter a number.[/yellow]")
                    continue
                if expect_int:
                    return int(choice_str)
                return choice_str.strip()
            except ValueError:
                if expect_int:
                    console.print(f"[red]Invalid input '{choice_str}'. Please enter a number.[/red]")
            except Exception as e:
                logger.error(f"Error getting user input: {e}")
                return -1 if expect_int else ""
    
    def display_main_menu(self) -> None:
        """Display the main menu."""
        console.clear()
        
        # Create status panel
        status_items = []
        
        # Default PV status
        pv_context = self.state.get("selected_pv_for_categorization")
        if pv_context:
            pv_name = pv_context.get('display_name', 'Unknown')
            status_items.append(f"[cyan]Default PV:[/cyan] {pv_name}")
        else:
            status_items.append("[cyan]Default PV:[/cyan] None (uses current chat)")
        
        # Target group status
        target_group = self.state.get("selected_target_group")
        if target_group:
            group_type = "Forum" if target_group.get('is_forum') else "Regular"
            group_name = target_group.get('title', 'Unknown')
            status_items.append(f"[cyan]Target Group:[/cyan] {group_name} ({group_type})")
        else:
            status_items.append("[cyan]Target Group:[/cyan] Not set")
        
        # Monitoring status
        is_monitoring = self.state.get("is_monitoring_active", False)
        monitoring_status = "[green]Active[/green]" if is_monitoring else "[red]Inactive[/red]"
        status_items.append(f"[cyan]Monitoring:[/cyan] {monitoring_status}")
        
        # Authorized PVs count
        authorized_pvs = self.state.get("directly_authorized_pvs", [])
        status_items.append(f"[cyan]Authorized PVs:[/cyan] {len(authorized_pvs)}")
        
        # Display status panel
        console.print(Panel(
            "\n".join(status_items),
            title="[bold cyan]SakaiBot Status[/bold cyan]",
            border_style="cyan"
        ))
        
        # Display menu options
        console.print("\n[bold yellow]═══ Main Menu ═══[/bold yellow]\n")
        
        console.print("[bold]Private Chat Management:[/bold]")
        console.print("  1. List Cached Private Chats")
        console.print("  2. Refresh PV List from Telegram")
        console.print("  3. Search PVs")
        console.print("  4. Set Default PV Context")
        
        console.print("\n[bold]Group & Categorization:[/bold]")
        console.print("  5. Set/Change Target Group")
        console.print("  6. Manage Command Mappings")
        console.print("  7. Manage Authorized PVs")
        
        console.print("\n[bold]Monitoring:[/bold]")
        monitoring_action = "Stop" if is_monitoring else "Start"
        console.print(f"  8. {monitoring_action} Global Monitoring")
        
        console.print("\n[bold]Settings:[/bold]")
        console.print("  9. Configure API Settings")
        console.print("  10. View Current Configuration")
        
        console.print("\n[bold yellow]0. Exit (Save Settings)[/bold yellow]")
        console.print("─" * 40)
    
    async def handle_list_pvs(self) -> None:
        """Handle listing cached private chats."""
        console.print("\n[cyan]Loading cached private chats...[/cyan]")
        
        try:
            pvs = await self.cache.get("pv_list", [])
            if not pvs:
                console.print("[yellow]No cached PVs found. Use option 2 to refresh from Telegram.[/yellow]")
                return
            
            # Create table
            table = Table(title="Cached Private Chats", show_lines=True)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Name", style="green")
            table.add_column("Username", style="yellow")
            table.add_column("ID", style="magenta")
            
            for idx, pv in enumerate(pvs[:20], 1):  # Show max 20
                name = pv.get('display_name', 'Unknown')
                username = pv.get('username', 'N/A')
                user_id = str(pv.get('id', 'N/A'))
                table.add_row(str(idx), name, username, user_id)
            
            console.print(table)
            
            if len(pvs) > 20:
                console.print(f"\n[yellow]Showing first 20 of {len(pvs)} total PVs[/yellow]")
                
        except Exception as e:
            logger.error(f"Error listing PVs: {e}")
            console.print(f"[red]Error loading PVs: {e}[/red]")
    
    async def handle_refresh_pvs(self) -> None:
        """Handle refreshing PV list from Telegram."""
        console.print("\n[cyan]Refreshing PV list from Telegram...[/cyan]")
        console.print("[yellow]This may take a moment...[/yellow]")
        
        try:
            # Get dialogs from Telegram
            dialogs = []
            async for dialog in self.client._client.iter_dialogs():
                if dialog.is_user and not dialog.entity.bot:
                    dialogs.append({
                        'id': dialog.entity.id,
                        'display_name': dialog.name or "Unknown",
                        'username': dialog.entity.username,
                        'phone': getattr(dialog.entity, 'phone', None)
                    })
                if len(dialogs) >= 100:  # Limit to 100 for performance
                    break
            
            # Save to cache
            await self.cache.set("pv_list", dialogs)
            console.print(f"[green]✓ Refreshed {len(dialogs)} private chats[/green]")
            
        except Exception as e:
            logger.error(f"Error refreshing PVs: {e}")
            console.print(f"[red]Error refreshing PVs: {e}[/red]")
    
    async def handle_exit(self) -> None:
        """Handle exit and save settings."""
        console.print("\n[cyan]Saving settings...[/cyan]")
        
        try:
            # Save state to file
            settings_data = {
                "selected_pv_for_categorization": self.state.get("selected_pv_for_categorization"),
                "selected_target_group": self.state.get("selected_target_group"),
                "active_command_to_topic_map": self.state.get("active_command_to_topic_map", {}),
                "directly_authorized_pvs": self.state.get("directly_authorized_pvs", []),
            }
            
            # Save to user settings file
            import json
            settings_file = Path("data/sakaibot_user_settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            console.print("[green]✓ Settings saved successfully[/green]")
            self.running = False
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            console.print(f"[red]Error saving settings: {e}[/red]")
            self.running = False
    
    async def run(self) -> None:
        """Run the interactive menu loop."""
        console.print("[green]Starting Interactive CLI...[/green]\n")
        
        # Load saved settings
        try:
            import json
            settings_file = Path("data/sakaibot_user_settings.json")
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    for key, value in saved_settings.items():
                        self.state[key] = value
                console.print("[green]✓ Loaded saved settings[/green]")
        except Exception as e:
            logger.warning(f"Could not load saved settings: {e}")
        
        while self.running:
            try:
                self.display_main_menu()
                choice = await self.get_choice()
                
                if choice == 0:
                    await self.handle_exit()
                elif choice == 1:
                    await self.handle_list_pvs()
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 2:
                    await self.handle_refresh_pvs()
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 3:
                    console.print("[yellow]Search PVs - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 4:
                    console.print("[yellow]Set Default PV Context - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 5:
                    console.print("[yellow]Set Target Group - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 6:
                    console.print("[yellow]Manage Command Mappings - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 7:
                    console.print("[yellow]Manage Authorized PVs - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 8:
                    is_monitoring = self.state.get("is_monitoring_active", False)
                    self.state["is_monitoring_active"] = not is_monitoring
                    status = "started" if not is_monitoring else "stopped"
                    console.print(f"[green]✓ Global monitoring {status}[/green]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 9:
                    console.print("[yellow]Configure API Settings - Implementation pending[/yellow]")
                    await self.async_input("\nPress Enter to continue...")
                elif choice == 10:
                    console.print(f"\n[cyan]Current Configuration:[/cyan]")
                    console.print(f"Telegram Session: {self.settings.telegram.session_name}")
                    console.print(f"OpenRouter Model: {self.settings.openrouter.model_name}")
                    console.print(f"Environment: {self.settings.environment}")
                    console.print(f"Debug Mode: {self.settings.debug}")
                    await self.async_input("\nPress Enter to continue...")
                else:
                    console.print("[red]Invalid option. Please try again.[/red]")
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Received interrupt signal...[/yellow]")
                await self.handle_exit()
            except Exception as e:
                logger.error(f"Error in menu loop: {e}")
                console.print(f"[red]Error: {e}[/red]")
                await asyncio.sleep(2)


async def start_interactive_cli(client: SakaiBotTelegramClient, settings: Settings) -> None:
    """Start the interactive CLI menu.
    
    Args:
        client: Telegram client instance
        settings: Application settings
    """
    cli = InteractiveCLI(client, settings)
    await cli.run()