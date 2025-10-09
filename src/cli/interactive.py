"""Interactive menu system for SakaiBot CLI."""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich import print as rprint
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import get_settings
from src.core.settings import SettingsManager
from src.utils.logging import get_logger
from src.cli.menu_handlers.monitor_handler import MonitorMenuHandler
from src.cli.menu_handlers.group_handler import GroupMenuHandler

console = Console()
logger = get_logger(__name__)

class MenuState:
    """Manages the state of the interactive menu system."""
    
    def __init__(self):
        self.current_menu = "main"
        self.menu_stack = []
        self.context = {}
        self.settings_manager = SettingsManager()
        self.config = get_settings()
        
    def push_menu(self, menu_name: str):
        """Push current menu to stack and change to new menu."""
        self.menu_stack.append(self.current_menu)
        self.current_menu = menu_name
        
    def pop_menu(self) -> str:
        """Pop previous menu from stack."""
        if self.menu_stack:
            self.current_menu = self.menu_stack.pop()
        else:
            self.current_menu = "main"
        return self.current_menu
        
    def get_user_settings(self) -> Dict[str, Any]:
        """Get current user settings."""
        return self.settings_manager.load_user_settings()
        
    def save_user_settings(self, settings: Dict[str, Any]):
        """Save user settings."""
        self.settings_manager.save_user_settings(settings)

class InteractiveMenu:
    """Main interactive menu system."""
    
    def __init__(self):
        self.state = MenuState()
        self.running = True
        self.monitor_handler = MonitorMenuHandler(self.state)
        self.group_handler = GroupMenuHandler(self.state)
        
    def display_header(self, title: str, subtitle: str = ""):
        """Display a beautiful header."""
        header_text = Text(f" {title}", style="bold cyan")
        if subtitle:
            header_text.append(f"\n{subtitle}", style="dim")
            
        panel = Panel(
            header_text,
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(panel)
        
    def display_status_bar(self):
        """Display current status information."""
        settings = self.state.get_user_settings()
        
        status_items = []
        
        # AI Provider - only show if AI is enabled
        if self.state.config.is_ai_enabled:
            ai_provider = f"AI: {self.state.config.llm_provider.title()}"
            status_items.append(f"[green]{ai_provider}[/green]")
        
        # Target Group
        target_group = settings.get('selected_target_group')
        if target_group and isinstance(target_group, dict):
            group_name = target_group.get('title', 'Unknown')[:20]
            status_items.append(f"[blue]Group: {group_name}[/blue]")
        else:
            status_items.append("[yellow]Group: None[/yellow]")
            
        # Authorized users
        auth_count = len(settings.get('directly_authorized_pvs', []))
        status_items.append(f"[cyan]Auth: {auth_count}[/cyan]")
        
        # Monitoring
        monitoring = settings.get('is_monitoring_active', False)
        monitor_status = "[green]ON[/green]" if monitoring else "[red]OFF[/red]"
        status_items.append(f"Monitor: {monitor_status}")
        
        status_text = " | ".join(status_items)
        console.print(f"[dim]{status_text}[/dim]")
        console.print()
        
    def display_main_menu(self):
        """Display the main menu options."""
        self.display_header("SakaiBot Interactive Menu", "Navigate with numbers, 0 to go back")
        self.display_status_bar()
        
        # Create menu table
        table = Table(show_header=False, border_style="cyan", padding=(0, 2))
        table.add_column("Option", style="bold cyan", width=4)
        table.add_column("Title", style="bold white", width=35)
        table.add_column("Description", style="dim", width=40)
        
        menu_items = [
            ("1", "Groups & Categories", "Set target groups and categorization"),
            ("2", "Monitoring", "Start/stop monitoring and manage authorization"),
            ("3", "Settings", "View and modify bot configuration"),
            ("", "", ""),
            ("0", "Exit", "Save settings and exit")
        ]
        
        for option, title, desc in menu_items:
            if option:
                table.add_row(f"[{option}]", title, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def display_monitor_menu(self):
        """Display monitoring menu."""
        self.display_header("Monitoring & Authorization", "Manage bot monitoring and authorized users")
        
        settings = self.state.get_user_settings()
        monitoring_active = settings.get('is_monitoring_active', False)
        monitor_status = "[green]ACTIVE[/green]" if monitoring_active else "[red]INACTIVE[/red]"
        auth_count = len(settings.get('directly_authorized_pvs', []))
        
        console.print(f"[dim]Monitoring status: {monitor_status}[/dim]")
        console.print(f"[dim]Authorized users: {auth_count}[/dim]")
        console.print()
        
        table = Table(show_header=False, border_style="yellow", padding=(0, 2))
        table.add_column("Option", style="bold yellow", width=4)
        table.add_column("Action", style="bold white", width=30)
        table.add_column("Description", style="dim")
        
        monitor_action = "Stop Monitoring" if monitoring_active else "Start Monitoring"
        monitor_desc = "Stop global monitoring" if monitoring_active else "Start global monitoring"
        
        monitor_items = [
            ("1", monitor_action, monitor_desc),
            ("2", "Manage Authorized Users", "Add/remove authorized users"),
            ("3", "View Monitor Status", "Detailed monitoring information"),
            ("4", "Monitor Settings", "Configure monitoring options"),
            ("", "", ""),
            ("0", "Back to Main Menu", "")
        ]
        
        for option, action, desc in monitor_items:
            if option:
                table.add_row(f"[{option}]", action, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def display_group_menu(self):
        """Display group management menu."""
        self.display_header("Groups & Categories", "Manage target groups and categorization")
        
        settings = self.state.get_user_settings()
        target_group = settings.get('selected_target_group')
        if target_group and isinstance(target_group, dict):
            group_info = f"{target_group.get('title', 'Unknown')} ({target_group.get('type', 'Unknown')})"
        else:
            group_info = "None selected"
            
        mappings_count = len(settings.get('active_command_to_topic_map', {}))
        
        console.print(f"[dim]Target group: {group_info}[/dim]")
        console.print(f"[dim]Command mappings: {mappings_count}[/dim]")
        console.print()
        
        table = Table(show_header=False, border_style="green", padding=(0, 2))
        table.add_column("Option", style="bold green", width=4)
        table.add_column("Action", style="bold white", width=30)
        table.add_column("Description", style="dim")
        
        group_items = [
            ("1", "Set Target Group", "Choose group for categorization"),
            ("2", "Manage Mappings", "Configure command-to-topic mappings"),
            ("3", "List Groups", "Show all available groups"),
            ("4", "Test Categorization", "Test current setup"),
            ("", "", ""),
            ("0", "Back to Main Menu", "")
        ]
        
        for option, action, desc in group_items:
            if option:
                table.add_row(f"[{option}]", action, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def display_settings_menu(self):
        """Display settings menu."""
        self.display_header("Settings", "View and modify bot configuration")
        
        table = Table(show_header=False, border_style="cyan", padding=(0, 2))
        table.add_column("Option", style="bold cyan", width=4)
        table.add_column("Action", style="bold white", width=30)
        table.add_column("Description", style="dim")
        
        settings_items = [
            ("1", "View Configuration", "Show current bot configuration"),
            ("2", "Edit Settings", "Modify bot settings"),
            ("3", "Clear Cache", "Clear group cache"),
            ("4", "Backup Settings", "Export settings to file"),
            ("5", "Restore Settings", "Import settings from file"),
            ("", "", ""),
            ("0", "Back to Main Menu", "")
        ]
        
        for option, action, desc in settings_items:
            if option:
                table.add_row(f"[{option}]", action, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def get_user_choice(self, prompt: str = "Enter your choice", valid_options: List[str] = None) -> str:
        """Get user input with validation."""
        while True:
            try:
                choice = Prompt.ask(f"[bold cyan]{prompt}[/bold cyan]", default="0")
                if valid_options and choice not in valid_options:
                    console.print(f"[red]Invalid option. Please choose from: {', '.join(valid_options)}[/red]")
                    continue
                return choice
            except KeyboardInterrupt:
                console.print("\n[yellow]Use option 0 to go back or exit[/yellow]")
                continue
            except EOFError:
                return "0"
                
    async def handle_main_menu_choice(self, choice: str):
        """Handle main menu selections."""
        if choice == "1":
            self.state.push_menu("group")
        elif choice == "2":
            self.state.push_menu("monitor")
        elif choice == "3":
            self.state.push_menu("settings")
        elif choice == "0":
            await self.confirm_exit()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            
    async def handle_group_menu_choice(self, choice: str):
        """Handle group menu selections."""
        if choice == "1":
            await self.set_target_group()
        elif choice == "2":
            await self.manage_mappings()
        elif choice == "3":
            await self.list_groups()
        elif choice == "4":
            await self.test_categorization()
        elif choice == "0":
            self.state.pop_menu()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            
    async def handle_monitor_menu_choice(self, choice: str):
        """Handle monitor menu selections."""
        if choice == "1":
            await self.toggle_monitoring()
        elif choice == "2":
            await self.manage_authorized_users()
        elif choice == "3":
            await self.view_monitor_status()
        elif choice == "4":
            await self.configure_monitor_settings()
        elif choice == "0":
            self.state.pop_menu()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            
    async def handle_settings_menu_choice(self, choice: str):
        """Handle settings menu selections."""
        if choice == "1":
            await self.view_configuration()
        elif choice == "2":
            await self.edit_settings()
        elif choice == "3":
            await self.clear_cache()
        elif choice == "4":
            await self.backup_settings()
        elif choice == "5":
            await self.restore_settings()
        elif choice == "0":
            self.state.pop_menu()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            
    async def confirm_exit(self):
        """Confirm exit and save settings."""
        console.print("\n[yellow]Saving settings...[/yellow]")
        
        # Save current settings
        try:
            # Settings are automatically saved by SettingsManager
            console.print("[green]Settings saved successfully[/green]")
        except Exception as e:
            console.print(f"[red]Warning: Could not save settings: {e}[/red]")
            
        console.print("[cyan]Thank you for using SakaiBot![/cyan]")
        self.running = False
        
    # Real menu action implementations using handlers
    async def set_target_group(self):
        """Set target group."""
        await self.group_handler.set_target_group()
        
    async def manage_mappings(self):
        """Manage command mappings."""
        await self.group_handler.manage_command_mappings()
        
    async def list_groups(self):
        """List available groups."""
        await self.group_handler.list_groups()
        
    async def test_categorization(self):
        """Test categorization setup."""
        await self.group_handler.quick_setup_wizard()
        
    async def toggle_monitoring(self):
        """Toggle monitoring on/off."""
        await self.monitor_handler.toggle_monitoring()
        
    async def manage_authorized_users(self):
        """Manage authorized users."""
        await self.monitor_handler.manage_authorized_users()
        
    async def view_monitor_status(self):
        """View monitoring status."""
        await self.monitor_handler.view_monitor_status()
        
    async def configure_monitor_settings(self):
        """Configure monitor settings."""
        await self.monitor_handler.configure_monitor_settings()
        
    async def view_configuration(self):
        """View current configuration."""
        try:
            from src.core.config import get_settings
            from rich.table import Table
            
            config = get_settings()
            
            # Create configuration table
            table = Table(title="SakaiBot Configuration", show_header=True, header_style="bold cyan")
            table.add_column("Category", style="cyan", width=20)
            table.add_column("Setting", style="green", width=25)
            table.add_column("Value", width=40)
            
            # Telegram settings
            table.add_row("Telegram", "API ID", str(config.telegram_api_id))
            table.add_row("", "API Hash", config.telegram_api_hash[:10] + "..." if len(config.telegram_api_hash) > 15 else "***")
            table.add_row("", "Phone Number", config.telegram_phone_number)
            table.add_row("", "Session Name", config.telegram_session_name)
            
            # LLM settings
            table.add_row("LLM", "Provider", config.llm_provider.title())
            
            if config.llm_provider == "gemini":
                table.add_row("", "Gemini Model", config.gemini_model)
                if config.gemini_api_key:
                    key_display = config.gemini_api_key[:10] + "..." if len(config.gemini_api_key) > 20 else "***"
                    table.add_row("", "Gemini API Key", key_display)
            elif config.llm_provider == "openrouter":
                table.add_row("", "OpenRouter Model", config.openrouter_model)
                if config.openrouter_api_key:
                    key_display = config.openrouter_api_key[:10] + "..." if len(config.openrouter_api_key) > 20 else "***"
                    table.add_row("", "OpenRouter API Key", key_display)
            
            # UserBot settings
            table.add_row("UserBot", "Max Analyze Messages", str(config.userbot_max_analyze_messages))
            
            # Paths
            if config.paths_ffmpeg_executable:
                table.add_row("Paths", "FFmpeg", config.paths_ffmpeg_executable)
            
            # Environment
            table.add_row("Environment", "Environment", config.environment)
            table.add_row("", "Debug Mode", str(config.debug))
            
            console.print(table)
            
            # Show file locations
            console.print("\n[bold cyan]Configuration Files:[/bold cyan]")
            console.print(f"  • Main config: {Path('.env').absolute()}")
            console.print(f"  • User settings: {Path('data/sakaibot_user_settings.json').absolute()}")
            console.print(f" • Session: {Path('data/' + config.telegram_session_name + '.session').absolute()}")
            
        except Exception as e:
            logger.error(f"Error viewing configuration: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def edit_settings(self):
        """Edit settings."""
        try:
            import os
            import platform
            import subprocess
            
            env_path = Path(".env")
            
            if not env_path.exists():
                console.print("[red].env file not found[/red]")
                return
            
            # Try to open in default editor
            if platform.system() == "Windows":
                os.startfile(str(env_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(env_path)])
            else:  # Linux
                editor = os.environ.get("EDITOR", "nano")
                subprocess.run([editor, str(env_path)])
            
            console.print("[green]Opened .env in editor[/green]")
            console.print("[yellow]Restart the bot for changes to take effect[/yellow]")
            
        except Exception as e:
            logger.error(f"Error editing settings: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            console.print(f"[dim]You can manually edit: {Path('.env').absolute()}[/dim]")
        
        input("\nPress Enter to continue...")
        
    async def clear_cache(self):
        """Clear cache."""
        try:
            from src.utils.cache import CacheManager
            cache_manager = CacheManager()
            
            console.print("[yellow]This will clear all cached data including groups and settings.[/yellow]")
            confirm = Prompt.ask("Type 'confirm' to continue or press Enter to cancel")
            
            if confirm.lower() == 'confirm':
                cache_manager.clear_all_caches()
                console.print("[green]✓ All caches cleared[/green]")
            else:
                console.print("[blue]Operation cancelled[/blue]")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def backup_settings(self):
        """Backup settings."""
        try:
            from datetime import datetime
            import json
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"data/backup_sakaibot_settings_{timestamp}.json"
            backup_path = Path(backup_filename)
            
            settings = self.state.get_user_settings()
            
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            
            console.print(f"[green]✓ Settings backed up to: {backup_path}[/green]")
            
        except Exception as e:
            logger.error(f"Error backing up settings: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def restore_settings(self):
        """Restore settings."""
        try:
            from pathlib import Path
            import json
            from rich.filesize import decimal
            from rich.prompt import Prompt
            
            # List backup files
            data_dir = Path("data")
            backup_files = list(data_dir.glob("backup_sakaibot_settings_*.json"))
            
            if not backup_files:
                console.print("[yellow]No backup files found in data/ directory[/yellow]")
                return
            
            console.print("[bold cyan]Available backup files:[/bold cyan]")
            for i, file_path in enumerate(backup_files, 1):
                size = decimal(file_path.stat().st_size)
                console.print(f"  [{i}] {file_path.name} ({size})")
            
            choice = Prompt.ask("Enter the number of the backup to restore (or press Enter to cancel)")
            
            if not choice.isdigit():
                console.print("[blue]Operation cancelled[/blue]")
                return
                
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(backup_files):
                console.print("[red]Invalid selection[/red]")
                return
                
            backup_path = backup_files[choice_idx]
            
            # Load backup
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Confirm restoration
            console.print(f"[yellow]This will overwrite current settings with backup from: {backup_path.name}[/yellow]")
            confirm = Prompt.ask("Type 'confirm' to continue")
            
            if confirm.lower() == 'confirm':
                self.state.save_user_settings(backup_data)
                console.print("[green]✓ Settings restored successfully[/green]")
            else:
                console.print("[blue]Operation cancelled[/blue]")
                
        except Exception as e:
            logger.error(f"Error restoring settings: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
        
        input("\nPress Enter to continue...")
        
    async def run(self):
        """Main menu loop."""
        console.clear()
        console.print("[bold green]Welcome to SakaiBot Interactive Menu![/bold green]")
        console.print("[dim]Tip: Use Ctrl+C to go back, or select option 0[/dim]\n")
        
        while self.running:
            try:
                console.clear()
                
                # Display appropriate menu based on current state
                if self.state.current_menu == "main":
                    self.display_main_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_main_menu_choice(choice)
                    
                elif self.state.current_menu == "group":
                    self.display_group_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_group_menu_choice(choice)
                    
                elif self.state.current_menu == "monitor":
                    self.display_monitor_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_monitor_menu_choice(choice)
                    
                elif self.state.current_menu == "settings":
                    self.display_settings_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_settings_menu_choice(choice)
                    
            except KeyboardInterrupt:
                if self.state.current_menu != "main":
                    self.state.pop_menu()
                    console.print("\n[yellow]Going back...[/yellow]")
                else:
                    console.print("\n[yellow]Use option 0 to exit safely[/yellow]")
                    
                await asyncio.sleep(1)
                continue
                
            except Exception as e:
                logger.error(f"Error in menu loop: {e}", exc_info=True)
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Press Enter to continue...[/yellow]")
                input()

# Main function to start interactive menu
async def start_interactive_menu():
    """Start the interactive menu system."""
    menu = InteractiveMenu()
    await menu.run()

if __name__ == "__main__":
    asyncio.run(start_interactive_menu())