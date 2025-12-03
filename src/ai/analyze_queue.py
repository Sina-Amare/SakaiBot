"""
AI Command Queue System for rate-limiting expensive LLM operations.

Prevents concurrent AI requests on the same chat by implementing
a chat-level lock system with timeout protection.

Supported Commands:
- /analyze (all modes: fun, romance, general)
- /prompt
- /tellme

Key Features:
- One AI command per chat at a time
- Immediate rejection (no queueing)
- 5-minute timeout auto-release
- Background cleanup task
- Graceful shutdown support

Note: Queue state is in-memory and doesn't persist across bot restarts.
On restart, all locks are cleared and users with in-progress requests
won't receive results. This is acceptable to keep implementation simple.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from ..utils.logging import get_logger


logger = get_logger(__name__)

# Configuration
TIMEOUT_SECONDS = 300  # 5 minutes
CLEANUP_INTERVAL = 60  # 1 minute

# Commands that should be queue-protected (use pro model, expensive)
PROTECTED_COMMANDS = {"analyze", "prompt", "tellme"}


@dataclass
class AnalyzeRequest:
    """Represents an active AI command request."""
    chat_id: int
    user_id: int
    command_type: str  # analyze, prompt, tellme
    analysis_type: str  # For analyze: fun/romance/general; for others: "default"
    started_at: datetime
    request_id: str


class AnalyzeQueue:
    """
    Manages AI command execution to prevent concurrent operations per chat.
    
    Uses a chat-level lock system where only one AI command can run per chat
    at a time. New requests are rejected immediately with a friendly message.
    
    Locks automatically release after TIMEOUT_SECONDS to prevent stuck states.
    
    Supports /analyze, /prompt, and /tellme commands.
    """
    
    def __init__(self):
        """Initialize the AI command queue."""
        self._active: Dict[int, AnalyzeRequest] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._logger = logger
        
    async def start_cleanup_task(self):
        """
        Start background cleanup task.
        
        Should be called once on bot startup. The task runs every
        CLEANUP_INTERVAL seconds to clean up timed-out locks.
        """
        if self._cleanup_task is not None:
            self._logger.warning("Cleanup task already running")
            return
            
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._logger.info("Started analyze queue cleanup task")
        
    async def stop_cleanup_task(self):
        """
        Stop cleanup task gracefully.
        
        Should be called on bot shutdown. Cancels the background task
        and waits for it to finish.
        """
        if self._cleanup_task is None:
            return
            
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        self._cleanup_task = None
        self._logger.info("Stopped analyze queue cleanup task")
        
    async def try_start_analysis(
        self,
        chat_id: int,
        user_id: int,
        analysis_type: str,
        command_type: str = "analyze"
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to start an AI command for a chat.
        
        Args:
            chat_id: Telegram chat ID
            user_id: User who requested the command
            analysis_type: Type of analysis (fun, romance, general) or "default" for other commands
            command_type: Type of command (analyze, prompt, tellme)
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            If success is False, error_message contains HTML-formatted
            message to send to user.
        """
        async with self._lock:
            # Check if chat already has active AI command
            if chat_id in self._active:
                active = self._active[chat_id]
                self._logger.info(
                    f"Rejected {command_type} request for chat {chat_id} "
                    f"(active: {active.request_id}, command: {active.command_type})"
                )
                
                # Dynamic error message based on what's running
                active_cmd = active.command_type.title()
                requested_cmd = command_type.title()
                
                error_msg = (
                    f"⏳ <b>AI Command In Progress</b>\n\n"
                    f"A <b>{active_cmd}</b> command is currently processing for this chat.\n\n"
                    f"<i>Please wait for it to complete before starting a new {requested_cmd} request.</i>"
                )
                return False, error_msg
                
            # Create new request
            request = AnalyzeRequest(
                chat_id=chat_id,
                user_id=user_id,
                command_type=command_type,
                analysis_type=analysis_type,
                started_at=datetime.now(),
                request_id=f"{command_type}_{uuid.uuid4().hex[:8]}"
            )
            
            self._active[chat_id] = request
            self._logger.info(
                f"Started {command_type} {request.request_id} for chat {chat_id} "
                f"(analysis_type: {analysis_type})"
            )
            
            return True, None
            
    async def complete_analysis(self, chat_id: int):
        """
        Mark analysis as complete and release lock.
        
        Args:
            chat_id: Telegram chat ID
        """
        async with self._lock:
            if chat_id in self._active:
                request = self._active.pop(chat_id)
                duration = (datetime.now() - request.started_at).total_seconds()
                self._logger.info(
                    f"Completed analysis {request.request_id} for chat {chat_id} "
                    f"(duration: {duration:.1f}s)"
                )
            else:
                self._logger.warning(
                    f"Attempted to complete non-existent analysis for chat {chat_id}"
                )
                
    async def fail_analysis(self, chat_id: int):
        """
        Mark analysis as failed and release lock.
        
        Args:
            chat_id: Telegram chat ID
        """
        async with self._lock:
            if chat_id in self._active:
                request = self._active.pop(chat_id)
                duration = (datetime.now() - request.started_at).total_seconds()
                self._logger.warning(
                    f"Failed analysis {request.request_id} for chat {chat_id} "
                    f"(duration: {duration:.1f}s)"
                )
            else:
                self._logger.warning(
                    f"Attempted to fail non-existent analysis for chat {chat_id}"
                )
                
    def get_active_analysis(self, chat_id: int) -> Optional[AnalyzeRequest]:
        """
        Get currently active analysis for a chat.
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            AnalyzeRequest if active, None otherwise
        """
        return self._active.get(chat_id)
        
    async def _cleanup_loop(self):
        """
        Background task to clean up timed-out locks.
        
        Runs every CLEANUP_INTERVAL seconds and removes any analyses
        that have been running longer than TIMEOUT_SECONDS.
        
        Handles errors gracefully to avoid crashing the bot.
        """
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                await self._cleanup_stale_locks()
            except asyncio.CancelledError:
                self._logger.debug("Cleanup loop cancelled")
                break
            except Exception as e:
                self._logger.error(
                    f"Error in cleanup loop: {e}",
                    exc_info=True
                )
                # Continue running despite errors
                
    async def _cleanup_stale_locks(self):
        """Remove analyses that have exceeded timeout."""
        now = datetime.now()
        timeout_threshold = now - timedelta(seconds=TIMEOUT_SECONDS)
        
        async with self._lock:
            stale_chats = [
                chat_id
                for chat_id, request in self._active.items()
                if request.started_at < timeout_threshold
            ]
            
            for chat_id in stale_chats:
                request = self._active.pop(chat_id)
                duration = (now - request.started_at).total_seconds()
                self._logger.warning(
                    f"Cleaned up stale analysis {request.request_id} "
                    f"for chat {chat_id} (duration: {duration:.1f}s)"
                )
                
            if stale_chats:
                self._logger.info(
                    f"Cleanup removed {len(stale_chats)} stale lock(s)"
                )


# Global queue instance
analyze_queue = AnalyzeQueue()
