"""Rich-based interactive menu system for SakaiBot CLI.

This module provides a beautiful, user-friendly menu interface using Rich
for terminal formatting, tables, and interactive elements.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.rule import Rule
from rich.columns import Columns
from rich import box
from rich.align import Align

from .models import (
    CLIState, MenuOption, MenuAction, SelectionResult, 
    TableData, TableColumn, SearchCriteria
)
from .state import StateManager
from ..core.exceptions import CLIError, InputError
from ..core.constants import APP_NAME, APP_VERSION, EMOJI

logger = logging.getLogger(__name__)


class RichMenu:
    """Rich-based interactive menu system."""
    
    def __init__(self, state_manager: StateManager):
        """Initialize Rich menu.
        
        Args:
            state_manager: State manager instance
        """
        self.console = Console()
        self.state_manager = state_manager
        self._menu_options = self._create_menu_options()
    
    def _create_menu_options(self) -> List[MenuOption]:
        """Create menu options configuration.
        
        Returns:
            List[MenuOption]: Configured menu options
        """
        return [
            MenuOption(
                key="1",
                title="List All Cached Private Chats (PVs)",
                description="View all cached private conversations",
                action=MenuAction.LIST_PVS
            ),
            MenuOption(
                key="2",
                title="Refresh/Update PV List from Telegram",
                description="Fetch recent chats and update cache",
                action=MenuAction.REFRESH_PVS
            ),
            MenuOption(
                key="3",
                title="Search PVs (from cached list)",
                description="Search cached PVs by ID, username, or name",
                action=MenuAction.SEARCH_PVS
            ),
            MenuOption(
                key="4",
                title="Set Default PV Context (for /analyze)",
                description="Set default private chat for analysis commands",
                action=MenuAction.SET_DEFAULT_PV
            ),
            MenuOption(
                key="5",
                title="Set/Change Categorization Target Group",
                description="Select group for message categorization",
                action=MenuAction.SET_TARGET_GROUP
            ),
            MenuOption(
                key="6",
                title="Manage Categorization Command Mappings",
                description="Configure command-to-topic mappings",
                action=MenuAction.MANAGE_MAPPINGS,
                requires_setup=["target_group"]
            ),
            MenuOption(
                key="7",
                title="Toggle GLOBAL Monitoring",
                description="Start/stop monitoring for categorization & AI commands",
                action=MenuAction.TOGGLE_MONITORING
            ),
            MenuOption(
                key="8",
                title="Manage Directly Authorized PVs",
                description="Manage users authorized for direct commands",
                action=MenuAction.MANAGE_AUTHORIZED
            ),
            MenuOption(
                key="0",
                title="Exit (Save Settings)",
                description="Save current configuration and exit",
                action=MenuAction.EXIT
            )
        ]
    
    def display_header(self) -> None:
        """Display application header."""
        header_text = Text()
        header_text.append(f"{APP_NAME} ", style="bold blue")
        header_text.append(f"v{APP_VERSION}", style="dim")
        header_text.append(f" {EMOJI['robot']}", style="bold")
        
        panel = Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            style="blue"
        )
        self.console.print(panel)
    
    def display_main_menu(self) -> None:
        """Display the main menu with current state information."""
        state = self.state_manager.state
        
        # Create status information
        status_info = self._create_status_panel(state)
        
        # Create menu options table
        menu_table = self._create_menu_table(state)
        
        # Display everything
        self.console.print()
        self.console.print(status_info)
        self.console.print()
        self.console.print(menu_table)
        self.console.print()
    
    def _create_status_panel(self, state: CLIState) -> Panel:
        """Create status information panel.
        
        Args:
            state: Current CLI state
            
        Returns:
            Panel: Rich panel with status information
        """
        status_lines = []
        
        # PV Status
        pv_status = f"{EMOJI['info']} Default PV: {state.get_pv_display_name()}"
        status_lines.append(pv_status)
        
        # Group Status
        group_status = f"{EMOJI['folder']} {state.get_group_status_text()}"
        status_lines.append(group_status)
        
        # Authorization Status
        auth_count = len(state.directly_authorized_pvs)
        auth_status = f"{EMOJI['key']} Authorized Users: {auth_count}"
        status_lines.append(auth_status)
        
        # Monitoring Status
        monitoring_emoji = EMOJI['success'] if state.is_monitoring_active else EMOJI['warning']
        monitoring_text = "Active" if state.is_monitoring_active else "Inactive"
        monitoring_status = f"{monitoring_emoji} Monitoring: {monitoring_text}"
        status_lines.append(monitoring_status)
        
        status_text = "\n".join(status_lines)
        
        return Panel(
            status_text,
            title="Current Status",
            box=box.ROUNDED,
            style="dim"
        )
    
    def _create_menu_table(self, state: CLIState) -> Table:
        """Create menu options table.
        
        Args:
            state: Current CLI state
            
        Returns:
            Table: Rich table with menu options
        """
        table = Table(
            title="Menu Options",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Action", style="white", width=40)
        table.add_column("Status", width=20)
        
        # Group options by category
        categories = {
            "PV Management": ["1", "2", "3", "4"],
            "Group & Categorization": ["5", "6"],
            "Monitoring & Authorization": ["7", "8"],
            "System": ["0"]
        }
        
        for category, option_keys in categories.items():
            # Add category header
            table.add_row("", f"[bold]{category}[/bold]", "", style="dim")
            
            # Add options in category
            for option_key in option_keys:
                option = next((opt for opt in self._menu_options if opt.key == option_key), None)
                if not option:
                    continue
                
                # Determine status
                status_style = "green"
                status_text = "Available"
                
                if not option.is_available(state):
                    status_style = "yellow"
                    status_text = "Requires Setup"
                
                # Special status for monitoring
                if option.action == MenuAction.TOGGLE_MONITORING:
                    if state.is_monitoring_active:
                        status_text = "[red]Active[/red]"
                    else:
                        can_start, _ = state.can_start_monitoring()
                        status_text = "[green]Ready[/green]" if can_start else "[yellow]Not Ready[/yellow]"
                    status_style = ""
                
                table.add_row(
                    f"[cyan]{option.key}[/cyan]",
                    option.title,
                    f"[{status_style}]{status_text}[/{status_style}]" if status_style else status_text
                )
        
        return table
    
    async def get_user_choice(self, prompt: str = "Enter your choice", expect_int: bool = True) -> Any:
        """Get user input with Rich prompt.
        
        Args:
            prompt: Prompt text to display
            expect_int: Whether to expect integer input
            
        Returns:
            Any: User input (int or str)
            
        Raises:
            InputError: If input is invalid
        """
        try:
            if expect_int:
                choice = IntPrompt.ask(
                    f"[bold cyan]{prompt}[/bold cyan]",
                    console=self.console
                )
                return choice
            else:
                choice = Prompt.ask(
                    f"[bold cyan]{prompt}[/bold cyan]",
                    console=self.console
                )
                return choice.strip()
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            raise InputError("User cancelled input")
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            raise InputError(f"Input error: {e}")
    
    def display_entity_table(
        self,
        entities: List[Dict[str, Any]],
        title: str,
        entity_type: str = "PV",
        show_numbers: bool = True
    ) -> bool:
        """Display entities in a formatted table.
        
        Args:
            entities: List of entity dictionaries
            title: Table title
            entity_type: Type of entity (PV, Group, Topic)
            show_numbers: Whether to show row numbers
            
        Returns:
            bool: True if entities were displayed, False if empty
        """
        if not entities:
            self.console.print(f"\n[yellow]No {entity_type.lower()}s to display.[/yellow]")
            return False
        
        table = Table(
            title=title,
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        if show_numbers:
            table.add_column("No.", style="cyan", width=6)
        
        if entity_type == "PV":
            table.add_column("Display Name", style="white", width=30)
            table.add_column("Username", style="blue", width=20)
            table.add_column("User ID", style="dim", width=15)
            
            for idx, pv in enumerate(entities):
                row_data = []
                if show_numbers:
                    row_data.append(str(idx + 1))
                
                row_data.extend([
                    pv.get('display_name', 'N/A')[:29],
                    f"@{pv.get('username', 'N/A')[:19]}" if pv.get('username') else "N/A",
                    str(pv['id'])
                ])
                table.add_row(*row_data)
        
        elif entity_type == "Group":
            table.add_column("Group Title", style="white", width=35)
            table.add_column("Type", style="blue", width=15)
            table.add_column("Group ID", style="dim", width=15)
            
            for idx, group in enumerate(entities):
                row_data = []
                if show_numbers:
                    row_data.append(str(idx + 1))
                
                group_type = "Forum" if group.get('is_forum') else "Regular"
                row_data.extend([
                    group.get('title', 'N/A')[:34],
                    group_type,
                    str(group['id'])
                ])
                table.add_row(*row_data)
        
        elif entity_type == "Topic":
            table.add_column("Topic Title", style="white", width=50)
            table.add_column("Topic ID", style="dim", width=15)
            
            for idx, topic in enumerate(entities):
                row_data = []
                if show_numbers:
                    row_data.append(str(idx + 1))
                
                row_data.extend([
                    topic.get('title', 'N/A')[:49],
                    str(topic['id'])
                ])
                table.add_row(*row_data)
        
        self.console.print(table)
        return True
    
    def display_command_mappings(self, state: CLIState) -> None:
        """Display current command mappings.
        
        Args:
            state: Current CLI state
        """
        if not state.active_command_to_topic_map:
            self.console.print("\n[yellow]No command mappings currently defined.[/yellow]")
            return
        
        table = Table(
            title="Current Command Mappings",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Target", style="white", width=45)
        
        is_forum = state.selected_target_group and state.selected_target_group.get('is_forum', False)
        
        for command, topic_id in state.active_command_to_topic_map.items():
            target_description = "Main Group Chat"
            
            if topic_id is not None and is_forum:
                # Find topic title from cache
                topic_title = next(
                    (t['title'] for t in state.current_group_topics_cache if t['id'] == topic_id),
                    f"Unknown Topic (ID: {topic_id})"
                )
                target_description = f"Topic: '{topic_title}' (ID: {topic_id})"
            elif topic_id is not None:
                target_description = f"Target ID: {topic_id} (Warning: Non-forum with topic ID)"
            
            table.add_row(f"/{command}", target_description)
        
        self.console.print(table)
    
    def display_progress(
        self,
        description: str,
        total: Optional[int] = None
    ) -> Progress:
        """Create and display a progress bar.
        
        Args:
            description: Progress description
            total: Total steps (None for spinner)
            
        Returns:
            Progress: Rich progress instance
        """
        if total is None:
            # Spinner for indeterminate progress
            progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                console=self.console
            )
        else:
            # Progress bar for determinate progress
            progress = Progress(
                TextColumn("{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            )
        
        progress.start()
        task = progress.add_task(description, total=total)
        return progress
    
    async def show_loading(self, description: str, coro) -> Any:
        """Show loading spinner while executing coroutine.
        
        Args:
            description: Loading description
            coro: Coroutine to execute
            
        Returns:
            Any: Result of coroutine execution
        """
        with self.display_progress(description) as progress:
            task = progress.add_task(description)
            result = await coro
            progress.update(task, completed=100)
            return result
    
    def display_error(self, message: str, details: Optional[str] = None) -> None:
        """Display error message.
        
        Args:
            message: Error message
            details: Optional error details
        """
        error_text = f"{EMOJI['error']} {message}"
        if details:
            error_text += f"\n[dim]{details}[/dim]"
        
        panel = Panel(
            error_text,
            title="Error",
            box=box.ROUNDED,
            style="red"
        )
        self.console.print(panel)
    
    def display_success(self, message: str, details: Optional[str] = None) -> None:
        """Display success message.
        
        Args:
            message: Success message
            details: Optional success details
        """
        success_text = f"{EMOJI['success']} {message}"
        if details:
            success_text += f"\n[dim]{details}[/dim]"
        
        panel = Panel(
            success_text,
            title="Success",
            box=box.ROUNDED,
            style="green"
        )
        self.console.print(panel)
    
    def display_warning(self, message: str, details: Optional[str] = None) -> None:
        """Display warning message.
        
        Args:
            message: Warning message
            details: Optional warning details
        """
        warning_text = f"{EMOJI['warning']} {message}"
        if details:
            warning_text += f"\n[dim]{details}[/dim]"
        
        panel = Panel(
            warning_text,
            title="Warning",
            box=box.ROUNDED,
            style="yellow"
        )
        self.console.print(panel)
    
    def display_info(self, message: str, title: str = "Information") -> None:
        """Display information message.
        
        Args:
            message: Information message
            title: Panel title
        """
        panel = Panel(
            f"{EMOJI['info']} {message}",
            title=title,
            box=box.ROUNDED,
            style="blue"
        )
        self.console.print(panel)
    
    async def confirm_action(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """Get user confirmation for an action.
        
        Args:
            message: Confirmation message
            default: Default value if user just presses Enter
            
        Returns:
            bool: User confirmation
        """
        try:
            return Prompt.ask(
                f"[bold yellow]{message}[/bold yellow]",
                choices=["y", "n", "yes", "no"],
                default="y" if default else "n",
                console=self.console
            ).lower() in ["y", "yes"]
        except KeyboardInterrupt:
            return False
    
    async def get_selection_from_list(
        self,
        items: List[Dict[str, Any]],
        title: str,
        entity_type: str = "item",
        allow_cancel: bool = True
    ) -> SelectionResult:
        """Get user selection from a list of items.
        
        Args:
            items: List of items to select from
            title: Selection title
            entity_type: Type of entity being selected
            allow_cancel: Whether to allow cancellation
            
        Returns:
            SelectionResult: Result of selection
        """
        if not items:
            return SelectionResult.error_result(f"No {entity_type}s available for selection")
        
        # Display items
        self.display_entity_table(items, title, entity_type, show_numbers=True)
        
        # Get user selection
        max_num = len(items)
        cancel_text = ", or 0 to cancel" if allow_cancel else ""
        prompt = f"Enter number (1-{max_num}{cancel_text})"
        
        try:
            choice = await self.get_user_choice(prompt, expect_int=True)
            
            if choice == 0 and allow_cancel:
                return SelectionResult.cancelled_result()
            
            if 1 <= choice <= max_num:
                selected_item = items[choice - 1]
                return SelectionResult.success_result(selected_item, choice - 1)
            else:
                return SelectionResult.error_result(f"Invalid selection: {choice}")
                
        except InputError as e:
            return SelectionResult.error_result(str(e))
    
    def display_separator(self, title: Optional[str] = None) -> None:
        """Display a separator line.
        
        Args:
            title: Optional title for the separator
        """
        if title:
            self.console.print(Rule(title, style="dim"))
        else:
            self.console.print(Rule(style="dim"))
    
    def clear_screen(self) -> None:
        """Clear the console screen."""
        self.console.clear()
    
    async def wait_for_keypress(self, message: str = "Press Enter to continue...") -> None:
        """Wait for user to press a key.
        
        Args:
            message: Message to display
        """
        try:
            Prompt.ask(
                f"\n[dim]{message}[/dim]",
                default="",
                show_default=False,
                console=self.console
            )
        except KeyboardInterrupt:
            pass
    
    def display_help(self, command_info: Optional[Dict[str, str]] = None) -> None:
        """Display help information.
        
        Args:
            command_info: Optional command-specific help
        """
        help_text = f"""
{EMOJI['info']} [bold]SakaiBot CLI Help[/bold]

This CLI allows you to configure and manage your SakaiBot instance.

[bold]Key Features:[/bold]
• Configure private chat contexts for analysis
• Set up message categorization to groups/topics
• Manage user authorization for direct commands
• Monitor and process commands globally

[bold]Quick Setup:[/bold]
1. Set target group for categorization (Option 5)
2. Configure command mappings (Option 6)
3. Start monitoring (Option 7)

[bold]Tips:[/bold]
• Use refresh (Option 2) if you don't see recent chats
• Forum groups allow topic-specific categorization
• Authorized users can send commands directly to the bot
"""
        
        if command_info:
            help_text += f"\n[bold]Command Info:[/bold]\n{command_info.get('description', '')}"
        
        panel = Panel(
            help_text,
            title="Help",
            box=box.DOUBLE,
            style="blue"
        )
        self.console.print(panel)
    
    def display_state_summary(self, state: CLIState) -> None:
        """Display comprehensive state summary.
        
        Args:
            state: CLI state to summarize
        """
        summary = state.get_state_summary()
        
        # Create summary table
        table = Table(
            title="Configuration Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white", width=40)
        table.add_column("Status", width=15)
        
        # Add rows
        rows = [
            ("Default PV", summary["default_pv"], "✓" if "None" not in summary["default_pv"] else "○"),
            ("Target Group", summary["target_group"], "✓" if "No group" not in summary["target_group"] else "○"),
            ("Authorized Users", str(summary["authorized_pvs_count"]), "✓" if summary["authorized_pvs_count"] > 0 else "○"),
            ("Command Mappings", str(summary["command_mappings_count"]), "✓" if summary["command_mappings_count"] > 0 else "○"),
            ("API Configuration", "Configured" if summary["api_configured"] else "Missing", "✓" if summary["api_configured"] else "✗"),
            ("Monitoring", "Active" if summary["monitoring_active"] else "Inactive", "✓" if summary["monitoring_active"] else "○"),
            ("Can Categorize", "Yes" if summary["can_categorize"] else "No", "✓" if summary["can_categorize"] else "○")
        ]
        
        for setting, value, status in rows:
            status_style = "green" if status == "✓" else "red" if status == "✗" else "yellow"
            table.add_row(setting, value, f"[{status_style}]{status}[/{status_style}]")
        
        self.console.print(table)
    
    async def search_entities(
        self,
        entities: List[Dict[str, Any]],
        entity_type: str = "PV"
    ) -> List[Dict[str, Any]]:
        """Interactive search for entities.
        
        Args:
            entities: List of entities to search
            entity_type: Type of entity being searched
            
        Returns:
            List[Dict[str, Any]]: Filtered entities
        """
        if not entities:
            self.display_warning(f"No {entity_type.lower()}s available to search")
            return []
        
        try:
            query = await self.get_user_choice(
                f"Enter search term (User ID, @Username, or Name)",
                expect_int=False
            )
            
            if not query:
                self.display_warning("Search term cannot be empty")
                return []
            
            criteria = SearchCriteria(query=query, search_type="all")
            
            if entity_type == "PV":
                results = [pv for pv in entities if criteria.matches_pv(pv)]
            else:
                # For other entity types, implement basic text search
                query_lower = query.lower()
                results = [
                    entity for entity in entities
                    if query_lower in str(entity.get('title', '')).lower() or
                       query_lower in str(entity.get('display_name', '')).lower() or
                       str(entity.get('id', '')) == query
                ]
            
            if results:
                self.display_entity_table(
                    results,
                    f"Search Results for '{query}'",
                    entity_type,
                    show_numbers=True
                )
            else:
                self.display_warning(f"No {entity_type.lower()}s found matching '{query}'")
            
            return results
            
        except InputError:
            return []
        except Exception as e:
            logger.error(f"Error during entity search: {e}", exc_info=True)
            self.display_error(f"Search failed: {str(e)}")
            return []
    
    def display_monitoring_requirements(self, missing_requirements: List[str]) -> None:
        """Display monitoring requirements that are not met.
        
        Args:
            missing_requirements: List of missing requirements
        """
        if not missing_requirements:
            return
        
        requirements_text = "\n".join([f"• {req}" for req in missing_requirements])
        
        panel = Panel(
            f"Cannot start monitoring. Missing requirements:\n\n{requirements_text}",
            title="Requirements Not Met",
            box=box.ROUNDED,
            style="yellow"
        )
        self.console.print(panel)
    
    def display_welcome_message(self) -> None:
        """Display welcome message for first-time users."""
        welcome_text = f"""
{EMOJI['robot']} Welcome to {APP_NAME} CLI!

This interactive menu helps you configure and manage your Telegram userbot.

[bold]First-time setup:[/bold]
1. Use Option 5 to select a target group for categorization
2. Use Option 6 to configure command mappings
3. Use Option 7 to start monitoring
4. Optionally authorize other users (Option 8)

[bold]Need help?[/bold] Most options include detailed guidance.
"""
        
        panel = Panel(
            welcome_text,
            title="Welcome",
            box=box.DOUBLE,
            style="blue"
        )
        self.console.print(panel)
