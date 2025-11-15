"""Telegram-related modules for SakaiBot."""

from .client import TelegramClientManager
from .utils import TelegramUtils

# Import EventHandlers from handlers.py file
# Note: There's both handlers.py (file) and handlers/ (package)
# We need to import from the .py file, not the package
# Use a workaround: import the module with a different name to avoid conflict
import sys
from pathlib import Path

# Temporarily remove handlers package from path to import handlers.py file
_handlers_package_path = Path(__file__).parent / "handlers"
_original_path = None
if _handlers_package_path.exists() and str(_handlers_package_path) in sys.path:
    sys.path.remove(str(_handlers_package_path))
    _original_path = str(_handlers_package_path)

try:
    # Import handlers.py as a module (not the package)
    from src.telegram import handlers as handlers_file
    EventHandlers = handlers_file.EventHandlers
except (ImportError, AttributeError):
    EventHandlers = None
finally:
    # Restore path if we removed it
    if _original_path and _original_path not in sys.path:
        sys.path.append(_original_path)

__all__ = [
    "TelegramClientManager",
    "TelegramUtils",
]

if EventHandlers is not None:
    __all__.append("EventHandlers")
