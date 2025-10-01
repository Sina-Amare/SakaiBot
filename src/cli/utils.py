"""Utility functions for the modern CLI."""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint
import asyncio
from typing import Optional, List, Dict, Any

console = Console()

def setup_environment(debug: bool = False, config_file: Optional[str] = None):
    """Setup environment for CLI operations."""
    if debug:
        os.environ['DEBUG'] = '1'
    
    if config_file:
        os.environ['CONFIG_FILE'] = config_file

def display_banner():
    """Display SakaiBot banner."""
    banner_text = """
╔═══════════════════════════════════════╗
║          🤖 SakaiBot v2.0.0           ║
║   Advanced Telegram Userbot with AI   ║
╚═══════════════════════════════════════╝
    """
    console.print(Panel(banner_text, style="bold cyan", border_style="cyan"))

def display_error(message: str):
    """Display error message."""
    console.print(f"[red]✗ Error:[/red] {message}")

def display_success(message: str):
    """Display success message."""
    console.print(f"[green]✓ Success:[/green] {message}")

def display_warning(message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")

def display_info(message: str):
    """Display info message."""
    console.print(f"[blue]ℹ Info:[/blue] {message}")

async def get_telegram_client():
    """Get initialized Telegram client."""
    from src.core.config import load_config
    from src.telegram.client import TelegramClientManager
    
    try:
        config = load_config()
        client_manager = TelegramClientManager(config)
        client = await client_manager.initialize()
        return client, client_manager
    except Exception as e:
        display_error(f"Failed to initialize Telegram client: {e}")
        return None, None

async def get_cache_manager():
    """Get cache manager instance."""
    from src.utils.cache import CacheManager
    return CacheManager()

async def get_settings_manager():
    """Get settings manager instance."""
    from src.core.settings import SettingsManager
    return SettingsManager()

def format_pv_table(pvs: List[Dict[str, Any]]) -> Table:
    """Format PV list as a rich table."""
    from rich.table import Table
    
    table = Table(title="Private Chats", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=6)
    table.add_column("Display Name", style="cyan", width=30)
    table.add_column("Username", style="green", width=20)
    table.add_column("User ID", style="yellow", width=15)
    
    for idx, pv in enumerate(pvs, 1):
        display_name = pv.get('display_name', 'N/A')
        username = f"@{pv.get('username')}" if pv.get('username') else "N/A"
        user_id = str(pv.get('id', 'N/A'))
        
        table.add_row(str(idx), display_name, username, user_id)
    
    return table

def format_group_table(groups: List[Dict[str, Any]]) -> Table:
    """Format group list as a rich table."""
    from rich.table import Table
    
    table = Table(title="Groups", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=6)
    table.add_column("Group Title", style="cyan", width=30)
    table.add_column("Type", style="green", width=15)
    table.add_column("Group ID", style="yellow", width=20)
    
    for idx, group in enumerate(groups, 1):
        title = group.get('title', 'N/A')
        group_type = "Forum" if group.get('is_forum') else "Regular"
        group_id = str(group.get('id', 'N/A'))
        
        table.add_row(str(idx), title, group_type, group_id)
    
    return table

def confirm_action(message: str) -> bool:
    """Ask user for confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(message)

def prompt_choice(message: str, choices: List[str], default: Optional[str] = None) -> str:
    """Prompt user to select from choices."""
    from rich.prompt import Prompt
    
    # Display choices
    console.print(f"\n[bold]{message}[/bold]")
    for idx, choice in enumerate(choices, 1):
        console.print(f"  {idx}. {choice}")
    
    while True:
        selection = Prompt.ask("Enter your choice", default=default)
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            else:
                display_error(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            # Check if it's a direct match
            if selection in choices:
                return selection
            display_error("Invalid choice. Please enter a number or exact match.")

def prompt_text(message: str, default: Optional[str] = None) -> str:
    """Prompt user for text input."""
    from rich.prompt import Prompt
    return Prompt.ask(message, default=default)

def prompt_number(message: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Prompt user for number input."""
    from rich.prompt import IntPrompt
    
    while True:
        try:
            value = IntPrompt.ask(message)
            if min_val is not None and value < min_val:
                display_error(f"Value must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                display_error(f"Value must be at most {max_val}")
                continue
            return value
        except Exception:
            display_error("Please enter a valid number")

class ProgressSpinner:
    """Context manager for showing progress spinner."""
    
    def __init__(self, message: str):
        self.message = message
        self.spinner = None
        
    def __enter__(self):
        from rich.progress import Progress, SpinnerColumn, TextColumn
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        )
        self.progress.start()
        self.task = self.progress.add_task(self.message, total=None)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
        
    def update(self, message: str):
        """Update spinner message."""
        self.progress.update(self.task, description=message)