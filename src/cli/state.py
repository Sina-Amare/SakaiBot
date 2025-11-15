"""CLI state management for SakaiBot."""

from typing import Dict, Any, List, Optional, Tuple
from src.core.config import Config

class CLIState:
    """Manages the state for CLI operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self._raw_selected_target_group: Optional[Any] = None
        self._selected_target_group: Optional[Dict[str, Any]] = None
        self._active_command_to_topic_map: Dict[Any, List[str]] = {}
        self.directly_authorized_pvs: List[Any] = []
        self.is_monitoring_active: bool = False
        self.settings_saved_on_cli_exit: bool = False
        self.registered_handler_info: Optional[Tuple[Any, Any, Any, Any]] = None
    
    @property
    def selected_target_group(self) -> Optional[Dict[str, Any]]:
        """Get normalized selected target group."""
        from ..cli.utils import normalize_selected_group
        if self._selected_target_group is None and self._raw_selected_target_group is not None:
            self._selected_target_group = normalize_selected_group(self._raw_selected_target_group)
        return self._selected_target_group
    
    @selected_target_group.setter
    def selected_target_group(self, value: Optional[Any]):
        """Set raw selected target group value."""
        self._raw_selected_target_group = value
        self._selected_target_group = None  # Reset cached normalized value
        
    @property
    def can_categorize(self) -> bool:
        """Check if categorization can be performed."""
        return (
            self.selected_target_group is not None and 
            len(self.active_command_to_topic_map) > 0
        )
    
    @property
    def can_use_ai(self) -> bool:
        """Check if AI features are available."""
        return self.config.is_ai_enabled if self.config else False
    
    @property
    def can_start_monitoring(self) -> bool:
        """Check if monitoring can be started."""
        # Monitoring can start if we have at least one of these:
        # - Categorization setup (target group + mappings)
        # - AI features enabled
        # - Authorized PVs configured
        return (
            self.can_categorize or 
            self.can_use_ai or 
            len(self.directly_authorized_pvs) > 0
        )
    @property
    def active_command_to_topic_map(self) -> Dict[Any, List[str]]:
        """Get normalized command-to-topic mappings."""
        return self._active_command_to_topic_map
    
    @active_command_to_topic_map.setter
    def active_command_to_topic_map(self, value: Any):
        """Normalise and set command-to-topic mappings."""
        from .utils import normalize_command_mappings
        self._active_command_to_topic_map = normalize_command_mappings(value)
    
    def to_settings_dict(self) -> Dict[str, Any]:
        """Convert CLI state to settings dictionary for persistence."""
        return {
            'selected_target_group': self._raw_selected_target_group,
            'active_command_to_topic_map': self._active_command_to_topic_map,
            'directly_authorized_pvs': self.directly_authorized_pvs,
            'is_monitoring_active': self.is_monitoring_active
        }
    
