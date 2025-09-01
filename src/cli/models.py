"""
Data models for CLI module.

This module defines data structures used throughout the CLI interface.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime

from src.core.constants import UserRole, ProcessingStatus


class MenuChoice(Enum):
    """Enumeration of main menu choices."""
    LIST_PV = auto()
    REFRESH_PV = auto()
    SEARCH_PV = auto()
    SET_DEFAULT_PV = auto()
    SET_TARGET_GROUP = auto()
    MANAGE_MAPPINGS = auto()
    TOGGLE_MONITORING = auto()
    MANAGE_AUTHORIZED = auto()
    VIEW_SETTINGS = auto()
    SAVE_SETTINGS = auto()
    EXIT = auto()


class InputType(Enum):
    """Types of user input."""
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    CONFIRMATION = "confirmation"
    PASSWORD = "password"


@dataclass
class CLIState:
    """
    Centralized state management for CLI.
    
    Attributes:
        selected_pv_for_categorization: Selected PV for analysis
        selected_target_group: Target group for message forwarding
        active_command_to_topic_map: Command to topic mappings
        directly_authorized_pvs: List of authorized PV IDs
        current_group_topics_cache: Cached forum topics
        is_monitoring_active: Whether monitoring is enabled
        settings_saved_on_cli_exit: Whether to save on exit
        openrouter_api_key: OpenRouter API key (if set via CLI)
        openrouter_model_name: Model name for OpenRouter
        max_analyze_messages: Maximum messages to analyze
        ffmpeg_path: Path to FFmpeg executable
        session_active: Whether a Telegram session is active
        last_refresh_time: Last time PV list was refreshed
    """
    selected_pv_for_categorization: Optional[Dict[str, Any]] = None
    selected_target_group: Optional[Dict[str, Any]] = None
    active_command_to_topic_map: Dict[str, int] = field(default_factory=dict)
    directly_authorized_pvs: List[int] = field(default_factory=list)
    current_group_topics_cache: List[Dict[str, Any]] = field(default_factory=list)
    is_monitoring_active: bool = False
    settings_saved_on_cli_exit: bool = True
    openrouter_api_key: Optional[str] = None
    openrouter_model_name: str = "deepseek/deepseek-chat"
    max_analyze_messages: int = 5000
    ffmpeg_path: Optional[str] = None
    session_active: bool = False
    last_refresh_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "selected_pv_for_categorization": self.selected_pv_for_categorization,
            "selected_target_group": self.selected_target_group,
            "active_command_to_topic_map": self.active_command_to_topic_map,
            "directly_authorized_pvs": self.directly_authorized_pvs,
            "current_group_topics_cache": self.current_group_topics_cache,
            "is_monitoring_active": self.is_monitoring_active,
            "settings_saved_on_cli_exit": self.settings_saved_on_cli_exit,
            "openrouter_model_name": self.openrouter_model_name,
            "max_analyze_messages": self.max_analyze_messages,
            "ffmpeg_path": self.ffmpeg_path,
            "last_refresh_time": self.last_refresh_time.isoformat() if self.last_refresh_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CLIState":
        """
        Create state from dictionary.
        
        Args:
            data: Dictionary containing state data
            
        Returns:
            CLIState instance
        """
        state = cls()
        
        # Update fields from dictionary
        for key, value in data.items():
            if hasattr(state, key):
                if key == "last_refresh_time" and value:
                    value = datetime.fromisoformat(value)
                setattr(state, key, value)
        
        return state


@dataclass
class MenuItem:
    """
    Represents a single menu item.
    
    Attributes:
        id: Unique identifier for the menu item
        label: Display label
        description: Detailed description
        action: Callable action or submenu
        enabled: Whether the item is enabled
        requires_session: Whether item requires active Telegram session
        icon: Optional emoji or symbol for the item
    """
    id: str
    label: str
    description: str
    action: Optional[Callable] = None
    enabled: bool = True
    requires_session: bool = False
    icon: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of menu item."""
        prefix = self.icon if self.icon else ""
        status = "" if self.enabled else " (disabled)"
        return f"{prefix} {self.label}{status}"


@dataclass
class MenuSection:
    """
    Represents a section of menu items.
    
    Attributes:
        title: Section title
        items: List of menu items in this section
        description: Optional section description
    """
    title: str
    items: List[MenuItem]
    description: Optional[str] = None


@dataclass
class UserInput:
    """
    Represents validated user input.
    
    Attributes:
        value: The input value
        input_type: Type of input
        validated: Whether input was validated
        validation_error: Error message if validation failed
    """
    value: Any
    input_type: InputType
    validated: bool = False
    validation_error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if input is valid."""
        return self.validated and not self.validation_error


@dataclass
class CommandMapping:
    """
    Represents a command to topic mapping.
    
    Attributes:
        command: The command string (without /)
        topic_id: The forum topic ID
        description: Optional description of the mapping
        created_at: When the mapping was created
        usage_count: Number of times the mapping was used
    """
    command: str
    topic_id: int
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    
    def increment_usage(self) -> None:
        """Increment the usage counter."""
        self.usage_count += 1


@dataclass
class PVSearchResult:
    """
    Represents a private chat search result.
    
    Attributes:
        id: Chat ID
        display_name: Display name of the chat
        username: Username if available
        match_type: Type of match (name, username, id)
        score: Match score for ranking
    """
    id: int
    display_name: str
    username: Optional[str]
    match_type: str
    score: float = 0.0
    
    def __str__(self) -> str:
        """String representation of search result."""
        username_str = f" (@{self.username})" if self.username else ""
        return f"{self.display_name}{username_str} [ID: {self.id}]"


@dataclass
class GroupInfo:
    """
    Information about a Telegram group.
    
    Attributes:
        id: Group ID
        title: Group title
        is_forum: Whether the group is a forum
        topic_count: Number of topics if forum
        member_count: Number of members
        is_admin: Whether bot is admin
    """
    id: int
    title: str
    is_forum: bool = False
    topic_count: int = 0
    member_count: int = 0
    is_admin: bool = False
    
    def __str__(self) -> str:
        """String representation of group info."""
        forum_str = " (Forum)" if self.is_forum else ""
        return f"{self.title}{forum_str} [Members: {self.member_count}]"


@dataclass
class SelectionResult:
    """
    Result of a selection operation.
    
    Attributes:
        success: Whether the selection was successful
        value: The selected value (if successful)
        index: The index of the selection (if applicable)
        error: Error message (if failed)
        cancelled: Whether the selection was cancelled
    """
    success: bool
    value: Optional[Any] = None
    index: Optional[int] = None
    error: Optional[str] = None
    cancelled: bool = False
    
    @classmethod
    def success_result(cls, value: Any, index: Optional[int] = None) -> "SelectionResult":
        """Create a successful result."""
        return cls(success=True, value=value, index=index)
    
    @classmethod
    def error_result(cls, error: str) -> "SelectionResult":
        """Create an error result."""
        return cls(success=False, error=error)
    
    @classmethod
    def cancelled_result(cls) -> "SelectionResult":
        """Create a cancelled result."""
        return cls(success=False, cancelled=True)


@dataclass
class SearchCriteria:
    """
    Search criteria for filtering items.
    
    Attributes:
        query: Search query string
        field: Field to search in
        case_sensitive: Whether search is case sensitive
        exact_match: Whether to require exact match
        limit: Maximum number of results
    """
    query: str
    field: Optional[str] = None
    case_sensitive: bool = False
    exact_match: bool = False
    limit: Optional[int] = None


@dataclass
class MenuOption:
    """
    Represents a menu option.
    
    Attributes:
        key: Option key/number
        label: Display label
        action: Action identifier
        enabled: Whether the option is enabled
        description: Optional description
    """
    key: str
    label: str
    action: str
    enabled: bool = True
    description: Optional[str] = None


@dataclass
class TableColumn:
    """
    Represents a table column for display.
    
    Attributes:
        name: Column name
        width: Column width (optional)
        align: Column alignment ('left', 'center', 'right')
    """
    name: str
    width: Optional[int] = None
    align: str = 'left'


@dataclass
class TableData:
    """
    Represents table data for display.
    
    Attributes:
        columns: List of table columns
        rows: List of rows (each row is a list of values)
        title: Optional table title
        show_index: Whether to show row indices
    """
    columns: List[TableColumn]
    rows: List[List[Any]]
    title: Optional[str] = None
    show_index: bool = True


@dataclass
class MenuAction:
    """
    Represents a menu action result.
    
    Attributes:
        action: Action identifier
        data: Optional data associated with the action
        next_menu: Next menu to display (if any)
        exit: Whether to exit the menu
    """
    action: str
    data: Optional[Any] = None
    next_menu: Optional[str] = None
    exit: bool = False


@dataclass
class CLIContext:
    """
    Context for CLI operations.
    
    Attributes:
        client: Telegram client instance
        state: Current CLI state
        session: Current CLI session
        config: Application configuration
    """
    client: Optional[Any] = None
    state: Optional[CLIState] = None
    session: Optional['CLISession'] = None
    config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.state is None:
            self.state = CLIState()
        if self.session is None:
            self.session = CLISession()


@dataclass
class CLISession:
    """
    Represents a CLI session.
    
    Attributes:
        start_time: When the session started
        user: Username running the session
        commands_executed: Number of commands executed
        errors_encountered: Number of errors encountered
        state: Current CLI state
    """
    start_time: datetime = field(default_factory=datetime.now)
    user: Optional[str] = None
    commands_executed: int = 0
    errors_encountered: int = 0
    state: CLIState = field(default_factory=CLIState)
    
    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def record_command(self) -> None:
        """Record a command execution."""
        self.commands_executed += 1
    
    def record_error(self) -> None:
        """Record an error."""
        self.errors_encountered += 1


@dataclass
class ProgressStep:
    """
    Represents a step in a progress operation.
    
    Attributes:
        name: Step name
        description: Step description
        total: Total units of work
        completed: Completed units
        status: Current status
    """
    name: str
    description: str
    total: int = 100
    completed: int = 0
    status: str = "pending"
    
    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100


@dataclass
class ValidationRule:
    """
    Represents a validation rule.
    
    Attributes:
        field: Field to validate
        rule_type: Type of validation
        value: Expected value or pattern
        message: Error message if validation fails
    """
    field: str
    rule_type: str
    value: Any
    message: str


class CLIMode(Enum):
    """CLI operation modes."""
    INTERACTIVE = "interactive"
    COMMAND = "command"
    BATCH = "batch"
    DAEMON = "daemon"


@dataclass
class CLICommand:
    """
    Represents a CLI command.
    
    Attributes:
        name: Command name
        description: Command description
        handler: Command handler function
        args: Command arguments
        options: Command options
        requires_auth: Whether command requires authentication
    """
    name: str
    description: str
    handler: Callable
    args: List[Tuple[str, type]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = True