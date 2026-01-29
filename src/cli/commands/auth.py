"""Authorization management commands."""

import click
import asyncio
from rich.table import Table
from typing import Optional
from ..utils import (
    get_cache_manager, get_settings_manager,
    display_error, display_success, display_info, display_warning,
    prompt_choice, prompt_text, confirm_action, console
)
from src.telegram.user_verifier import TelegramUserVerifier

@click.group()
def auth():
    """Manage authorized users."""
    pass

@auth.command()
def list():
    """List all authorized users."""
    asyncio.run(_list_authorized())

async def _list_authorized():
    """List authorized users implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        auth_pvs = settings.get('directly_authorized_pvs', [])
        
        if not auth_pvs:
            display_info("No authorized users. Use 'sakaibot auth add' to authorize users.")
            return
        
        # Get PV details from cache
        cache_manager = await get_cache_manager()
        cached_pvs, _ = cache_manager.load_pv_cache()
        
        # Get Telegram client for direct verification of users not in cache
        from ..utils import get_telegram_client
        client, client_manager = await get_telegram_client()
        verifier = None  # Initialize verifier as None
        if not client:
            # Bot is running, show cached data with helpful message
            display_warning(
                "Bot is currently running - showing cached data.\n"
                "For live updates, use: /auth list in Telegram"
            )
            cached_pvs = cached_pvs or []
        else:
            # Use the user verifier to get updated information for users not in cache
            verifier = TelegramUserVerifier(client)
        
        # Create table
        table = Table(title="Authorized Users", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=6)
        table.add_column("Display Name", style="cyan", width=30)
        table.add_column("Username", style="green", width=20)
        table.add_column("User ID", style="yellow", width=15)
        
        for idx, pv_id in enumerate(auth_pvs, 1):
            # Find PV details in cache first
            pv_info = None
            if cached_pvs:
                for pv in cached_pvs:
                    if pv['id'] == pv_id:
                        pv_info = pv
                        break
            
            # If not found in cache and we have a client, fetch directly from Telegram
            if not pv_info and client and verifier:
                try:
                    user_info = await verifier.verify_user_by_identifier(str(pv_id))
                    if user_info:
                        pv_info = user_info
                except Exception:
                    # If direct fetch fails, continue with what we have
                    pass
            
            if pv_info:
                display_name = pv_info.get('display_name', 'N/A')
                username = f"@{pv_info.get('username')}" if pv_info.get('username') else "N/A"
            else:
                display_name = "Unknown"
                username = "N/A"
                pv_info = {'id': pv_id}
            
            table.add_row(str(idx), display_name, username, str(pv_info['id']))
        
        console.print(table)
        display_info(f"Total authorized users: {len(auth_pvs)}")
        
    except Exception as e:
        display_error(f"Failed to list authorized users: {e}")

@auth.command()
@click.argument('identifier')
def add(identifier):
    """Add an authorized user by username, ID, or name."""
    asyncio.run(_add_authorized(identifier))

async def _add_authorized(identifier: str):
    """Add authorized user implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()

        # Code disabled as user_info is undefined
        # if user_info['id'] in auth_pvs:
        #     display_warning(f"{user_info['display_name']} is already authorized")
        #     return

        # # Add to authorized list
        # auth_pvs.append(user_info['id'])
        # settings['directly_authorized_pvs'] = auth_pvs
        # settings_manager.save_user_settings(settings)

        # username = user_info.get('username', 'N/A')
        # display_success(f"Authorized: {user_info['display_name']} ({username})")
        # display_info(f"Total authorized users: {len(auth_pvs)}")
        
        display_warning("This command is deprecated. Use Telegram commands instead.")

    except Exception as e:
        display_error(f"Failed to add authorized user: {e}")

@auth.command()
@click.argument('identifier')
def remove(identifier):
    """Remove an authorized user."""
    asyncio.run(_remove_authorized(identifier))

async def _remove_authorized(identifier: str):
    """Remove authorized user implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        auth_pvs = settings.get('directly_authorized_pvs', [])
        
        if not auth_pvs:
            display_info("No authorized users to remove.")
            return

        # Code disabled as user_info is undefined and logic is incomplete
        # if user_info['id'] not in auth_pvs:
        #     display_error(f"User {user_info['display_name']} is not authorized")
        #     return

        # # Remove from authorized list
        # auth_pvs.remove(user_info['id'])
        # settings['directly_authorized_pvs'] = auth_pvs
        # settings_manager.save_user_settings(settings)

        # username = user_info.get('username', 'N/A')
        # display_success(f"Removed authorization: {user_info['display_name']} ({username})")
        # display_info(f"Remaining authorized users: {len(auth_pvs)}")
        
        display_warning("This command is deprecated. Use Telegram commands instead.")

    except Exception as e:
        display_error(f"Failed to remove authorized user: {e}")

@auth.command()
def clear():
    """Clear all authorized users."""
    asyncio.run(_clear_authorized())

async def _clear_authorized():
    """Clear all authorized users implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        auth_pvs = settings.get('directly_authorized_pvs', [])
        
        if not auth_pvs:
            display_info("No authorized users to clear.")
            return
        
        if confirm_action(f"Remove authorization for all {len(auth_pvs)} users?"):
            settings['directly_authorized_pvs'] = []
            settings_manager.save_user_settings(settings)
            display_success(f"Cleared all {len(auth_pvs)} authorized users")
        else:
            display_info("Operation cancelled")
        
    except Exception as e:
        display_error(f"Failed to clear authorized users: {e}")

@auth.command()
def refresh():
    """Refresh PV cache from Telegram."""
    asyncio.run(_refresh_cache())

async def _refresh_cache():
    """Refresh PV cache implementation."""
    try:
        from ..utils import get_telegram_client
        from src.telegram.utils import TelegramUtils
        from src.utils.cache import CacheManager

        client, client_manager = await get_telegram_client()
        if not client:
            display_error("Failed to connect to Telegram. Cannot refresh cache.")
            return

        cache_manager = await get_cache_manager()
        telegram_utils = TelegramUtils()
        pvs = await cache_manager.get_pvs(client, telegram_utils, force_refresh=True)

        if pvs:
            display_success(f"Successfully refreshed PV cache with {len(pvs)} users")
        else:
            display_warning("No PVs found to cache")

    except Exception as e:
        display_error(f"Failed to refresh PV cache: {e}")
