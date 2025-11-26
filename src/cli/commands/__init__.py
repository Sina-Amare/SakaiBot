"""CLI command modules."""

from .config import config
from .group import group
from .monitor import monitor
# from .status import status  # Status is handled in main.py locally
# from .auth import auth  # Auth commands disabled - use Telegram self-commands instead

__all__ = [
    'config',
    'group',
    'monitor',
    # 'status',
    # 'auth',
]