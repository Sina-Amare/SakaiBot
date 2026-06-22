"""Run uvicorn on the SAME asyncio loop as the connected Telethon client.

``loop="none"`` is critical: it tells uvicorn to use the already-running loop
(where Telethon lives) instead of creating/owning one. Telethon is not
thread-safe, so everything must stay on this single loop.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import uvicorn

from ..utils.logging import get_logger
from .app import create_app

logger = get_logger(__name__)


@dataclass
class PanelHandle:
    server: uvicorn.Server
    task: asyncio.Task

    async def stop(self) -> None:
        self.server.should_exit = True
        try:
            await asyncio.wait_for(self.task, timeout=6)
        except asyncio.TimeoutError:
            logger.warning("Panel did not stop within timeout")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Panel stop error: %s", exc)


async def start_panel(state: Any) -> PanelHandle:
    """Build the app and start serving it on the current loop. Non-blocking."""
    app = create_app(state)
    cfg = state.panel_config

    uconfig = uvicorn.Config(
        app,
        host=cfg.host,            # PanelConfig already enforced loopback-only
        port=cfg.port,
        loop="none",              # use the running Telethon loop
        lifespan="on",
        log_level="warning",
        access_log=False,
        timeout_graceful_shutdown=5,
    )
    server = uvicorn.Server(uconfig)
    # The bot owns SIGINT; uvicorn must not install its own handlers.
    server.install_signal_handlers = lambda: None

    task = asyncio.create_task(server.serve(), name="panel-uvicorn")

    # Give uvicorn a moment to bind so we can log a clean URL (or fail fast).
    for _ in range(60):
        if getattr(server, "started", False) or task.done():
            break
        await asyncio.sleep(0.05)
    if task.done() and task.exception():
        raise task.exception()  # surface bind errors (e.g. port in use)

    logger.info("Control panel listening on http://%s:%s", cfg.host, cfg.port)
    return PanelHandle(server=server, task=task)
