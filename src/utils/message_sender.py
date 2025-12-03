"""Enterprise-grade message sending utility with retry, pagination, and markdown support."""

import asyncio
from typing import List, Optional, Tuple
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import Message

from ..core.constants import MAX_MESSAGE_LENGTH
from ..utils.logging import get_logger
from ..utils.helpers import split_message
from ..utils.retry import retry_with_backoff
from ..utils.rtl_fixer import ensure_rtl_safe


class MessageSender:
    """Handles reliable message sending with pagination, retry, and markdown support."""
    
    # Reserve space for markdown formatting overhead
    MARKDOWN_OVERHEAD = 200
    # Reserve space for pagination indicator (e.g., " (1/3)")
    PAGINATION_OVERHEAD = 20
    
    def __init__(self, client: TelegramClient):
        """
        Initialize MessageSender.
        
        Args:
            client: Telegram client instance
        """
        self._client = client
        self._logger = get_logger(self.__class__.__name__)
    
    async def send_message_safe(
        self,
        chat_id: int,
        text: str,
        reply_to: Optional[int] = None,
        parse_mode: Optional[str] = None,
        max_retries: int = 3,
        skip_rtl_fix: bool = False
    ) -> Optional[Message]:
        """
        Send a message with retry logic and automatic RTL fixing.
        
        Args:
            chat_id: Target chat ID
            text: Message text
            reply_to: Reply to message ID
            parse_mode: Parse mode ('md' or 'html')
            max_retries: Maximum retry attempts
            skip_rtl_fix: Skip RTL fix (use when RTL already applied to content)
            
        Returns:
            Sent message or None if failed
        """
        # Apply RTL fix for Persian text (auto-detects Persian) unless skipped
        if not skip_rtl_fix:
            text = ensure_rtl_safe(text)
        
        @retry_with_backoff(max_retries=max_retries, base_delay=1.0)
        async def _send():
            return await self._client.send_message(
                chat_id,
                text,
                reply_to=reply_to,
                parse_mode=parse_mode
            )
        
        try:
            return await _send()
        except Exception as e:
            self._logger.error(f"Failed to send message after {max_retries} retries: {e}")
            return None
    
    async def edit_message_safe(
        self,
        message: Message,
        new_text: str,
        parse_mode: Optional[str] = None,
        max_retries: int = 2
    ) -> bool:
        """
        Edit a message with retry logic and duplicate content handling.
        
        Args:
            message: Message to edit
            new_text: New message text
            parse_mode: Parse mode ('md' or 'html')
            max_retries: Maximum retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        @retry_with_backoff(max_retries=max_retries, base_delay=0.5)
        async def _edit():
            await self._client.edit_message(message, new_text, parse_mode=parse_mode)
            return True
        
        try:
            return await _edit()
        except Exception as e:
            error_str = str(e).lower()
            # Ignore "content not modified" errors - these are expected
            if "content of the message was not modified" in error_str or "message not modified" in error_str:
                return False
            self._logger.debug(f"Could not edit message: {e}")
            return False
    
    def _split_with_pagination(
        self,
        text: str,
        max_length: int = MAX_MESSAGE_LENGTH,
        reserve_for_formatting: int = 0
    ) -> List[Tuple[str, str]]:
        """
        Split text into chunks with pagination indicators.
        
        Args:
            text: Text to split
            max_length: Maximum length per chunk
            reserve_for_formatting: Additional bytes to reserve for formatting
            
        Returns:
            List of tuples: (chunk_text, pagination_suffix)
        """
        # Calculate effective max length
        effective_max = max_length - reserve_for_formatting - self.PAGINATION_OVERHEAD
        
        if len(text) <= effective_max:
            return [(text, "")]
        
        # Split the message
        chunks = split_message(text, max_length=effective_max, reserve_length=0)
        total_chunks = len(chunks)
        
        # Add pagination indicators
        result = []
        for i, chunk in enumerate(chunks, 1):
            if total_chunks > 1:
                pagination = f" ({i}/{total_chunks})"
            else:
                pagination = ""
            result.append((chunk, pagination))
        
        return result
    
    async def send_long_message(
        self,
        chat_id: int,
        text: str,
        reply_to: Optional[int] = None,
        parse_mode: Optional[str] = None,
        edit_message: Optional[Message] = None,
        skip_rtl_fix: bool = False
    ) -> List[Message]:
        """
        Send a long message, splitting if necessary with pagination.
        
        Args:
            chat_id: Target chat ID
            text: Message text (may be long)
            reply_to: Reply to message ID
            parse_mode: Parse mode ('md' or 'html')
            edit_message: Optional message to edit with first chunk
            skip_rtl_fix: Skip RTL fix (use when RTL already applied to content)
            
        Returns:
            List of sent messages
        """
        # Reserve space for markdown formatting if using markdown
        reserve = self.MARKDOWN_OVERHEAD if parse_mode == 'md' else 0
        
        # Split with pagination
        chunks_with_pagination = self._split_with_pagination(
            text,
            max_length=MAX_MESSAGE_LENGTH,
            reserve_for_formatting=reserve
        )
        
        sent_messages = []
        
        for i, (chunk, pagination) in enumerate(chunks_with_pagination):
            full_text = chunk + pagination
            
            if i == 0 and edit_message:
                # Edit existing message with first chunk
                success = await self.edit_message_safe(
                    edit_message,
                    full_text,
                    parse_mode=parse_mode
                )
                if success:
                    sent_messages.append(edit_message)
                else:
                    # If edit failed, send as new message
                    msg = await self.send_message_safe(
                        chat_id,
                        full_text,
                        reply_to=reply_to,
                        parse_mode=parse_mode,
                        skip_rtl_fix=skip_rtl_fix
                    )
                    if msg:
                        sent_messages.append(msg)
            else:
                # Send new message
                msg = await self.send_message_safe(
                    chat_id,
                    full_text,
                    reply_to=reply_to if i == 0 else None,  # Only first chunk replies
                    parse_mode=parse_mode,
                    skip_rtl_fix=skip_rtl_fix
                )
                if msg:
                    sent_messages.append(msg)
            
            # Small delay between messages to avoid rate limiting
            if i < len(chunks_with_pagination) - 1:
                await asyncio.sleep(0.3)
        
        return sent_messages
    
    async def send_with_thinking_message(
        self,
        chat_id: int,
        thinking_text: str,
        response_text: str,
        reply_to: Optional[int] = None,
        parse_mode: Optional[str] = None
    ) -> List[Message]:
        """
        Send a response by editing a thinking message, splitting if necessary.
        
        Args:
            chat_id: Target chat ID
            thinking_text: Initial "thinking" message text
            response_text: Final response text
            reply_to: Reply to message ID
            parse_mode: Parse mode ('md' or 'html')
            
        Returns:
            List of sent messages (including edited thinking message)
        """
        # Send thinking message
        thinking_msg = await self.send_message_safe(
            chat_id,
            thinking_text,
            reply_to=reply_to
        )
        
        if not thinking_msg:
            # If thinking message failed, just send response directly
            return await self.send_long_message(
                chat_id,
                response_text,
                reply_to=reply_to,
                parse_mode=parse_mode
            )
        
        # Send response by editing thinking message and splitting if needed
        return await self.send_long_message(
            chat_id,
            response_text,
            reply_to=reply_to,
            parse_mode=parse_mode,
            edit_message=thinking_msg
        )

