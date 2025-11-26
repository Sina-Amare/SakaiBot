"""CLI command modules."""

from .config import config
from .group import group
"""CLI command modules."""

from .config import config
from .group import group
from .monitor import monitor
from .status import status
# Auth commands disabled - use Telegram self-commands instead:
# /auth list, /auth add @user, /auth remove @user
# from .auth import auth

__all__ = [
    'config',
    'group',
    'monitor',
    'status',
    # 'auth',  # Disabled - use Telegram self-commands
]