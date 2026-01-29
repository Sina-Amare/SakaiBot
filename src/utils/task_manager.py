"""Task manager for tracking and managing async tasks."""

import asyncio
from typing import Set, Optional
from weakref import WeakSet

from .logging import get_logger

logger = get_logger(__name__)


class TaskManager:
    """Manages async task lifecycle and provides centralized task tracking."""
    
    def __init__(self):
        """Initialize TaskManager."""
        # Use WeakSet to avoid keeping references to completed tasks
        self._tasks: WeakSet[asyncio.Task] = WeakSet()
        self._logger = get_logger(self.__class__.__name__)
    
    def create_task(self, coro) -> asyncio.Task:
        """
        Create and track an async task.
        
        Args:
            coro: Coroutine to run as a task
            
        Returns:
            Created asyncio.Task instance
        """
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        
        # Add callback to remove task from tracking when done
        task.add_done_callback(self._on_task_done)
        
        self._logger.debug(f"Created and tracking task: {task.get_name()}")
        return task
    
    def _on_task_done(self, task: asyncio.Task) -> None:
        """
        Callback when a task completes.
        
        Args:
            task: Completed task
        """
        try:
            # Check if task had an exception
            if task.exception():
                self._logger.warning(
                    f"Task {task.get_name()} completed with exception: {task.exception()}",
                    exc_info=task.exception()
                )
            else:
                self._logger.debug(f"Task {task.get_name()} completed successfully")
        except Exception as e:
            self._logger.error(f"Error in task done callback: {e}", exc_info=True)
        finally:
            # Task will be automatically removed from WeakSet when no longer referenced
            pass
    
    async def cancel_all(self) -> None:
        """
        Cancel all tracked tasks gracefully.
        
        This should be called during shutdown to ensure all tasks are properly cancelled.
        """
        # Get current tasks (WeakSet doesn't support iteration directly, so we get all tasks)
        current_tasks = [task for task in self._tasks if not task.done()]
        
        if not current_tasks:
            self._logger.debug("No active tasks to cancel")
            return
        
        self._logger.info(f"Cancelling {len(current_tasks)} active tasks")
        
        # Cancel all tasks
        for task in current_tasks:
            if not task.done():
                task.cancel()
                self._logger.debug(f"Cancelled task: {task.get_name()}")
        
        # Wait for all tasks to finish cancellation
        if current_tasks:
            try:
                await asyncio.gather(*current_tasks, return_exceptions=True)
                self._logger.info("All tasks cancelled successfully")
            except Exception as e:
                self._logger.error(f"Error during task cancellation: {e}", exc_info=True)
    
    def get_active_task_count(self) -> int:
        """
        Get the number of active (not done) tasks.
        
        Returns:
            Number of active tasks
        """
        return len([task for task in self._tasks if not task.done()])
    
    def get_all_tasks(self) -> Set[asyncio.Task]:
        """
        Get all tracked tasks (both active and completed).
        
        Returns:
            Set of all tracked tasks
        """
        # Convert WeakSet to regular set for return
        return set(self._tasks)


# Global task manager instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """
    Get the global TaskManager instance.
    
    Returns:
        Global TaskManager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager

