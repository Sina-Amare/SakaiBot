"""CLI state management for SakaiBot."""

from typing import Dict, Any, List, Optional
from src.core.config import Config

class CLIState:
    """Manages the state for CLI operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.selected_target_group: Optional[Dict[str, Any]] = None
        self.active_command_to_topic_map: Dict[str, Any] = {}
        self.directly_authorized_pvs: List[Any] = []
        self.is_monitoring_active: bool = False
        
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