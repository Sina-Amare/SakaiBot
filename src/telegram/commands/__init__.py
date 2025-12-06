"""Telegram bot self-commands package."""

from .self_commands import (
    handle_auth_command,
    handle_help_command,
    handle_status_command,
    handle_group_command,
)

__all__ = [
    'handle_auth_command',
    'handle_help_command',
    'handle_status_command',
    'handle_group_command',
]
