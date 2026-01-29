"""Single-instance lock to prevent multiple bot instances."""

import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)


class InstanceLock:
    """Ensures only one bot instance runs at a time.
    
    Uses a PID lock file to detect and terminate existing instances.
    """
    
    def __init__(self, lock_file: str = "data/.sakaibot.lock"):
        """Initialize the instance lock.
        
        Args:
            lock_file: Path to the lock file (default: data/.sakaibot.lock)
        """
        self.lock_file = Path(lock_file)
        self.current_pid = os.getpid()
        self._acquired = False
        
        # Ensure data directory exists
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    def acquire(self, force: bool = True) -> bool:
        """Acquire the instance lock.
        
        Args:
            force: If True, kill existing instance. If False, fail if locked.
        
        Returns:
            True if lock acquired, False otherwise
        """
        if self._acquired:
            logger.debug("Lock already acquired by this process")
            return True
        
        # Check if lock file exists
        if self.lock_file.exists():
            try:
                old_pid_str = self.lock_file.read_text().strip()
                old_pid = int(old_pid_str)
                
                # Check if process is still running
                if self._is_process_running(old_pid):
                    if force:
                        logger.info(f"Found running instance (PID: {old_pid}), terminating...")
                        self._kill_process(old_pid)
                        logger.info(f"Terminated old instance (PID: {old_pid})")
                    else:
                        logger.error(f"Another instance is running (PID: {old_pid})")
                        return False
                else:
                    logger.info(f"Found stale lock file (PID: {old_pid}), cleaning up")
            
            except (ValueError, OSError) as e:
                logger.warning(f"Error reading lock file: {e}, removing it")
        
        # Write our PID to lock file
        try:
            self.lock_file.write_text(str(self.current_pid))
            self._acquired = True
            logger.info(f"Instance lock acquired (PID: {self.current_pid})")
            return True
        except OSError as e:
            logger.error(f"Failed to write lock file: {e}")
            return False
    
    def release(self) -> None:
        """Release the instance lock."""
        if not self._acquired:
            return
        
        try:
            if self.lock_file.exists():
                # Verify it's our lock file before deleting
                pid_in_file = int(self.lock_file.read_text().strip())
                if pid_in_file == self.current_pid:
                    self.lock_file.unlink()
                    logger.info(f"Instance lock released (PID: {self.current_pid})")
                else:
                    logger.warning(
                        f"Lock file PID mismatch: expected {self.current_pid}, "
                        f"found {pid_in_file}"
                    )
            self._acquired = False
        except (OSError, ValueError) as e:
            logger.error(f"Error releasing lock: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running.
        
        Args:
            pid: Process ID to check
        
        Returns:
            True if process is running, False otherwise
        """
        try:
            # Send signal 0 to check if process exists
            # This works on both Windows and Unix
            if sys.platform == "win32":
                # On Windows, use tasklist
                import subprocess
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                return str(pid) in result.stdout
            else:
                # On Unix, use kill with signal 0
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    
    def _kill_process(self, pid: int) -> None:
        """Terminate a process with given PID.
        
        Args:
            pid: Process ID to terminate
        """
        try:
            if sys.platform == "win32":
                # On Windows, use taskkill
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    check=False,
                    capture_output=True
                )
            else:
                # On Unix, use SIGTERM then SIGKILL if needed
                try:
                    os.kill(pid, signal.SIGTERM)
                    # Give it a moment to terminate gracefully
                    import time
                    time.sleep(1)
                    if self._is_process_running(pid):
                        os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass  # Process already terminated
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False
