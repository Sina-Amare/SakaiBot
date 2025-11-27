"""CLI handler for SakaiBot that integrates InteractiveMenu with Telegram client."""

from typing import Optional
from telethon import TelegramClient

from .interactive import InteractiveMenu
from .state import CLIState
from ..core.config import Config, get_settings
from ..utils.cache import CacheManager
from ..telegram.utils import TelegramUtils
from ..core.settings import SettingsManager
from ..telegram.event_handlers import EventHandlers
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CLIHandler:
    """Handles CLI operations and integrates InteractiveMenu with Telegram client."""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        telegram_utils: TelegramUtils,
        settings_manager: SettingsManager,
        event_handlers: EventHandlers
    ):
        """
        Initialize CLIHandler.
        
        Args:
            cache_manager: Cache manager instance
            telegram_utils: Telegram utilities instance
            settings_manager: Settings manager instance
            event_handlers: Event handlers instance
        """
        self._cache_manager = cache_manager
        self._telegram_utils = telegram_utils
        self._settings_manager = settings_manager
        self._event_handlers = event_handlers
        
        # Get config for CLIState
        config = get_settings()
        
        # Initialize CLI state
        self._cli_state = CLIState(config)
        
        # Load existing settings into CLI state
        self._load_settings_into_state()
        
        # Initialize InteractiveMenu
        self._interactive_menu = InteractiveMenu()
        
        logger.info("CLIHandler initialized")
    
    @property
    def cli_state(self) -> CLIState:
        """Get the CLI state instance."""
        return self._cli_state
    
    def _load_settings_into_state(self) -> None:
        """Load existing user settings into CLI state."""
        try:
            settings = self._settings_manager.load_user_settings()
            
            if settings:
                self._cli_state.selected_target_group = settings.get('selected_target_group')
                self._cli_state.active_command_to_topic_map = settings.get('active_command_to_topic_map', {})
                self._cli_state.directly_authorized_pvs = settings.get('directly_authorized_pvs', [])
                self._cli_state.is_monitoring_active = settings.get('is_monitoring_active', False)
                
                logger.debug("Loaded settings into CLI state")
        except Exception as e:
            logger.warning(f"Failed to load settings into CLI state: {e}")
    
    async def display_main_menu_loop(self, client: TelegramClient) -> None:
        """
        Display main menu loop and handle user interactions.
        
        Args:
            client: Telegram client instance
        """
        logger.info("Starting main menu loop")
        
        try:
            # Run the interactive menu
            await self._interactive_menu.run()
            
            # When menu exits (option 0), mark settings as saved
            self._cli_state.settings_saved_on_cli_exit = True
            
            # Save settings before exiting
            settings_to_save = self._cli_state.to_settings_dict()
            self._settings_manager.save_user_settings(settings_to_save)
            
            logger.info("Main menu loop completed, settings saved")
            
        except KeyboardInterrupt:
            logger.info("Main menu loop interrupted by user")
            # Settings will be saved in graceful shutdown
        except Exception as e:
            logger.error(f"Error in main menu loop: {e}", exc_info=True)
            raise

