"""State management for CLI operations.

This module handles the persistent state of the CLI application,
including user selections, configuration, and session management.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .models import CLIState, MenuAction
from ..core.exceptions import CLIError, InputError
from ..core.constants import APP_NAME

logger = logging.getLogger(__name__)


class StateManager:
    """Manages CLI state persistence and operations."""
    
    def __init__(self, settings_manager=None):
        """Initialize state manager.
        
        Args:
            settings_manager: Settings manager instance for persistence
        """
        self._state = CLIState()
        self._settings_manager = settings_manager
        self._initialized = False
    
    @property
    def state(self) -> CLIState:
        """Get current CLI state."""
        return self._state
    
    async def initialize(
        self,
        openrouter_api_key: str,
        openrouter_model_name: str,
        max_analyze_messages: int,
        ffmpeg_path: Optional[str] = None
    ) -> None:
        """Initialize state with configuration values.
        
        Args:
            openrouter_api_key: OpenRouter API key
            openrouter_model_name: Default model name
            max_analyze_messages: Maximum messages to analyze
            ffmpeg_path: Path to FFmpeg executable
        """
        try:
            self._state.openrouter_api_key = openrouter_api_key
            self._state.openrouter_model_name = openrouter_model_name
            self._state.max_analyze_messages = max_analyze_messages
            self._state.ffmpeg_path = ffmpeg_path
            self._state.settings_saved_on_exit = False
            
            # Load persisted settings if available
            if self._settings_manager:
                await self._load_persisted_settings()
            
            self._initialized = True
            logger.info(f"{APP_NAME} CLI state initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CLI state: {e}", exc_info=True)
            raise CLIError(f"State initialization failed: {e}")
    
    async def _load_persisted_settings(self) -> None:
        """Load settings from persistent storage."""
        try:
            if not self._settings_manager:
                return
            
            loaded_settings = self._settings_manager.load_user_settings()
            
            if loaded_settings:
                self._state.selected_pv_for_categorization = loaded_settings.get("selected_pv_for_categorization")
                self._state.selected_target_group = loaded_settings.get("selected_target_group")
                self._state.active_command_to_topic_map = loaded_settings.get("active_command_to_topic_map", {})
                self._state.directly_authorized_pvs = loaded_settings.get("directly_authorized_pvs", [])
                
                logger.info(
                    f"Loaded settings: "
                    f"authorized_pvs={len(self._state.directly_authorized_pvs)}, "
                    f"mappings={len(self._state.active_command_to_topic_map)}"
                )
            
        except Exception as e:
            logger.warning(f"Failed to load persisted settings: {e}")
            # Don't raise - continue with defaults
    
    async def cache_group_topics(
        self,
        client,
        telegram_utils
    ) -> None:
        """Cache topics for the selected target group if it's a forum."""
        if not self._state.selected_target_group:
            return
        
        if not self._state.selected_target_group.get('is_forum'):
            self._state.current_group_topics_cache = []
            return
        
        try:
            group_id = self._state.selected_target_group['id']
            group_title = self._state.selected_target_group.get('title', 'N/A')
            
            logger.info(f"Caching topics for forum group '{group_title}'...")
            
            topics, _ = await telegram_utils.get_group_topics(client, group_id)
            self._state.current_group_topics_cache = topics
            
            logger.info(f"Cached {len(topics)} topics for group '{group_title}'")
            
        except Exception as e:
            logger.error(f"Failed to cache group topics: {e}", exc_info=True)
            self._state.current_group_topics_cache = []
    
    def set_default_pv(self, pv_data: Dict[str, Any]) -> None:
        """Set default PV for categorization.
        
        Args:
            pv_data: PV data dictionary
        """
        self._state.selected_pv_for_categorization = pv_data
        logger.info(
            f"Default PV context set: ID={pv_data['id']}, "
            f"Name='{pv_data['display_name']}'"
        )
    
    def clear_default_pv(self) -> None:
        """Clear default PV context."""
        self._state.selected_pv_for_categorization = None
        logger.info("Default PV context cleared")
    
    def set_target_group(self, group_data: Dict[str, Any]) -> None:
        """Set target group for categorization.
        
        Args:
            group_data: Group data dictionary
        """
        # Clear mappings if changing groups
        if (
            self._state.selected_target_group and
            self._state.selected_target_group['id'] != group_data['id']
        ):
            logger.info("Target group changed. Clearing command-topic mappings.")
            self._state.active_command_to_topic_map = {}
        
        self._state.selected_target_group = group_data
        logger.info(
            f"Target group set: ID={group_data['id']}, "
            f"Title='{group_data['title']}', "
            f"Is Forum: {group_data['is_forum']}"
        )
    
    def add_command_mapping(self, command: str, topic_id: Optional[int]) -> None:
        """Add command to topic mapping.
        
        Args:
            command: Command name (without /)
            topic_id: Topic ID or None for main chat
        """
        command = command.strip().lower().replace(" ", "_")
        self._state.active_command_to_topic_map[command] = topic_id
        
        logger.info(f"Added command mapping: /{command} -> {topic_id or 'Main Chat'}")
    
    def remove_command_mapping(self, command: str) -> bool:
        """Remove command mapping.
        
        Args:
            command: Command name to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if command in self._state.active_command_to_topic_map:
            del self._state.active_command_to_topic_map[command]
            logger.info(f"Removed command mapping: /{command}")
            return True
        return False
    
    def authorize_pv(self, pv_data: Dict[str, Any]) -> bool:
        """Authorize a PV for direct commands.
        
        Args:
            pv_data: PV data dictionary
            
        Returns:
            bool: True if authorized, False if already authorized
        """
        pv_id = pv_data['id']
        
        # Check if already authorized
        if self._state.is_pv_authorized(pv_id):
            return False
        
        auth_info = {
            'id': pv_id,
            'display_name': pv_data['display_name'],
            'username': pv_data['username']
        }
        
        self._state.directly_authorized_pvs.append(auth_info)
        logger.info(f"Authorized PV: {auth_info['display_name']} (ID: {pv_id})")
        return True
    
    def deauthorize_pv(self, pv_id: int) -> Optional[Dict[str, Any]]:
        """Deauthorize a PV.
        
        Args:
            pv_id: PV ID to deauthorize
            
        Returns:
            Optional[Dict[str, Any]]: Deauthorized PV data or None if not found
        """
        for i, pv in enumerate(self._state.directly_authorized_pvs):
            if pv['id'] == pv_id:
                deauthorized = self._state.directly_authorized_pvs.pop(i)
                logger.info(f"Deauthorized PV: {deauthorized['display_name']} (ID: {pv_id})")
                return deauthorized
        return None
    
    def set_monitoring_active(
        self,
        active: bool,
        handler_info: Optional[tuple] = None
    ) -> None:
        """Set monitoring state.
        
        Args:
            active: Whether monitoring is active
            handler_info: Handler information tuple
        """
        self._state.is_monitoring_active = active
        self._state.registered_handler_info = handler_info
        
        status = "started" if active else "stopped"
        logger.info(f"Monitoring {status}")
    
    async def save_settings(self) -> None:
        """Save current state to persistent storage."""
        if not self._settings_manager:
            logger.warning("No settings manager available for saving")
            return
        
        try:
            settings_dict = self._state.to_settings_dict()
            self._settings_manager.save_user_settings(settings_dict)
            self._state.settings_saved_on_exit = True
            logger.info("CLI settings saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save CLI settings: {e}", exc_info=True)
            raise CLIError(f"Settings save failed: {e}")
    
    def validate_state(self) -> tuple[bool, List[str]]:
        """Validate current state for common operations.
        
        Returns:
            tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        if not self._state.openrouter_api_key:
            issues.append("OpenRouter API key not configured")
        
        if self._state.selected_target_group and not self._state.active_command_to_topic_map:
            issues.append("Target group selected but no command mappings defined")
        
        return len(issues) == 0, issues
    
    def reset_state(self) -> None:
        """Reset CLI state to defaults."""
        logger.info("Resetting CLI state to defaults")
        self._state = CLIState()
        self._initialized = False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state.
        
        Returns:
            Dict[str, Any]: State summary for display
        """
        return {
            "default_pv": self._state.get_pv_display_name(),
            "target_group": self._state.get_group_status_text(),
            "authorized_pvs_count": len(self._state.directly_authorized_pvs),
            "command_mappings_count": len(self._state.active_command_to_topic_map),
            "monitoring_active": self._state.is_monitoring_active,
            "api_configured": bool(self._state.openrouter_api_key),
            "can_categorize": bool(
                self._state.selected_target_group and 
                self._state.active_command_to_topic_map
            )
        }


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get or create the global state manager instance.
    
    Returns:
        StateManager: Global state manager
        
    Raises:
        CLIError: If state manager cannot be created
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the global state manager instance.
    
    Args:
        manager: StateManager instance to set as global
    """
    global _state_manager
    _state_manager = manager


async def initialize_state(
    openrouter_api_key: str,
    openrouter_model_name: str,
    max_analyze_messages: int,
    ffmpeg_path: Optional[str] = None,
    settings_manager=None
) -> StateManager:
    """Initialize CLI state with configuration.
    
    Args:
        openrouter_api_key: OpenRouter API key
        openrouter_model_name: Default model name
        max_analyze_messages: Maximum messages to analyze
        ffmpeg_path: Path to FFmpeg executable
        settings_manager: Settings manager for persistence
        
    Returns:
        StateManager: Initialized state manager
        
    Raises:
        CLIError: If initialization fails
    """
    try:
        manager = StateManager(settings_manager)
        await manager.initialize(
            openrouter_api_key,
            openrouter_model_name,
            max_analyze_messages,
            ffmpeg_path
        )
        set_state_manager(manager)
        return manager
        
    except Exception as e:
        logger.error(f"State initialization failed: {e}", exc_info=True)
        raise CLIError(f"Could not initialize CLI state: {e}")


def validate_state_for_action(action: MenuAction, state: CLIState) -> tuple[bool, List[str]]:
    """Validate state requirements for a specific action.
    
    Args:
        action: Menu action to validate
        state: Current CLI state
        
    Returns:
        tuple[bool, List[str]]: (is_valid, list_of_missing_requirements)
    """
    missing = []
    
    if action == MenuAction.TOGGLE_MONITORING:
        can_start, reasons = state.can_start_monitoring()
        if not can_start:
            missing.extend(reasons)
    
    elif action == MenuAction.MANAGE_MAPPINGS:
        if not state.selected_target_group:
            missing.append("Target group must be selected first")
    
    elif action in [MenuAction.SET_DEFAULT_PV, MenuAction.SEARCH_PVS]:
        # These actions work with cached data, no specific requirements
        pass
    
    elif action == MenuAction.MANAGE_AUTHORIZED:
        # This action manages the authorization list, no specific requirements
        pass
    
    return len(missing) == 0, missing


def get_state_health_check() -> Dict[str, Any]:
    """Get health check information for current state.
    
    Returns:
        Dict[str, Any]: Health check results
    """
    try:
        manager = get_state_manager()
        state = manager.state
        
        health = {
            "status": "healthy",
            "initialized": manager._initialized,
            "api_configured": bool(state.openrouter_api_key),
            "target_group_set": bool(state.selected_target_group),
            "mappings_defined": len(state.active_command_to_topic_map) > 0,
            "authorized_users": len(state.directly_authorized_pvs),
            "monitoring_active": state.is_monitoring_active,
            "issues": []
        }
        
        # Check for issues
        is_valid, issues = manager.validate_state()
        if not is_valid:
            health["status"] = "degraded"
            health["issues"] = issues
        
        return health
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "initialized": False
        }
