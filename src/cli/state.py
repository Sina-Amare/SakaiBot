"""CLI state management for SakaiBot."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple

from ..core.config import Config


@dataclass
class CLIState:
    """Manages the state of the CLI interface."""
    
    # PV and Group Selection
    selected_pv_for_categorization: Optional[Dict[str, Any]] = None
    selected_target_group: Optional[Dict[str, Any]] = None
    
    # Command Mappings
    active_command_to_topic_map: Dict[str, Optional[int]] = field(default_factory=dict)
    directly_authorized_pvs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Cache
    current_group_topics_cache: List[Dict[str, Any]] = field(default_factory=list)
    
    # Monitoring State
    is_monitoring_active: bool = False
    registered_handler_info: Optional[Tuple[Any, Any, Any, List[Any]]] = None
    
    # Configuration
    config: Optional[Config] = None
    
    # Settings Management
    settings_saved_on_cli_exit: bool = False
    
    def __post_init__(self) -> None:
        """Initialize state after creation."""
        if self.config is None:
            from ..core.config import settings
            self.config = settings
    
    @property
    def can_categorize(self) -> bool:
        """Check if categorization is properly configured."""
        return bool(
            self.selected_target_group and 
            self.active_command_to_topic_map
        )
    
    @property
    def can_use_ai(self) -> bool:
        """Check if AI features are available."""
        return self.config is not None and self.config.is_ai_enabled
    
    @property
    def can_start_monitoring(self) -> bool:
        """Check if monitoring can be started."""
        return self.can_categorize or self.can_use_ai
    
    def get_pv_display_name(self) -> str:
        """Get display name for selected PV."""
        if self.selected_pv_for_categorization:
            return self.selected_pv_for_categorization.get('display_name', 'Unknown')
        return "None (Uses current chat for /analyze)"
    
    def get_group_status_text(self) -> str:
        """Get status text for selected group."""
        if not self.selected_target_group:
            return "(No group selected for categorization)"
        
        group_type = "Forum Group" if self.selected_target_group.get('is_forum') else "Regular Group"
        group_title = self.selected_target_group.get('title', 'N/A')
        return f"(Categorization Target: '{group_title}' - {group_type})"
    
    def get_monitoring_status(self) -> str:
        """Get monitoring status text."""
        return "Stop GLOBAL Monitoring" if self.is_monitoring_active else "Start GLOBAL Monitoring"
    
    def clear_command_mappings(self) -> None:
        """Clear command mappings when target group changes."""
        self.active_command_to_topic_map.clear()
        self.current_group_topics_cache.clear()
    
    def to_settings_dict(self) -> Dict[str, Any]:
        """Convert state to settings dictionary for persistence."""
        return {
            "selected_pv_for_categorization": self.selected_pv_for_categorization,
            "selected_target_group": self.selected_target_group,
            "active_command_to_topic_map": self.active_command_to_topic_map,
            "directly_authorized_pvs": self.directly_authorized_pvs
        }
    
    def load_from_settings(self, settings_data: Dict[str, Any]) -> None:
        """Load state from settings dictionary."""
        self.selected_pv_for_categorization = settings_data.get("selected_pv_for_categorization")
        self.selected_target_group = settings_data.get("selected_target_group")
        self.active_command_to_topic_map = settings_data.get("active_command_to_topic_map", {})
        self.directly_authorized_pvs = settings_data.get("directly_authorized_pvs", [])
    
    def is_pv_authorized(self, pv_id: int) -> bool:
        """Check if a PV is authorized for direct commands."""
        return any(pv['id'] == pv_id for pv in self.directly_authorized_pvs)
    
    def add_authorized_pv(self, pv_info: Dict[str, Any]) -> bool:
        """Add a PV to the authorized list. Returns True if added, False if already exists."""
        if self.is_pv_authorized(pv_info['id']):
            return False
        
        auth_info = {
            'id': pv_info['id'],
            'display_name': pv_info['display_name'],
            'username': pv_info['username']
        }
        self.directly_authorized_pvs.append(auth_info)
        return True
    
    def remove_authorized_pv(self, pv_id: int) -> Optional[Dict[str, Any]]:
        """Remove a PV from the authorized list. Returns the removed PV info if found."""
        for i, pv in enumerate(self.directly_authorized_pvs):
            if pv['id'] == pv_id:
                return self.directly_authorized_pvs.pop(i)
        return None
