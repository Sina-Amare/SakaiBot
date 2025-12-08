"""Connection health monitoring with auto-recovery for SakaiBot.

Provides:
- Periodic heartbeat checks (every 120 seconds)
- Automatic reconnection with exponential backoff
- Proxy service restart on persistent failures
- Health status logging
"""

import asyncio
import subprocess
from typing import Optional, Callable, Awaitable

from ..utils.logging import get_logger


class ConnectionHealthMonitor:
    """
    Monitors Telegram connection health and handles auto-recovery.
    
    Features:
    - Periodic heartbeat checks via get_me()
    - Automatic reconnection with exponential backoff (5s → 5min cap)
    - Proxy service restart after 3 consecutive Telegram reconnect failures
    - Logs WARNING at 3 failures, CRITICAL at 5+ failures
    """
    
    # Configuration
    HEALTH_CHECK_INTERVAL = 120  # seconds (2 minutes)
    BASE_RETRY_DELAY = 5  # seconds
    MAX_RETRY_DELAY = 300  # 5 minutes cap
    PROXY_RESTART_THRESHOLD = 3  # Restart proxy after this many failures
    
    def __init__(
        self,
        client_manager,
        on_recovery_callback: Optional[Callable[[], Awaitable[None]]] = None
    ):
        """
        Initialize the connection health monitor.
        
        Args:
            client_manager: TelegramClientManager instance
            on_recovery_callback: Optional async callback after successful recovery
        """
        self._client_manager = client_manager
        self._on_recovery_callback = on_recovery_callback
        self._logger = get_logger(self.__class__.__name__)
        
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._consecutive_failures = 0
        self._last_successful_check = None
    
    async def start_monitoring(self) -> None:
        """Start the background health monitoring task."""
        if self._is_running:
            self._logger.warning("Health monitor already running")
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self._logger.info(
            f"Connection health monitor started "
            f"(interval: {self.HEALTH_CHECK_INTERVAL}s)"
        )
    
    async def stop_monitoring(self) -> None:
        """Stop the health monitoring task."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        self._logger.info("Connection health monitor stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop - runs health checks periodically."""
        # Initial delay before first check
        await asyncio.sleep(30)
        
        while self._is_running:
            try:
                is_healthy = await self._health_check()
                
                if is_healthy:
                    self._consecutive_failures = 0
                    self._last_successful_check = asyncio.get_event_loop().time()
                else:
                    self._consecutive_failures += 1
                    await self._handle_failure()
                
                # Wait for next check interval
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in monitoring loop: {e}")
                self._consecutive_failures += 1
                await asyncio.sleep(self.BASE_RETRY_DELAY)
    
    async def _health_check(self) -> bool:
        """
        Perform connection health check via get_me().
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self._client_manager.is_connected():
                self._logger.warning("Client disconnected detected")
                return False
            
            # Try to get user info - this validates the connection
            client = self._client_manager.client
            if client:
                me = await asyncio.wait_for(
                    client.get_me(),
                    timeout=30.0
                )
                if me:
                    self._logger.debug(f"Health check OK: {me.first_name}")
                    return True
            
            return False
            
        except asyncio.TimeoutError:
            self._logger.warning("Health check timed out")
            return False
        except Exception as e:
            self._logger.warning(f"Health check failed: {e}")
            return False
    
    async def _handle_failure(self) -> None:
        """Handle connection failure with appropriate recovery actions."""
        failures = self._consecutive_failures
        
        # Log based on severity
        if failures >= 5:
            self._logger.critical(
                f"Connection health critical: {failures} consecutive failures"
            )
        elif failures >= 3:
            self._logger.warning(
                f"Connection health degraded: {failures} consecutive failures"
            )
        else:
            self._logger.info(
                f"Connection check failed (attempt {failures})"
            )
        
        # Attempt recovery
        recovered = await self._attempt_recovery()
        
        if recovered:
            self._logger.info(
                f"Connection recovered after {failures} failures"
            )
            self._consecutive_failures = 0
            
            # Call recovery callback if provided
            if self._on_recovery_callback:
                try:
                    await self._on_recovery_callback()
                except Exception as e:
                    self._logger.error(f"Recovery callback error: {e}")
    
    async def _attempt_recovery(self) -> bool:
        """
        Attempt to recover connection with exponential backoff.
        
        Returns:
            True if recovery successful, False otherwise
        """
        failures = self._consecutive_failures
        
        # Calculate backoff delay
        delay = min(
            self.BASE_RETRY_DELAY * (2 ** (failures - 1)),
            self.MAX_RETRY_DELAY
        )
        
        self._logger.info(f"Attempting recovery in {delay}s...")
        await asyncio.sleep(delay)
        
        # Try restarting proxy services if we've failed multiple times
        if failures >= self.PROXY_RESTART_THRESHOLD:
            self._logger.warning(
                f"Restarting proxy services after {failures} failures"
            )
            await self._restart_proxy_services()
            await asyncio.sleep(5)  # Give proxy time to restart
        
        # Try to reconnect Telegram client
        try:
            client = self._client_manager.client
            if client:
                if not client.is_connected():
                    self._logger.info("Reconnecting to Telegram...")
                    await client.connect()
                
                # Verify connection
                me = await asyncio.wait_for(
                    client.get_me(),
                    timeout=30.0
                )
                
                if me:
                    self._logger.info(
                        f"Successfully reconnected as {me.first_name}"
                    )
                    return True
            
            return False
            
        except Exception as e:
            self._logger.error(f"Recovery attempt failed: {e}")
            return False
    
    async def _restart_proxy_services(self) -> None:
        """Restart xray and redsocks proxy services."""
        try:
            # Run systemctl restart in a subprocess
            # This works on the VPS where the bot runs
            process = await asyncio.create_subprocess_exec(
                "systemctl", "restart", "xray", "redsocks",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )
            
            if process.returncode == 0:
                self._logger.info("Proxy services restarted successfully")
            else:
                self._logger.warning(
                    f"Proxy restart returned code {process.returncode}: "
                    f"{stderr.decode() if stderr else 'no error'}"
                )
                
        except asyncio.TimeoutError:
            self._logger.error("Proxy restart timed out")
        except FileNotFoundError:
            # Not running on Linux or systemctl not available
            self._logger.debug(
                "systemctl not available - skipping proxy restart"
            )
        except Exception as e:
            self._logger.error(f"Failed to restart proxy: {e}")
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is currently healthy."""
        return self._consecutive_failures == 0
    
    @property
    def consecutive_failures(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures
