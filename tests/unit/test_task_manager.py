"""Unit tests for task manager."""

import unittest
import asyncio

from src.utils.task_manager import TaskManager, get_task_manager


class TestTaskManager(unittest.IsolatedAsyncioTestCase):
    """Test TaskManager class."""
    
    async def test_create_task(self):
        """Test task creation and tracking."""
        manager = TaskManager()
        
        async def dummy_task():
            await asyncio.sleep(0.01)
            return "done"
        
        task = manager.create_task(dummy_task(), name="test_task")
        self.assertIsNotNone(task)
        self.assertEqual(task.get_name(), "test_task")
        
        # Wait for task to complete
        await task
        self.assertTrue(task.done())
    
    async def test_cancel_all(self):
        """Test cancelling all tasks."""
        manager = TaskManager()
        
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                pass
        
        task1 = manager.create_task(long_task(), name="task1")
        task2 = manager.create_task(long_task(), name="task2")
        
        # Cancel all tasks
        await manager.cancel_all()
        
        # Tasks should be cancelled
        self.assertTrue(task1.cancelled() or task1.done())
        self.assertTrue(task2.cancelled() or task2.done())
    
    async def test_cancel_all_empty(self):
        """Test cancelling when no tasks exist."""
        manager = TaskManager()
        # Should not raise
        await manager.cancel_all()
    
    def test_get_task_manager_singleton(self):
        """Test singleton pattern."""
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        self.assertIs(manager1, manager2)


if __name__ == "__main__":
    unittest.main()

