"""Tests for async task lifecycle tracking."""

import asyncio
import gc

from src.utils.task_manager import TaskManager


async def test_task_manager_keeps_task_alive_until_completion():
    """Fire-and-forget command tasks need a strong reference while running."""
    manager = TaskManager()
    started = asyncio.Event()
    release = asyncio.Event()

    async def worker():
        started.set()
        await release.wait()

    manager.create_task(worker())
    await asyncio.wait_for(started.wait(), timeout=1)

    # The caller deliberately keeps no task reference. The manager must.
    gc.collect()
    assert manager.get_active_task_count() == 1

    release.set()
    for _ in range(20):
        if manager.get_active_task_count() == 0:
            break
        await asyncio.sleep(0.01)

    assert manager.get_active_task_count() == 0
