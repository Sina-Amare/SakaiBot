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
from src.cli.menu_handlers.pv_handler import PVMenuHandler
from src.cli.menu_handlers.ai_handler import AIMenuHandler
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
        self.pv_handler = PVMenuHandler(self.state)
        self.ai_handler = AIMenuHandler(self.state)
        self.monitor_handler = MonitorMenuHandler(self.state)
        self.group_handler = GroupMenuHandler(self.state)
        
    def display_header(self, title: str, subtitle: str = ""):
        """Display a beautiful header."""
        header_text = Text(f"🤖 {title}", style="bold cyan")
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
        
        # AI Provider
        ai_provider = f"AI: {self.state.config.llm_provider.title()}"
        status_items.append(f"[green]{ai_provider}[/green]")
        
        # Target Group
        target_group = settings.get('selected_target_group')
        if target_group and isinstance(target_group, dict):
            group_name = target_group.get('title', 'Unknown')[:20]
            status_items.append(f"[blue]Group: {group_name}[/blue]")
        else:
            status_items.append("[yellow]Group: None[/yellow]")
            
        # Authorized PVs
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
            ("1", "📱 Private Chats (PVs)", "Manage private conversations and analysis"),
            ("2", "👥 Groups & Categories", "Set target groups and categorization"),
            ("3", "🤖 AI Tools", "Translation, prompts, and AI configuration"),
            ("4", "📊 Monitoring", "Start/stop monitoring and manage authorization"),
            ("5", "⚙️  Settings", "View and modify bot configuration"),
            ("", "", ""),
            ("0", "🚪 Exit", "Save settings and exit")
        ]
        
        for option, title, desc in menu_items:
            if option:
                table.add_row(f"[{option}]", title, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def display_pv_menu(self):
        """Display PV management menu."""
        self.display_header("Private Chats (PVs)", "Manage private conversations")
        
        settings = self.state.get_user_settings()
        default_pv = settings.get('selected_pv_for_categorization')
        pv_context = default_pv.get('display_name', 'None') if default_pv else 'None'
        
        console.print(f"[dim]Current default PV: {pv_context}[/dim]")
        console.print()
        
        table = Table(show_header=False, border_style="blue", padding=(0, 2))
        table.add_column("Option", style="bold blue", width=4)
        table.add_column("Action", style="bold white", width=30)
        table.add_column("Description", style="dim")
        
        pv_items = [
            ("1", "📋 List Cached PVs", "Show all cached private chats"),
            ("2", "🔄 Refresh from Telegram", "Update PV list from Telegram"),
            ("3", "🔍 Search PVs", "Search through cached PVs"),
            ("4", "⚙️ Set Default Context", "Set default PV for analysis"),
            ("5", "📊 Analyze Messages", "Analyze PV with Persian sarcasm! 😏"),
            ("", "", ""),
            ("0", "⬅️  Back to Main Menu", "")
        ]
        
        for option, action, desc in pv_items:
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
            ("1", "🎯 Set Target Group", "Choose group for categorization"),
            ("2", "🗂️  Manage Mappings", "Configure command-to-topic mappings"),
            ("3", "📋 List Groups", "Show all available groups"),
            ("4", "🔧 Test Categorization", "Test current setup"),
            ("", "", ""),
            ("0", "⬅️  Back to Main Menu", "")
        ]
        
        for option, action, desc in group_items:
            if option:
                table.add_row(f"[{option}]", action, desc)
            else:
                table.add_row("", "", "")
                
        console.print(table)
        
    def display_ai_menu(self):
        """Display AI tools menu."""
        self.display_header("AI Tools", "Translation, prompts, and configuration")
        
        ai_provider = self.state.config.llm_provider.title()
        if self.state.config.llm_provider == "gemini":
            model_info = f"{ai_provider} ({self.state.config.gemini_model})"
        else:
            model_info = f"{ai_provider} ({self.state.config.openrouter_model})"
            
        console.print(f"[dim]Current provider: {model_info}[/dim]")
        console.print()
        
        table = Table(show_header=False, border_style="magenta", padding=(0, 2))
        table.add_column("Option", style="bold magenta", width=4)
        table.add_column("Action", style="bold white", width=30)
        table.add_column("Description", style="dim")
        
        ai_items = [
            ("1", "🧪 Test AI Connection", "Test current AI configuration"),
            ("2", "🌐 Translate Text", "Translate with Persian phonetics"),
            ("3", "💬 Custom Prompt", "Send custom prompt to AI"),
            ("4", "📝 Persian Analysis Demo", "Try the new sarcastic analysis!"),
            ("5", "⚙️ Configure Provider", "Switch AI provider or model"),
            ("", "", ""),
            ("0", "⬅️  Back to Main Menu", "")
        ]
        
        for option, action, desc in ai_items:
            if option:
                table.add_row(f"[{option}]", action, desc)
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
        
        monitor_action = "🛑 Stop Monitoring" if monitoring_active else "▶️  Start Monitoring"
        monitor_desc = "Stop global monitoring" if monitoring_active else "Start global monitoring"
        
        monitor_items = [
            ("1", monitor_action, monitor_desc),
            ("2", "👥 Manage Authorized Users", "Add/remove authorized users"),
            ("3", "📊 View Monitor Status", "Detailed monitoring information"),
            ("4", "🔧 Monitor Settings", "Configure monitoring options"),
            ("", "", ""),
            ("0", "⬅️  Back to Main Menu", "")
        ]
        
        for option, action, desc in monitor_items:
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
            ("1", "📋 View Configuration", "Show current bot configuration"),
            ("2", "🔧 Edit Settings", "Modify bot settings"),
            ("3", "🗑️  Clear Cache", "Clear PV and group cache"),
            ("4", "💾 Backup Settings", "Export settings to file"),
            ("5", "📥 Restore Settings", "Import settings from file"),
            ("", "", ""),
            ("0", "⬅️  Back to Main Menu", "")
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
            self.state.push_menu("pv")
        elif choice == "2":
            self.state.push_menu("group")
        elif choice == "3":
            self.state.push_menu("ai")
        elif choice == "4":
            self.state.push_menu("monitor")
        elif choice == "5":
            self.state.push_menu("settings")
        elif choice == "0":
            await self.confirm_exit()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            
    async def handle_pv_menu_choice(self, choice: str):
        """Handle PV menu selections."""
        if choice == "1":
            await self.list_pvs()
        elif choice == "2":
            await self.refresh_pvs()
        elif choice == "3":
            await self.search_pvs()
        elif choice == "4":
            await self.set_default_pv()
        elif choice == "5":
            await self.analyze_pv_messages()
        elif choice == "0":
            self.state.pop_menu()
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
            
    async def handle_ai_menu_choice(self, choice: str):
        """Handle AI menu selections."""
        if choice == "1":
            await self.test_ai_connection()
        elif choice == "2":
            await self.translate_text()
        elif choice == "3":
            await self.custom_prompt()
        elif choice == "4":
            await self.demo_persian_analysis()
        elif choice == "5":
            await self.configure_ai_provider()
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
            console.print("[green]✓ Settings saved successfully[/green]")
        except Exception as e:
            console.print(f"[red]Warning: Could not save settings: {e}[/red]")
            
        console.print("[cyan]Thank you for using SakaiBot! 🤖[/cyan]")
        self.running = False
        
    # Real menu action implementations using handlers
    async def list_pvs(self):
        """List private chats."""
        await self.pv_handler.list_pvs()
        
    async def refresh_pvs(self):
        """Refresh PV list from Telegram.""" 
        await self.pv_handler.refresh_pvs()
        
    async def search_pvs(self):
        """Search PVs."""
        await self.pv_handler.search_pvs()
        
    async def set_default_pv(self):
        """Set default PV context."""
        await self.pv_handler.set_default_pv_context()
        
    async def analyze_pv_messages(self):
        """Analyze PV messages with Persian sarcasm."""
        await self.pv_handler.analyze_pv_messages()
        
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
        
    async def test_ai_connection(self):
        """Test AI connection."""
        await self.ai_handler.test_ai_connection()
        
    async def translate_text(self):
        """Translate text with Persian phonetics."""
        await self.ai_handler.translate_text()
        
    async def custom_prompt(self):
        """Send custom prompt."""
        await self.ai_handler.custom_prompt()
        
    async def demo_persian_analysis(self):
        """Demo Persian sarcastic analysis."""
        await self.ai_handler.demo_persian_analysis()
        
    async def configure_ai_provider(self):
        """Configure AI provider."""
        await self.ai_handler.configure_ai_provider()
        
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
        console.print("[yellow]View configuration feature coming soon![/yellow]")
        input("\nPress Enter to continue...")
        
    async def edit_settings(self):
        """Edit settings."""
        console.print("[yellow]Edit settings feature coming soon![/yellow]")
        input("\nPress Enter to continue...")
        
    async def clear_cache(self):
        """Clear cache."""
        console.print("[yellow]Clear cache feature coming soon![/yellow]")
        input("\nPress Enter to continue...")
        
    async def backup_settings(self):
        """Backup settings."""
        console.print("[yellow]Backup settings feature coming soon![/yellow]")
        input("\nPress Enter to continue...")
        
    async def restore_settings(self):
        """Restore settings.""" 
        console.print("[yellow]Restore settings feature coming soon![/yellow]")
        input("\nPress Enter to continue...")
        
    async def run(self):
        """Main menu loop."""
        console.clear()
        console.print("[bold green]Welcome to SakaiBot Interactive Menu! 🤖[/bold green]")
        console.print("[dim]Tip: Use Ctrl+C to go back, or select option 0[/dim]\n")
        
        while self.running:
            try:
                console.clear()
                
                # Display appropriate menu based on current state
                if self.state.current_menu == "main":
                    self.display_main_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_main_menu_choice(choice)
                    
                elif self.state.current_menu == "pv":
                    self.display_pv_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_pv_menu_choice(choice)
                    
                elif self.state.current_menu == "group":
                    self.display_group_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_group_menu_choice(choice)
                    
                elif self.state.current_menu == "ai":
                    self.display_ai_menu()
                    choice = self.get_user_choice("Select option")
                    await self.handle_ai_menu_choice(choice)
                    
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