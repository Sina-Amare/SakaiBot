"""Telegram client management for SakaiBot."""

import asyncio
from typing import Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from ..core.config import Config
from ..core.constants import SYSTEM_VERSION
from ..core.exceptions import TelegramError
from ..utils.logging import get_logger


class TelegramClientManager:
    """Manages Telegram client connection and authentication."""
    
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[TelegramClient] = None
    
    @property
    def client(self) -> Optional[TelegramClient]:
        """Get the Telegram client instance."""
        return self._client
    
    async def initialize(self) -> TelegramClient:
        """Initialize and connect the Telegram client."""
        try:
            # Ensure session file is in data directory
            from pathlib import Path
            session_dir = Path("data")
            session_dir.mkdir(parents=True, exist_ok=True)
            session_path = session_dir / self._config.telegram_session_name
            
            self._client = TelegramClient(
                session=str(session_path),
                api_id=self._config.telegram_api_id,
                api_hash=self._config.telegram_api_hash,
                system_version=SYSTEM_VERSION
            )
            
            self._logger.info(f"Initializing Telegram client with session: '{session_path}.session'")
            await self._client.connect()
            
            if not await self._client.is_user_authorized():
                await self._authenticate()
            
            # Get user info
            me = await self._client.get_me()
            if me:
                self._logger.info(f"Signed in as: {me.first_name} (@{me.username or 'N/A'})")
                return self._client
            else:
                raise TelegramError("Could not get user info after authentication")
        
        except KeyboardInterrupt:
            self._logger.info("Authentication cancelled by user")
            if self._client and self._client.is_connected():
                await self._client.disconnect()
            raise
        except Exception as e:
            if isinstance(e, TelegramError):
                raise
            raise TelegramError(f"Failed to initialize Telegram client: {e}")
    
    async def _authenticate(self) -> None:
        """Handle Telegram authentication flow."""
        if not self._client:
            raise TelegramError("Client not initialized")
        
        self._logger.info(f"User not authorized. Sending code to {self._config.telegram_phone_number}")
        
        try:
            await self._client.send_code_request(self._config.telegram_phone_number)
            
            while True:
                code = await self._get_user_input('Enter code: ')
                try:
                    await self._client.sign_in(self._config.telegram_phone_number, code)
                    break
                except SessionPasswordNeededError:
                    self._logger.info("2FA enabled")
                    while True:
                        password = await self._get_user_input('Enter 2FA password: ')
                        try:
                            await self._client.sign_in(password=password)
                            return
                        except Exception as e:
                            self._logger.error(f"2FA login failed: {e}")
                            print(f"2FA login failed: {e}. Try again.")
                except Exception as e:
                    self._logger.error(f"Code verification failed: {e}")
                    print(f"Code verification failed: {e}. Try again.")
        
        except Exception as e:
            raise TelegramError(f"Authentication failed: {e}")
    
    async def _get_user_input(self, prompt: str) -> str:
        """Get user input asynchronously."""
        import sys
        import threading
        
        result = []
        exception = []
        
        def read_input():
            try:
                # Use regular input but in a thread
                user_input = input(prompt)
                result.append(user_input)
            except (KeyboardInterrupt, EOFError) as e:
                exception.append(e)
            except Exception as e:
                exception.append(e)
        
        # Start input thread
        input_thread = threading.Thread(target=read_input, daemon=True)
        input_thread.start()
        
        # Wait for input with periodic checks for shutdown
        while input_thread.is_alive():
            try:
                await asyncio.sleep(0.1)  # Check every 100ms
            except asyncio.CancelledError:
                self._logger.info("Input cancelled")
                raise KeyboardInterrupt("User cancelled authentication")
        
        # Check results
        if exception:
            if isinstance(exception[0], (KeyboardInterrupt, EOFError)):
                raise KeyboardInterrupt("User cancelled authentication")
            raise exception[0]
        
        if result:
            return result[0]
        
        raise EOFError("No input received")
    
    async def disconnect(self) -> None:
        """Disconnect the Telegram client."""
        if self._client and self._client.is_connected():
            self._logger.info("Disconnecting Telegram client")
            await self._client.disconnect()
            self._client = None
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None and self._client.is_connected()
