"""Telegram event handlers package."""

# Export specialized handlers
from .base import BaseHandler
from .stt_handler import STTHandler
from .tts_handler import TTSHandler
from .ai_handler import AIHandler
from .categorization_handler import CategorizationHandler

# Import EventHandlers from the parent module file (handlers.py)
# We need to import it in a way that avoids circular imports
# The handlers.py file imports from this package, so we need to be careful
import sys
from pathlib import Path

# Store original module cache
_original_modules = {}

try:
    # Temporarily remove this package from sys.modules to avoid circular import
    _package_name = __name__
    if _package_name in sys.modules:
        _original_modules[_package_name] = sys.modules[_package_name]
        del sys.modules[_package_name]
    
    # Import the parent module file
    _parent_dir = Path(__file__).parent.parent
    _handlers_file_path = _parent_dir / "handlers.py"
    
    if _handlers_file_path.exists():
        # Use importlib to load it as a separate module
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "src.telegram.handlers_file",
            _handlers_file_path
        )
        if spec and spec.loader:
            handlers_file_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(handlers_file_module)
            EventHandlers = getattr(handlers_file_module, 'EventHandlers', None)
        else:
            EventHandlers = None
    else:
        EventHandlers = None
except Exception as e:
    EventHandlers = None
finally:
    # Restore original module
    if _package_name in _original_modules:
        sys.modules[_package_name] = _original_modules[_package_name]

__all__ = [
    'BaseHandler',
    'STTHandler',
    'TTSHandler',
    'AIHandler',
    'CategorizationHandler'
]

if EventHandlers is not None:
    __all__.append('EventHandlers')

