"""Modern CLI module for SakaiBot.

This module provides a comprehensive command-line interface using Click framework
and Rich for beautiful terminal UI, with full async support and modern Python practices.

Key Features:
- Click-based command structure with async support
- Rich terminal UI with tables, progress bars, and beautiful formatting
- Comprehensive state management with persistence
- Type-safe models and validation
- Clean separation of concerns
- Backward compatibility with legacy CLI

Usage:
    # Interactive mode
    python -m src.cli.interface interactive
    
    # Command mode
    python -m src.cli.interface list-pvs
    python -m src.cli.interface refresh
    python -m src.cli.interface monitor --start
    
    # Legacy compatibility
    from src.cli import display_main_menu_loop
    await display_main_menu_loop(...)
"""

from .interface import cli, display_main_menu_loop
from .commands import CLICommands
from .menu import RichMenu
from .models import (
    CLIState,
    MenuAction,
    MenuOption,
    SelectionResult,
    TableData,
    TableColumn,
    SearchCriteria,
    CommandMapping,
    CLIContext,
    ProgressStep,
    UserInput,
    ValidationRule,
    CLICommand,
    CLIMode
)
from .state import (
    StateManager,
    initialize_state,
    get_state_manager,
    set_state_manager,
    validate_state_for_action,
    get_state_health_check
)

__all__ = [
    # Main interfaces
    "cli",
    "display_main_menu_loop",
    
    # Core classes
    "CLICommands",
    "RichMenu",
    "StateManager",
    
    # Models
    "CLIState",
    "MenuAction",
    "MenuOption",
    "SelectionResult",
    "TableData",
    "TableColumn",
    "SearchCriteria",
    "CommandMapping",
    "CLIContext",
    "ProgressStep",
    "UserInput",
    "ValidationRule",
    "CLICommand",
    "CLIMode",
    
    # State management
    "initialize_state",
    "get_state_manager",
    "set_state_manager",
    "validate_state_for_action",
    "get_state_health_check"
]

# Module metadata
__version__ = "2.0.0"
__author__ = "SakaiBot Team"
__description__ = "Modern CLI interface for SakaiBot with Click and Rich"
