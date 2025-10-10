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
        pvs, _ = cache_manager.load_pv_cache()
        
        # Create table
        table = Table(title="Authorized Users", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=6)
        table.add_column("Display Name", style="cyan", width=30)
        table.add_column("Username", style="green", width=20)
        table.add_column("User ID", style="yellow", width=15)
        
        for idx, pv_id in enumerate(auth_pvs, 1):
            # Find PV details
            pv_info = None
            if pvs:
                for pv in pvs:
                    if pv['id'] == pv_id:
                        pv_info = pv
                        break
            
            if pv_info:
                display_name = pv_info.get('display_name', 'N/A')
                username = f"@{pv_info.get('username')}" if pv_info.get('username') else "N/A"
            else:
                display_name = "Unknown"
                username = "N/A"
            
            table.add_row(str(idx), display_name, username, str(pv_id))
        
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
        
        auth_pvs = settings.get('directly_authorized_pvs', [])
        
        # Search for PV
        cache_manager = await get_cache_manager()
        pvs, _ = cache_manager.load_pv_cache()
        
        if not pvs:
            display_error("No PV cache found. Run 'sakaibot pv refresh' first.")
            return
        
        results = cache_manager.search_pvs(pvs, identifier)
        # Ensure results is a list to prevent NoneType errors
        if not results: # This check handles both None and empty list
            display_error(f"No user found matching '{identifier}'")
            return
        
        if len(results) == 1:
            selected_pv = results[0]
        else:
            # Multiple matches
            choices = []
            for pv in results[:10]:
                username = f"@{pv['username']}" if pv.get('username') else "N/A"
                choice = f"{pv['display_name']} ({username}) - ID: {pv['id']}"
                choices.append(choice)
            
            selection = prompt_choice("Multiple users found. Select one:", choices)
            selected_idx = choices.index(selection)
            selected_pv = results[selected_idx]
        
        # Check if already authorized
        if selected_pv['id'] in auth_pvs:
            display_warning(f"{selected_pv['display_name']} is already authorized")
            return
        
        # Add to authorized list
        auth_pvs.append(selected_pv['id'])
        settings['directly_authorized_pvs'] = auth_pvs
        settings_manager.save_user_settings(settings)
        
        username = f"@{selected_pv['username']}" if selected_pv.get('username') else "N/A"
        display_success(f"Authorized: {selected_pv['display_name']} ({username})")
        display_info(f"Total authorized users: {len(auth_pvs)}")
        
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
        
        # Try to parse as ID first
        try:
            user_id = int(identifier)
            if user_id in auth_pvs:
                auth_pvs.remove(user_id)
                settings['directly_authorized_pvs'] = auth_pvs
                settings_manager.save_user_settings(settings)
                display_success(f"Removed authorization for user ID: {user_id}")
                return
        except ValueError:
            pass
        
        # Search in cache
        cache_manager = await get_cache_manager()
        pvs, _ = cache_manager.load_pv_cache()
        
        if pvs:
            results = cache_manager.search_pvs(pvs, identifier)
            # Ensure results is a list to prevent NoneType errors
            if results:
                # Check which results are authorized
                authorized_results = [pv for pv in results if pv['id'] in auth_pvs]
                
                if not authorized_results:
                    display_warning(f"No authorized users found matching '{identifier}'")
                    return
                
                if len(authorized_results) == 1:
                    selected_pv = authorized_results[0]
                else:
                    # Multiple matches
                    choices = []
                    for pv in authorized_results:
                        username = f"@{pv['username']}" if pv.get('username') else "N/A"
                        choice = f"{pv['display_name']} ({username}) - ID: {pv['id']}"
                        choices.append(choice)
                    
                    selection = prompt_choice("Multiple authorized users found. Select one:", choices)
                    selected_idx = choices.index(selection)
                    selected_pv = authorized_results[selected_idx]
                
                auth_pvs.remove(selected_pv['id'])
                settings['directly_authorized_pvs'] = auth_pvs
                settings_manager.save_user_settings(settings)
                
                username = f"@{selected_pv['username']}" if selected_pv.get('username') else "N/A"
                display_success(f"Removed authorization: {selected_pv['display_name']} ({username})")
                display_info(f"Remaining authorized users: {len(auth_pvs)}")
                return
        
        display_error(f"No authorized user found matching '{identifier}'")
        
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
