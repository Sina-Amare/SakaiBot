"""Utility functions for the modern CLI."""

import os
import sys
from pathlib import Path
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint
import asyncio
from typing import Optional, List, Dict, Any

console = Console()

# Global storage for shared client (set by SakaiBot.run())
_shared_client = None
_shared_client_manager = None


def set_shared_client(client, client_manager):
    """Set the shared Telegram client for use by CLI commands.
    
    This should be called by SakaiBot.run() after connecting to Telegram.
    """
    global _shared_client, _shared_client_manager
    _shared_client = client
    _shared_client_manager = client_manager


def get_shared_client():
    """Get the shared Telegram client if available.
    
    Returns:
        Tuple of (client, client_manager) or (None, None) if not set.
    """
    return _shared_client, _shared_client_manager


def clear_shared_client():
    """Clear the shared client reference (called on shutdown)."""
    global _shared_client, _shared_client_manager
    _shared_client = None
    _shared_client_manager = None


def setup_environment(debug: bool = False, config_file: Optional[str] = None):
    """Setup environment for CLI operations."""
    if debug:
        os.environ['DEBUG'] = '1'
    
    if config_file:
        os.environ['CONFIG_FILE'] = config_file

def display_banner():
    """Display SakaiBot banner."""
    if not sys.stdout.isatty():
        return
    banner_text = """
╔═══════════════════════════════════════╗
║            SakaiBot v2.0.0            ║
║   Advanced Telegram Userbot with AI   ║
╚═══════════════════════════════════════╝
    """
    console.print(Panel(banner_text, style="bold cyan", border_style="cyan"))

def display_error(message: str):
    """Display error message."""
    if not sys.stdout.isatty():
        print(f"Error: {message}")
        return
    console.print(f"[red]Error:[/red] {message}")

def display_success(message: str):
    """Display success message."""
    if not sys.stdout.isatty():
        print(f"Success: {message}")
        return
    console.print(f"[green]Success:[/green] {message}")

def display_warning(message: str):
    """Display warning message."""
    if not sys.stdout.isatty():
        print(f"Warning: {message}")
        return
    console.print(f"[yellow]Warning:[/yellow] {message}")

def display_info(message: str):
    """Display info message."""
    if not sys.stdout.isatty():
        print(f"Info: {message}")
        return
    console.print(f"[blue]Info:[/blue] {message}")

async def get_telegram_client():
    """Get initialized Telegram client.
    
    If running inside SakaiBot (interactive menu), returns the shared client.
    If running standalone, creates a new client connection.
    Returns (None, None) if bot is already running to prevent database lock.
    """
    # First, check if we have a shared client (running inside SakaiBot)
    shared_client, shared_manager = get_shared_client()
    if shared_client is not None:
        return shared_client, shared_manager
    
    from pathlib import Path
    from src.core.config import load_config
    from src.telegram.client import TelegramClientManager
    
    # Check if bot is already running (only matters for standalone CLI)
    lock_file = Path("data/.sakaibot.lock")
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            # Check if process is actually running
            import psutil
            if psutil.pid_exists(pid):
                display_error(
                    "Bot is currently running! Cannot use CLI for user management.\n"
                    "Use Telegram self-commands instead:\n"
                    "  • /auth list - View authorized users\n"
                    "  • /auth add @username - Add user\n"
                    "  • /auth remove @username - Remove user\n\n"
                    "Send these commands in any Telegram chat (even Saved Messages)."
                )
                return None, None
        except (ValueError, FileNotFoundError, ImportError):
            pass  # Lock file corrupted or psutil not available, proceed
    
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

def normalize_selected_group(
    raw_group: Any,
    groups_cache: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Normalize selected group data for consistent runtime usage.

    Args:
        raw_group: Value loaded from settings (can be dict, int, or None).
        groups_cache: Optional cached group list to enrich metadata.

    Returns:
        A dictionary containing at least an 'id' key or None if unavailable.
    """
    if raw_group is None:
        return None

    normalized: Dict[str, Any]

    if isinstance(raw_group, dict):
        group_id = raw_group.get('id')
        if group_id is None:
            return None
        normalized = dict(raw_group)
    else:
        try:
            group_id = int(raw_group)
        except (TypeError, ValueError):
            return None
        normalized = {'id': group_id}

    if groups_cache:
        for group in groups_cache:
            if not group or not isinstance(group, dict):
                continue
            if group.get('id') == normalized['id']:
                normalized.setdefault('title', group.get('title'))
                normalized.setdefault('is_forum', group.get('is_forum'))
                normalized.setdefault('username', group.get('username'))
                normalized.setdefault('type', 'Forum' if group.get('is_forum') else 'Regular')
                break

    normalized.setdefault('title', f"Group {normalized['id']}")
    if 'is_forum' in normalized:
        normalized['type'] = normalized.get('type') or ('Forum' if normalized.get('is_forum') else 'Regular')
    else:
        normalized.setdefault('type', 'Unknown')

    return normalized


def normalize_command_mappings(raw_mappings: Any) -> Dict[Any, List[str]]:
    """Normalize mapping data to the canonical topic_id -> [commands] structure.

    Args:
        raw_mappings: Value loaded from settings which may be None, a dict in legacy
            command -> topic format, or already in the new format.

    Returns:
        A dictionary keyed by topic identifier (None for main chat) with lists of
        command strings.
    """
    normalized: Dict[Any, List[str]] = {}
    has_invalid_keys = False

    def _normalize_topic_key(topic_key: Any) -> Optional[Any]:
        """Convert persisted topic identifiers back to their runtime form."""
        nonlocal has_invalid_keys
        if topic_key is None:
            return None
        if isinstance(topic_key, int):
            return topic_key
        if isinstance(topic_key, str):
            stripped = topic_key.strip()
            if not stripped:
                return None
            lowered = stripped.lower()
            if lowered in {"none", "null", "main", "main chat", "main group chat"}:
                return None
            try:
                return int(stripped)
            except ValueError:
                has_invalid_keys = True
                return None
        has_invalid_keys = True
        return None

    def _clean_command_list(commands: List[Any]) -> List[str]:
        """Return a deduplicated, lower-case list of commands."""
        cleaned_commands: List[str] = []
        seen: set[str] = set()
        for cmd in commands:
            if not isinstance(cmd, str):
                continue
            cleaned = cmd.strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            cleaned_commands.append(cleaned)
        return cleaned_commands

    if not raw_mappings or not isinstance(raw_mappings, dict):
        return normalized

    values = list(raw_mappings.values())

    # New format: topic_id -> list of commands (allowing None for topic_id).
    is_new_format = True
    if values:
        for v in values:
            if v is not None and not isinstance(v, list):
                is_new_format = False
                break
    
    if is_new_format:
        for topic_id, commands in raw_mappings.items():
            if not isinstance(commands, list):
                continue
            cleaned_commands = _clean_command_list(commands)
            normalized_topic = _normalize_topic_key(topic_id)
            if normalized_topic is None and topic_id not in (None, "None", "null"):
                # Skip invalid topics that we could not normalise.
                continue
            if cleaned_commands:
                normalized[normalized_topic] = cleaned_commands
        return normalized

    # Legacy format: command -> topic_id (int/None).
    is_legacy_format = True
    if values:
        for v in values:
            if v is not None and not isinstance(v, int):
                is_legacy_format = False
                break
    
    if is_legacy_format:
        for command, topic_id in raw_mappings.items():
            if not isinstance(command, str):
                continue
            cleaned_command = command.strip().lower()
            if not cleaned_command:
                continue
            normalized_topic = _normalize_topic_key(topic_id)
            if normalized_topic is None and topic_id not in (None, "None", "null"):
                continue
            normalized.setdefault(normalized_topic, [])
            if cleaned_command not in normalized[normalized_topic]:
                normalized[normalized_topic].append(cleaned_command)
        return normalized

    # Mixed/unknown formats: best effort sanitisation.
    try:
        for key, value in raw_mappings.items():
            normalized_topic = _normalize_topic_key(key if isinstance(value, list) else value)
            if isinstance(value, list):
                cleaned_commands = _clean_command_list(value)
                if cleaned_commands and (normalized_topic is not None or key in (None, "None", "null")):
                    normalized[normalized_topic] = cleaned_commands
            elif isinstance(key, str):
                cleaned_command = key.strip().lower()
                if cleaned_command and (normalized_topic is not None or value in (None, "None", "null")):
                    normalized.setdefault(normalized_topic, []).append(cleaned_command)
    except TypeError:
        # Handle edge case where isinstance gets invalid arguments
        display_warning("Invalid mapping data detected, resetting mappings")
        return {}

    if has_invalid_keys:
        display_warning("Some topic mappings referenced invalid topic identifiers and were ignored.")

    return normalized


def prompt_choice(message: str, choices: List[str], default: Optional[str] = None) -> str:
    """Prompt user to select from choices."""
    from rich.prompt import Prompt
    
    if not choices:
        display_error("No choices available")
        return default if default else ""
    
    # Display choices with consistent numeric labels
    console.print(f"\n[bold]{message}[/bold]")
    for idx, choice in enumerate(choices, 1):
        console.print(f"  [bold]{idx}[/bold]. {choice}")
    
    while True:
        selection = Prompt.ask("Enter your choice (number or exact match)", default=default)
        
        if not selection:
            if default:
                return default
            else:
                display_error("Selection cannot be empty")
                continue
        
        try:
            # Try to parse as integer (numeric selection)
            idx = int(selection) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            else:
                display_error(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            # Check if it's a direct match to one of the choices
            for idx, choice in enumerate(choices):
                if selection.lower() == choice.lower():
                    return choice
            display_error(f"Invalid choice. Please enter a number (1-{len(choices)}) or exact match.")

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
