"""PV (Private Chat) management commands."""

import click
import asyncio
from rich import print as rprint
from typing import Optional
from ..utils import (
    get_telegram_client, get_cache_manager, get_settings_manager,
    format_pv_table, display_error, display_success, display_info, display_warning,
    ProgressSpinner, prompt_text, prompt_choice, console
)

@click.group()
def pv():
    """Manage private chats (PVs)."""
    pass

@pv.command()
@click.option('--limit', default=50, help='Number of PVs to display')
@click.option('--refresh', is_flag=True, help='Refresh cache before listing')
def list(limit, refresh):
    """List all cached private chats."""
    asyncio.run(_list_pvs(limit, refresh))

async def _list_pvs(limit: int, refresh: bool):
    """List PVs implementation."""
    try:
        # Get managers
        client, client_manager = await get_telegram_client()
        if not client:
            return
        
        cache_manager = await get_cache_manager()
        
        # Get telegram utils
        from src.telegram.utils import TelegramUtils
        telegram_utils = TelegramUtils()
        
        with ProgressSpinner("Fetching private chats...") as spinner:
            if refresh:
                spinner.update("Refreshing PV cache from Telegram...")
            
            pvs = await cache_manager.get_pvs(
                client=client,
                telegram_utils=telegram_utils,
                force_refresh=refresh
            )
        
        if not pvs:
            display_info("No private chats found in cache.")
            return
        
        # Display PVs
        limited_pvs = pvs[:limit] if limit else pvs
        table = format_pv_table(limited_pvs)
        console.print(table)
        
        if len(pvs) > limit:
            display_info(f"Showing {limit} of {len(pvs)} total PVs. Use --limit to see more.")
        
        display_success(f"Listed {len(limited_pvs)} private chats")
        
    except Exception as e:
        display_error(f"Failed to list PVs: {e}")
    finally:
        if client_manager:
            await client_manager.disconnect()

@pv.command()
@click.option('--fetch-limit', default=200, help='Number of recent chats to fetch')
def refresh(fetch_limit):
    """Refresh PV list from Telegram."""
    asyncio.run(_refresh_pvs(fetch_limit))

async def _refresh_pvs(fetch_limit: int):
    """Refresh PVs implementation."""
    try:
        client, client_manager = await get_telegram_client()
        if not client:
            return
        
        cache_manager = await get_cache_manager()
        from src.telegram.utils import TelegramUtils
        telegram_utils = TelegramUtils()
        
        with ProgressSpinner(f"Fetching up to {fetch_limit} recent chats from Telegram...") as spinner:
            pvs = await cache_manager.get_pvs(
                client=client,
                telegram_utils=telegram_utils,
                force_refresh=True,
                fetch_limit_on_refresh=fetch_limit
            )
        
        display_success(f"Cache refreshed with {len(pvs)} private chats")
        
    except Exception as e:
        display_error(f"Failed to refresh PVs: {e}")
    finally:
        if client_manager:
            await client_manager.disconnect()

@pv.command()
@click.argument('query')
@click.option('--limit', default=10, help='Maximum results to show')
def search(query, limit):
    """Search for private chats by name, username, or ID."""
    asyncio.run(_search_pvs(query, limit))

async def _search_pvs(query: str, limit: int):
    """Search PVs implementation."""
    try:
        cache_manager = await get_cache_manager()
        
        # Load PV cache
        pvs, _ = cache_manager.load_pv_cache()
        if not pvs:
            display_error("No PV cache found. Run 'sakaibot pv refresh' first.")
            return
        
        # Search
        results = cache_manager.search_pvs(pvs, query)
        
        if not results:
            display_info(f"No PVs found matching '{query}'")
            return
        
        # Display results
        limited_results = results[:limit] if limit else results
        table = format_pv_table(limited_results)
        console.print(table)
        
        if len(results) > limit:
            display_info(f"Showing {limit} of {len(results)} matches. Use --limit to see more.")
        
    except Exception as e:
        display_error(f"Search failed: {e}")

@pv.command(name='set-context')
@click.argument('identifier', required=False)
@click.option('--clear', is_flag=True, help='Clear the default context')
def set_context(identifier, clear):
    """Set default PV context for analysis commands."""
    asyncio.run(_set_context(identifier, clear))

async def _set_context(identifier: Optional[str], clear: bool):
    """Set PV context implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        if clear:
            settings['selected_pv_for_categorization'] = None
            settings_manager.save_user_settings(settings)
            display_success("Default PV context cleared")
            return
        
        if not identifier:
            display_error("Please provide a PV identifier (username, ID, or name)")
            return
        
        # Search for PV
        cache_manager = await get_cache_manager()
        pvs, _ = cache_manager.load_pv_cache()
        
        if not pvs:
            display_error("No PV cache found. Run 'sakaibot pv refresh' first.")
            return
        
        results = cache_manager.search_pvs(pvs, identifier)
        
        if not results:
            display_error(f"No PV found matching '{identifier}'")
            return
        
        if len(results) == 1:
            selected_pv = results[0]
        else:
            # Multiple matches, let user choose
            display_info(f"Found {len(results)} matches:")
            choices = []
            for pv in results[:10]:
                username = f"@{pv['username']}" if pv.get('username') else "N/A"
                choice = f"{pv['display_name']} ({username}) - ID: {pv['id']}"
                choices.append(choice)
            
            selection = prompt_choice("Select a PV", choices)
            selected_idx = choices.index(selection)
            selected_pv = results[selected_idx]
        
        # Save selection
        settings['selected_pv_for_categorization'] = selected_pv['id']
        settings_manager.save_user_settings(settings)
        
        username = f"@{selected_pv['username']}" if selected_pv.get('username') else "N/A"
        display_success(f"Default context set to: {selected_pv['display_name']} ({username})")
        
    except Exception as e:
        display_error(f"Failed to set context: {e}")

@pv.command()
def context():
    """Show current default PV context."""
    asyncio.run(_show_context())

async def _show_context():
    """Show current context implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        pv_id = settings.get('selected_pv_for_categorization')
        if not pv_id:
            display_info("No default PV context set. Use 'sakaibot pv set-context' to set one.")
            return
        
        # Find PV details
        cache_manager = await get_cache_manager()
        pvs, _ = cache_manager.load_pv_cache()
        
        if pvs:
            for pv in pvs:
                if pv['id'] == pv_id:
                    username = f"@{pv['username']}" if pv.get('username') else "N/A"
                    display_info(f"Current default context: {pv['display_name']} ({username}) - ID: {pv_id}")
                    return
        
        display_warning(f"Default context set to ID {pv_id}, but PV not found in cache")
        
    except Exception as e:
        display_error(f"Failed to show context: {e}")