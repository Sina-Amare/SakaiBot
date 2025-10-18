"""Telegram user verification module for SakaiBot."""

import asyncio
from typing import Optional, Dict, Any, Union
from telethon import TelegramClient
from telethon import functions
from telethon.tl.types import User
from telethon.errors import (
    FloodWaitError, 
    RPCError, 
    UsernameInvalidError, 
    PeerIdInvalidError
)

from ..utils.logging import get_logger
from ..core.exceptions import TelegramError


class TelegramUserVerifier:
    """Handles verification of Telegram users by fetching their information directly from Telegram API."""
    
    def __init__(self, client: TelegramClient) -> None:
        """Initialize the user verifier with a Telegram client."""
        self._client = client
        self._logger = get_logger(self.__class__.__name__)
    
    async def verify_user_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Verify a user by their identifier (username, ID, or name) by fetching directly from Telegram.
        
        Args:
            identifier: User identifier which can be a username (with or without @), user ID, or name
            
        Returns:
            Dictionary containing user information if found, None otherwise
        """
        self._logger.info(f"Verifying user by identifier: {identifier}")
        
        try:
            # Try to parse as integer for ID search
            try:
                user_id = int(identifier)
                return await self._fetch_user_by_id(user_id)
            except ValueError:
                pass
            
            # Handle username with or without @ prefix
            if identifier.startswith('@'):
                username = identifier[1:]
            else:
                username = identifier
            
            # Try fetching by username first
            user_info = await self._fetch_user_by_username(username)
            if user_info:
                return user_info
            
            # If username search failed, try searching by name
            # This is a more complex search and may require additional implementation
            return await self._search_user_by_name(identifier)
            
        except FloodWaitError as e:
            self._logger.warning(f"Rate limited by Telegram API: {e.seconds} seconds")
            raise TelegramError(f"Rate limited by Telegram API: {e.seconds} seconds")
        except (UsernameInvalidError, PeerIdInvalidError) as e:
            self._logger.warning(f"Invalid user identifier: {identifier} - {e}")
            return None
        except RPCError as e:
            self._logger.error(f"Telegram RPC error during user verification: {e}")
            raise TelegramError(f"Telegram API error: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error during user verification: {e}", exc_info=True)
            raise TelegramError(f"Unexpected error during user verification: {e}")
    
    async def _fetch_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user information by user ID."""
        self._logger.debug(f"Fetching user by ID: {user_id}")
        
        try:
            entity = await self._client.get_entity(user_id)
            if isinstance(entity, User) and not entity.deleted:
                return self._format_user_info(entity)
            else:
                self._logger.info(f"User with ID {user_id} not found or is deleted")
                return None
        except (ValueError, TypeError):
            # User ID not found in Telegram
            self._logger.info(f"User with ID {user_id} not found in Telegram")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching user by ID {user_id}: {e}", exc_info=True)
            raise
    
    async def _fetch_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user information by username."""
        self._logger.debug(f"Fetching user by username: {username}")
        
        try:
            entity = await self._client.get_entity(username)
            if isinstance(entity, User) and not entity.deleted:
                return self._format_user_info(entity)
            else:
                self._logger.info(f"User with username {username} not found or is deleted")
                return None
        except (ValueError, TypeError):
            # Username not found in Telegram
            self._logger.info(f"User with username {username} not found in Telegram")
            return None
        except Exception as e:
            self._logger.error(f"Error fetching user by username {username}: {e}", exc_info=True)
            raise
    
    async def _search_user_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for user by name - this is limited by Telegram API but we can try contacts."""
        self._logger.debug(f"Searching user by name: {name}")
        
        try:
            # First, try to search in the user's contacts
            result = await self._client(functions.contacts.SearchRequest(q=name, limit=10))
            if result and hasattr(result, 'users'):
                for user in result.users:
                    if isinstance(user, User) and not user.deleted:
                        # Check if the name matches closely enough
                        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip().lower()
                        if name.lower() in full_name or full_name in name.lower():
                            return self._format_user_info(user)
            
            # If not found in contacts, we can't search by name across all of Telegram
            # due to privacy restrictions
            self._logger.info(f"No user found matching name: {name}")
            return None
        except Exception as e:
            self._logger.error(f"Error searching user by name {name}: {e}", exc_info=True)
            raise TelegramError(f"Error searching user by name: {e}")
    
    def _format_user_info(self, user: User) -> Dict[str, Any]:
        """Format user information into a standardized dictionary."""
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        display_name = (first_name + " " + last_name).strip()
        username = user.username
        
        user_info = {
            'id': user.id,
            'display_name': display_name,
            'username': f"@{username}" if username else None,
            'first_name': first_name,
            'last_name': last_name,
            'is_bot': user.bot if hasattr(user, 'bot') else False,
            'is_verified': user.verified if hasattr(user, 'verified') else False,
            'is_premium': user.premium if hasattr(user, 'premium') else False,
        }
        
        self._logger.debug(f"Formatted user info for ID {user.id}: {user_info}")
        return user_info
    
    async def batch_verify_users(self, identifiers: list[str]) -> list[Dict[str, Any]]:
        """Verify multiple users at once."""
        self._logger.info(f"Batch verifying {len(identifiers)} users")
        results = []
        
        for identifier in identifiers:
            try:
                user_info = await self.verify_user_by_identifier(identifier)
                if user_info:
                    results.append(user_info)
            except Exception as e:
                self._logger.error(f"Error verifying user {identifier}: {e}", exc_info=True)
                # Continue with other users even if one fails
        
        self._logger.info(f"Batch verification completed. Found {len(results)} valid users")
        return results
