# -*- coding: utf-8 -*-
"""
Telegram client management for SakaiBot.

This module handles Telegram client initialization, authentication,
and session management with proper error handling and logging.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthKeyDuplicatedError
)

from ..core.exceptions import (
    TelegramError,
    AuthenticationError,
    SessionError,
    ConfigurationError,
    NetworkError,
    TimeoutError as SakaiBotTimeoutError
)
from ..core.config import Settings
from ..core.constants import (
    DEFAULT_SESSION_NAME,
    TELEGRAM_FLOOD_WAIT_MIN,
    TELEGRAM_FLOOD_WAIT_MAX
)


logger = logging.getLogger(__name__)


class SakaiBotTelegramClient:
    """
    Enhanced Telegram client wrapper with robust error handling,
    session management, and authentication flow.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Telegram client wrapper.
        
        Args:
            settings: Application settings containing Telegram configuration
            
        Raises:
            ConfigurationError: If required settings are missing
        """
        self._settings = settings
        self._client: Optional[TelegramClient] = None
        self._is_connected = False
        self._is_authenticated = False
        self._session_path: Optional[Path] = None
        self._event_handlers: List[Any] = []
        
        # Validate required settings
        self._validate_settings()
        
        # Initialize client
        self._initialize_client()
    
    def _validate_settings(self) -> None:
        """Validate required Telegram settings."""
        telegram_config = self._settings.telegram
        
        if not telegram_config.api_id:
            raise ConfigurationError("Telegram API ID is required")
        
        if not telegram_config.api_hash.get_secret_value():
            raise ConfigurationError("Telegram API Hash is required")
        
        if not telegram_config.phone_number:
            raise ConfigurationError("Phone number is required")
    
    def _initialize_client(self) -> None:
        """Initialize the Telegram client instance."""
        telegram_config = self._settings.telegram
        session_dir = self._settings.paths.session_dir
        
        # Set up session path
        session_name = telegram_config.session_name or DEFAULT_SESSION_NAME
        self._session_path = session_dir / f"{session_name}.session"
        
        # Create client
        self._client = TelegramClient(
            str(self._session_path.with_suffix('')),  # Remove .session extension
            telegram_config.api_id,
            telegram_config.api_hash.get_secret_value()
        )
        
        logger.info(f"Initialized Telegram client with session: {self._session_path}")
    
    @property
    def client(self) -> TelegramClient:
        """Get the underlying Telegram client."""
        if not self._client:
            raise SessionError("Telegram client not initialized")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._is_authenticated
    
    async def connect(self) -> None:
        """
        Connect to Telegram servers.
        
        Raises:
            NetworkError: If connection fails
            TelegramError: If client is not initialized
        """
        if not self._client:
            raise TelegramError("Client not initialized")
        
        try:
            logger.info("Connecting to Telegram servers...")
            await self._client.connect()
            self._is_connected = True
            logger.info("Successfully connected to Telegram")
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}", exc_info=True)
            raise NetworkError(f"Failed to connect to Telegram: {e}") from e
    
    async def authenticate(self) -> None:
        """
        Authenticate with Telegram.
        
        Raises:
            AuthenticationError: If authentication fails
            SessionError: If session is invalid
        """
        if not self._client:
            raise TelegramError("Client not initialized")
        
        if not self._is_connected:
            await self.connect()
        
        try:
            # Check if already authenticated
            if await self._client.is_user_authorized():
                logger.info("Already authenticated with existing session")
                self._is_authenticated = True
                return
            
            # Start authentication process
            phone = self._settings.telegram.phone_number
            logger.info(f"Starting authentication for phone: {phone[:4]}****{phone[-2:]}")
            
            await self._client.send_code_request(phone)
            logger.info("Verification code sent. Please check your Telegram app.")
            
            # Note: In a real implementation, you'd need to handle code input
            # This is a simplified version for the refactoring example
            raise AuthenticationError(
                "Interactive authentication required. "
                "Please run the bot interactively to complete authentication."
            )
            
        except SessionPasswordNeededError:
            raise AuthenticationError(
                "Two-factor authentication is enabled. "
                "Please provide your password through the interactive CLI."
            )
        except PhoneNumberInvalidError as e:
            raise AuthenticationError(f"Invalid phone number: {e}") from e
        except PhoneCodeInvalidError as e:
            raise AuthenticationError(f"Invalid verification code: {e}") from e
        except FloodWaitError as e:
            wait_time = min(e.seconds, TELEGRAM_FLOOD_WAIT_MAX)
            raise AuthenticationError(
                f"Rate limited by Telegram. Please wait {wait_time} seconds."
            ) from e
        except Exception as e:
            logger.error(f"Authentication failed: {e}", exc_info=True)
            raise AuthenticationError(f"Authentication failed: {e}") from e
    
    async def disconnect(self) -> None:
        """
        Disconnect from Telegram servers.
        
        Raises:
            TelegramError: If disconnection fails
        """
        if not self._client:
            return
        
        try:
            logger.info("Disconnecting from Telegram...")
            await self._client.disconnect()
            self._is_connected = False
            self._is_authenticated = False
            logger.info("Successfully disconnected from Telegram")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
            raise TelegramError(f"Failed to disconnect: {e}") from e
    
    def add_event_handler(
        self,
        handler,
        event_type=events.NewMessage,
        **kwargs
    ) -> None:
        """
        Add an event handler to the client.
        
        Args:
            handler: Event handler function
            event_type: Type of event to handle
            **kwargs: Additional event parameters
        """
        if not self._client:
            raise TelegramError("Client not initialized")
        
        try:
            self._client.add_event_handler(handler, event_type(**kwargs))
            self._event_handlers.append({
                'handler': handler,
                'event_type': event_type,
                'kwargs': kwargs
            })
            logger.debug(f"Added event handler: {handler.__name__}")
        except Exception as e:
            logger.error(f"Failed to add event handler: {e}", exc_info=True)
            raise TelegramError(f"Failed to add event handler: {e}") from e
    
    def remove_event_handler(self, handler) -> None:
        """
        Remove an event handler from the client.
        
        Args:
            handler: Event handler function to remove
        """
        if not self._client:
            raise TelegramError("Client not initialized")
        
        try:
            self._client.remove_event_handler(handler)
            # Remove from our tracking list
            self._event_handlers = [
                h for h in self._event_handlers 
                if h['handler'] != handler
            ]
            logger.debug(f"Removed event handler: {handler.__name__}")
        except Exception as e:
            logger.error(f"Failed to remove event handler: {e}", exc_info=True)
            raise TelegramError(f"Failed to remove event handler: {e}") from e
    
    async def get_me(self) -> Any:
        """
        Get information about the current user.
        
        Returns:
            User information
            
        Raises:
            AuthenticationError: If not authenticated
            TelegramError: If request fails
        """
        if not self._is_authenticated:
            raise AuthenticationError("Not authenticated")
        
        try:
            return await self._client.get_me()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}", exc_info=True)
            raise TelegramError(f"Failed to get user info: {e}") from e
    
    async def start(self) -> None:
        """
        Start the client (connect and authenticate).
        
        Raises:
            TelegramError: If start process fails
        """
        try:
            await self.connect()
            await self.authenticate()
            logger.info("Telegram client started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}", exc_info=True)
            raise TelegramError(f"Failed to start client: {e}") from e
    
    async def run_until_disconnected(self) -> None:
        """
        Run the client until disconnected.
        
        Raises:
            TelegramError: If client fails to run
        """
        if not self._client:
            raise TelegramError("Client not initialized")
        
        if not self._is_connected:
            await self.start()
        
        try:
            logger.info("Starting Telegram client event loop...")
            await self._client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Client run failed: {e}", exc_info=True)
            raise TelegramError(f"Client run failed: {e}") from e
        finally:
            self._is_connected = False
            self._is_authenticated = False
    
    async def __aenter__(self) -> "SakaiBotTelegramClient":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    def __del__(self) -> None:
        """Cleanup on deletion."""
        if self._client and self._is_connected:
            # Note: Can't await in __del__, so we just log
            logger.warning("TelegramClient was not properly disconnected")


def create_telegram_client(settings: Settings) -> SakaiBotTelegramClient:
    """
    Factory function to create a configured Telegram client.
    
    Args:
        settings: Application settings
        
    Returns:
        SakaiBotTelegramClient: Configured client instance
        
    Raises:
        ConfigurationError: If settings are invalid
    """
    try:
        client = SakaiBotTelegramClient(settings)
        logger.info("Created Telegram client instance")
        return client
    except Exception as e:
        logger.error(f"Failed to create Telegram client: {e}", exc_info=True)
        raise ConfigurationError(f"Failed to create Telegram client: {e}") from e
