"""Main entry point for SakaiBot."""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .core.config import Config, load_config
from .core.exceptions import ConfigurationError, TelegramError
from .core.settings import SettingsManager
from .telegram.client import TelegramClientManager
from .telegram.utils import TelegramUtils
from .telegram.event_handlers import EventHandlers
from .ai.processor import AIProcessor
from .ai.stt import SpeechToTextProcessor
from .ai.tts import TextToSpeechProcessor
from .utils.cache import CacheManager
from .utils.logging import setup_logging, get_logger
from .utils.task_manager import get_task_manager
from .utils.instance_lock import InstanceLock
from .ai.analyze_queue import analyze_queue
from .cli.handler import CLIHandler


class SakaiBot:
    """Main SakaiBot application class."""
    
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        
        # Initialize components
        self._client_manager = TelegramClientManager(config)
        self._telegram_utils = TelegramUtils()
        self._cache_manager = CacheManager()
        self._settings_manager = SettingsManager()
        
        # Initialize AI components
        self._ai_processor = AIProcessor(config)
        self._stt_processor = SpeechToTextProcessor()
        self._tts_processor = TextToSpeechProcessor()
        
        # Initialize event handlers
        self._event_handlers = EventHandlers(
            ai_processor=self._ai_processor,
            stt_processor=self._stt_processor,
            tts_processor=self._tts_processor,
            ffmpeg_path=config.ffmpeg_path_resolved
        )
        
        # Initialize CLI handler
        self._cli_handler = CLIHandler(
            cache_manager=self._cache_manager,
            telegram_utils=self._telegram_utils,
            settings_manager=self._settings_manager,
            event_handlers=self._event_handlers
        )
        
        # Shutdown flag
        self._is_shutting_down = False
        
        # Instance lock for single-instance enforcement
        self._instance_lock = InstanceLock()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle shutdown signals gracefully."""
        if self._is_shutting_down:
            self._logger.info("Force shutdown requested. Exiting immediately.")
            print("\nForce shutdown. Exiting immediately...")
            os._exit(1)  # Force exit on second Ctrl+C
            return
        
        self._is_shutting_down = True
        self._logger.warning("SIGINT (Ctrl+C) received. Initiating graceful shutdown.")
        print("\nShutting down gracefully... (Press Ctrl+C again to force quit)")
        
        # Cancel all running tasks via TaskManager
        try:
            task_manager = get_task_manager()
            # Note: cancel_all is async, but signal handler is sync
            # We'll handle this in graceful_shutdown instead
            self._logger.info("Signal received, will cancel tasks in graceful shutdown")
        except Exception as e:
            self._logger.error(f"Error during signal handler: {e}")
        
        # Exit cleanly
        sys.exit(0)
    
    async def _graceful_shutdown(self, source: str = "unknown") -> None:
        """Perform graceful shutdown tasks."""
        self._logger.info(f"Performing graceful shutdown tasks (source: {source})...")
        
        # Stop analyze queue cleanup task
        try:
            await analyze_queue.stop_cleanup_task()
            self._logger.info(f"Graceful shutdown ({source}): Analyze queue cleanup task stopped")
        except Exception as e:
            self._logger.error(f"Graceful shutdown ({source}): Error stopping analyze queue: {e}")
        
        try:
            # Save settings if not already saved
            if not self._cli_handler.cli_state.settings_saved_on_cli_exit:
                self._logger.info(f"Graceful shutdown ({source}): Saving settings...")
                settings_to_save = self._cli_handler.cli_state.to_settings_dict()
                self._settings_manager.save_user_settings(settings_to_save)
                self._logger.info(f"Graceful shutdown ({source}): Settings saved.")
            else:
                self._logger.info(f"Graceful shutdown ({source}): Settings already saved by CLI exit.")
            
            # Stop monitoring if active
            if (self._client_manager.is_connected() and 
                self._cli_handler.cli_state.is_monitoring_active):
                
                self._logger.info(f"Graceful shutdown ({source}): Stopping event monitoring...")
                
                handler_info = self._cli_handler.cli_state.registered_handler_info
                if handler_info:
                    owner_handler, owner_filter, auth_handler, auth_filters = handler_info
                    
                    try:
                        if owner_handler and owner_filter:
                            self._client_manager.client.remove_event_handler(owner_handler, owner_filter)
                        
                        if auth_handler and auth_filters:
                            for auth_filter in auth_filters:
                                self._client_manager.client.remove_event_handler(auth_handler, auth_filter)
                        
                        self._cli_handler.cli_state.is_monitoring_active = False
                        self._cli_handler.cli_state.registered_handler_info = None
                        
                        self._logger.info(f"Graceful shutdown ({source}): Monitoring handlers removed.")
                    
                    except Exception as e:
                        self._logger.error(f"Graceful shutdown ({source}): Error stopping monitoring: {e}")
                else:
                    self._logger.warning(
                        f"Graceful shutdown ({source}): Monitoring was active but no handler info found."
                    )
                    self._cli_handler.cli_state.is_monitoring_active = False
        
        except Exception as e:
            self._logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
    
    async def run(self) -> None:
        """Run the SakaiBot application."""
        # Acquire instance lock (kills old instances if needed)
        if not self._instance_lock.acquire(force=True):
            self._logger.error("Failed to acquire instance lock")
            print("Error: Could not start bot (another instance may be running)")
            return
        
        try:
            self._logger.info("Starting SakaiBot")
            print(f"Starting SakaiBot v{self._config.APP_VERSION if hasattr(self._config, 'APP_VERSION') else '2.0.0'}...")
            
            # Initialize Telegram client
            client = await self._client_manager.initialize()
            print(f"Signed in as: {(await client.get_me()).first_name}")
            
            # Share client with CLI commands (so monitoring can reuse it)
            from .cli.utils import set_shared_client
            set_shared_client(client, self._client_manager)
            
            # Start analyze queue cleanup task
            await analyze_queue.start_cleanup_task()
            self._logger.info("Analyze queue cleanup task started")
            
            # Hand control to CLI
            self._logger.info("Handing control to CLI Handler...")
            await self._cli_handler.display_main_menu_loop(client)
            
            self._is_shutting_down = True
            self._logger.info("Returned from CLI handler (Option 0 exit)")
        
        except ConfigurationError as e:
            self._logger.error(f"Configuration error: {e}")
            print(f"Configuration Error: {e}")
            sys.exit(1)
        
        except TelegramError as e:
            self._logger.error(f"Telegram error: {e}")
            print(f"Telegram Error: {e}")
            sys.exit(1)
        
        except KeyboardInterrupt:
            self._logger.warning("KeyboardInterrupt caught in main loop")
            if not self._is_shutting_down:
                self._is_shutting_down = True
                await self._graceful_shutdown("KeyboardInterrupt_main")
        
        except Exception as e:
            self._logger.error(f"Unexpected error in main: {e}", exc_info=True)
            print(f"An unexpected error occurred: {e}")
            if not self._is_shutting_down:
                self._is_shutting_down = True
                await self._graceful_shutdown("main_exception")
        
        finally:
            self._logger.info("Main 'finally' block reached")
            
            if not self._is_shutting_down:
                self._is_shutting_down = True
                self._logger.info("Performing final shutdown tasks")
                await self._graceful_shutdown("main_finally")
            
            # Cancel all tracked tasks
            try:
                task_manager = get_task_manager()
                self._logger.info("Cancelling all tracked tasks...")
                await task_manager.cancel_all()
            except Exception as e:
                self._logger.error(f"Error cancelling tasks: {e}", exc_info=True)
            
            # Disconnect client
            if self._client_manager.is_connected():
                print("Disconnecting Telegram client...")
                # Clear shared client reference
                from .cli.utils import clear_shared_client
                clear_shared_client()
                await self._client_manager.disconnect()
            
            # Release instance lock
            self._instance_lock.release()
            
            self._logger.info("SakaiBot has been stopped")
            print("SakaiBot has been stopped.")


async def main() -> None:
    """Main entry point function."""
    try:
        # Setup logging
        setup_logging()
        logger = get_logger("main")
        
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Create and run SakaiBot
        bot = SakaiBot(config)
        await bot.run()
    
    except ConfigurationError as e:
        print(f"CRITICAL: Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        logger = get_logger("main")
        logger.error(f"Critical error in main: {e}", exc_info=True)
        print(f"CRITICAL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except SystemExit:
        print("SakaiBot exited.")
    except KeyboardInterrupt:
        print("\nSakaiBot stopped by user (Ctrl+C).")
    finally:
        print("SakaiBot finished execution.")
