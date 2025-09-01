"""Main CLI interface using Click framework.

This module provides the primary CLI interface for SakaiBot using Click,
with support for both interactive and command-line modes.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import click
from rich.console import Console
from rich import print as rprint

from .commands import CLICommands
from .menu import RichMenu
from .state import StateManager, initialize_state, get_state_health_check
from ..core.config import get_settings
from ..core.exceptions import CLIError, ConfigurationError
from ..core.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION

logger = logging.getLogger(__name__)
console = Console()


class AsyncClickGroup(click.Group):
    """Click group that supports async commands."""
    
    def invoke(self, ctx: click.Context) -> None:
        """Invoke the command, handling async commands properly."""
        try:
            return super().invoke(ctx)
        except Exception as e:
            logger.error(f"Command invocation failed: {e}", exc_info=True)
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


def async_command(f):
    """Decorator to make Click commands async."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@click.group(
    cls=AsyncClickGroup,
    name="sakaibot",
    help=f"{APP_DESCRIPTION} - CLI Interface"
)
@click.version_option(
    version=APP_VERSION,
    prog_name=APP_NAME
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to configuration file"
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, config_file: Optional[str]) -> None:
    """SakaiBot CLI - Advanced Telegram userbot with AI capabilities."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Store config file path in context
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    ctx.obj["debug"] = debug


@cli.command()
@click.option(
    "--show-sensitive",
    is_flag=True,
    help="Show sensitive configuration values (use with caution)"
)
@async_command
async def config(show_sensitive: bool) -> None:
    """Display current configuration."""
    try:
        settings = get_settings()
        
        if show_sensitive:
            config_dict = settings.dict()
            console.print("[red]Warning: Showing sensitive configuration values![/red]")
        else:
            config_dict = settings.get_safe_dict()
        
        # Display configuration in a nice format
        console.print("\n[bold]Current Configuration:[/bold]")
        
        for section, values in config_dict.items():
            if isinstance(values, dict):
                console.print(f"\n[cyan]{section.title()}:[/cyan]")
                for key, value in values.items():
                    console.print(f"  {key}: [yellow]{value}[/yellow]")
            else:
                console.print(f"[cyan]{section}:[/cyan] [yellow]{values}[/yellow]")
        
    except Exception as e:
        logger.error(f"Error displaying configuration: {e}", exc_info=True)
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@async_command
async def status() -> None:
    """Display current bot status and health check."""
    try:
        health = get_state_health_check()
        
        console.print(f"\n[bold]{APP_NAME} Status:[/bold]")
        
        # Overall status
        status_color = {
            "healthy": "green",
            "degraded": "yellow",
            "error": "red"
        }.get(health["status"], "white")
        
        console.print(f"Status: [{status_color}]{health['status'].title()}[/{status_color}]")
        
        # Detailed status
        if "initialized" in health:
            console.print(f"Initialized: {'✓' if health['initialized'] else '✗'}")
        if "api_configured" in health:
            console.print(f"API Configured: {'✓' if health['api_configured'] else '✗'}")
        if "monitoring_active" in health:
            console.print(f"Monitoring Active: {'✓' if health['monitoring_active'] else '✗'}")
        
        # Issues
        if health.get("issues"):
            console.print("\n[yellow]Issues:[/yellow]")
            for issue in health["issues"]:
                console.print(f"  • {issue}")
        
        # Error details
        if health.get("error"):
            console.print(f"\n[red]Error:[/red] {health['error']}")
        
    except Exception as e:
        logger.error(f"Error checking status: {e}", exc_info=True)
        console.print(f"[red]Error checking status: {e}[/red]")


@cli.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force start even if configuration is incomplete"
)
@async_command
async def interactive(force: bool) -> None:
    """Start interactive CLI menu."""
    try:
        console.print(f"\n[bold blue]Starting {APP_NAME} Interactive CLI...[/bold blue]")
        
        # Load configuration
        try:
            settings = get_settings()
        except Exception as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            if not force:
                console.print("Use --force to start anyway")
                sys.exit(1)
            settings = None
        
        # Initialize CLI
        await _initialize_cli_components(settings, force)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]CLI interrupted by user[/yellow]")
    except Exception as e:
        logger.error(f"Interactive CLI failed: {e}", exc_info=True)
        console.print(f"[red]CLI failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("pv_query", required=False)
@async_command
async def list_pvs(pv_query: Optional[str]) -> None:
    """List or search private chats.
    
    Args:
        pv_query: Optional search query for filtering PVs
    """
    try:
        # Quick initialization for command mode
        settings = get_settings()
        state_manager = await _quick_init(settings)
        menu = RichMenu(state_manager)
        commands = await _create_command_handler(state_manager, menu, settings)
        
        if pv_query:
            # Search mode
            console.print(f"[blue]Searching PVs for: '{pv_query}'[/blue]")
            results = await commands.search_pvs(show_numbers=False)
        else:
            # List mode
            console.print("[blue]Listing cached PVs...[/blue]")
            results = await commands.list_cached_pvs(show_numbers=False)
        
        if not results:
            console.print("[yellow]No PVs found[/yellow]")
        
    except Exception as e:
        logger.error(f"Error listing PVs: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@async_command
async def refresh() -> None:
    """Refresh cached data from Telegram."""
    try:
        settings = get_settings()
        state_manager = await _quick_init(settings)
        menu = RichMenu(state_manager)
        commands = await _create_command_handler(state_manager, menu, settings)
        
        console.print("[blue]Refreshing data from Telegram...[/blue]")
        await commands.refresh_pvs()
        
    except Exception as e:
        logger.error(f"Error refreshing data: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--start",
    is_flag=True,
    help="Start monitoring"
)
@click.option(
    "--stop",
    is_flag=True,
    help="Stop monitoring"
)
@async_command
async def monitor(start: bool, stop: bool) -> None:
    """Control global monitoring."""
    if start and stop:
        console.print("[red]Cannot specify both --start and --stop[/red]")
        sys.exit(1)
    
    if not start and not stop:
        console.print("[yellow]Specify either --start or --stop[/yellow]")
        sys.exit(1)
    
    try:
        settings = get_settings()
        state_manager = await _quick_init(settings)
        menu = RichMenu(state_manager)
        commands = await _create_command_handler(state_manager, menu, settings)
        
        if start:
            console.print("[blue]Starting monitoring...[/blue]")
            await commands._start_monitoring()
        else:
            console.print("[blue]Stopping monitoring...[/blue]")
            await commands._stop_monitoring()
        
    except Exception as e:
        logger.error(f"Error controlling monitoring: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@async_command
async def wizard() -> None:
    """Run the configuration wizard."""
    try:
        settings = get_settings()
        state_manager = await _quick_init(settings)
        menu = RichMenu(state_manager)
        commands = await _create_command_handler(state_manager, menu, settings)
        
        await commands.display_config_wizard()
        
    except Exception as e:
        logger.error(f"Error running wizard: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def _initialize_cli_components(
    settings: Optional[Any],
    force: bool = False
) -> None:
    """Initialize CLI components and start interactive mode.
    
    Args:
        settings: Application settings
        force: Whether to force start with incomplete config
    """
    try:
        if not settings and not force:
            raise CLIError("Configuration not available and force not specified")
        
        # Initialize Telegram client and other components
        from telethon import TelegramClient
        import sys
        import os
        
        # Add root directory to Python path for legacy imports
        root_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(root_dir))
        
        try:
            import cache_manager
            import telegram_utils
            import settings_manager
            import event_handlers
        except ImportError as e:
            console.print(f"[red]Failed to import legacy modules: {e}[/red]")
            if not force:
                console.print("Use --force to continue anyway")
                sys.exit(1)
            return
        
        # Create Telegram client
        if settings:
            session_name = settings.telegram.session_name or "sakaibot_session"
            client = TelegramClient(
                session_name,
                settings.telegram.api_id,
                settings.telegram.api_hash.get_secret_value()
            )
            
            # Connect and authenticate
            await client.connect()
            if not await client.is_user_authorized():
                console.print("[yellow]Telegram authentication required[/yellow]")
                console.print("Please run the bot in normal mode first to authenticate")
                return
        else:
            console.print("[yellow]Running in limited mode without full configuration[/yellow]")
            return
        
        # Initialize components
        cache_mgr = cache_manager
        
        # Initialize state manager
        state_manager = await initialize_state(
            openrouter_api_key=settings.openrouter.api_key.get_secret_value(),
            openrouter_model_name=settings.openrouter.model_name,
            max_analyze_messages=settings.userbot.max_analyze_messages,
            ffmpeg_path=str(settings.paths.ffmpeg_executable) if settings.paths.ffmpeg_executable else None,
            settings_manager=settings_manager
        )
        
        # Create menu and commands
        menu = RichMenu(state_manager)
        commands = CLICommands(
            state_manager=state_manager,
            menu=menu,
            client=client,
            cache_manager=cache_mgr,
            telegram_utils=telegram_utils,
            settings_manager=settings_manager,
            event_handlers=event_handlers
        )
        
        # Cache group topics if needed
        await state_manager.cache_group_topics(client, telegram_utils)
        
        # Display startup information
        menu.display_header()
        
        # Check if this is first run
        state = state_manager.state
        is_first_run = not any([
            state.selected_target_group,
            state.active_command_to_topic_map,
            state.directly_authorized_pvs
        ])
        
        if is_first_run:
            menu.display_welcome_message()
            
            if await menu.confirm_action("Would you like to run the setup wizard?"):
                await commands.display_config_wizard()
                await menu.wait_for_keypress()
        
        # Display health check
        health = get_state_health_check()
        commands.display_startup_check(health)
        
        # Start main menu loop
        await _run_interactive_loop(commands, menu)
        
    except Exception as e:
        logger.error(f"CLI initialization failed: {e}", exc_info=True)
        console.print(f"[red]CLI initialization failed: {e}[/red]")
        sys.exit(1)


async def _run_interactive_loop(
    commands: CLICommands,
    menu: RichMenu
) -> None:
    """Run the main interactive menu loop.
    
    Args:
        commands: CLI commands instance
        menu: Rich menu instance
    """
    logger.info("Starting interactive CLI loop")
    
    try:
        while True:
            # Display main menu
            menu.display_main_menu()
            
            try:
                choice = await menu.get_user_choice("Enter your choice", expect_int=True)
                
                # Route to appropriate command
                if choice == 1:
                    await commands.list_cached_pvs()
                elif choice == 2:
                    await commands.refresh_pvs()
                elif choice == 3:
                    await commands.search_pvs()
                elif choice == 4:
                    await commands.set_default_pv_context()
                elif choice == 5:
                    await commands.set_target_group()
                elif choice == 6:
                    await commands.manage_command_mappings()
                elif choice == 7:
                    await commands.toggle_monitoring()
                elif choice == 8:
                    await commands.manage_authorized_pvs()
                elif choice == 0:
                    # Exit
                    if await commands.exit_cli():
                        break
                else:
                    menu.display_error("Invalid choice. Please try again.")
                
                # Wait for user to continue (except for exit)
                if choice != 0:
                    await menu.wait_for_keypress()
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation interrupted[/yellow]")
                if await menu.confirm_action("Do you want to exit the CLI?"):
                    if await commands.exit_cli():
                        break
                continue
            
            except Exception as e:
                logger.error(f"Error in menu loop: {e}", exc_info=True)
                menu.display_error("Menu operation failed", str(e))
                await menu.wait_for_keypress()
    
    except Exception as e:
        logger.error(f"Interactive loop failed: {e}", exc_info=True)
        menu.display_error("CLI loop failed", str(e))
    
    finally:
        logger.info("Interactive CLI loop ended")


async def _quick_init(settings: Any) -> StateManager:
    """Quick initialization for command-mode operations.
    
    Args:
        settings: Application settings
        
    Returns:
        StateManager: Initialized state manager
    """
    # Import required modules
    import settings_manager as sm
    
    # Initialize state manager with minimal setup
    state_manager = StateManager(sm)
    await state_manager.initialize(
        openrouter_api_key=settings.openrouter.api_key.get_secret_value(),
        openrouter_model_name=settings.openrouter.model_name,
        max_analyze_messages=settings.userbot.max_analyze_messages,
        ffmpeg_path=str(settings.paths.ffmpeg_executable) if settings.paths.ffmpeg_executable else None
    )
    
    return state_manager


async def _create_command_handler(
    state_manager: StateManager,
    menu: RichMenu,
    settings: Any
) -> CLICommands:
    """Create command handler with dependencies.
    
    Args:
        state_manager: State manager instance
        menu: Rich menu instance
        settings: Application settings
        
    Returns:
        CLICommands: Configured command handler
    """
    # Import required modules
    from telethon import TelegramClient
    import sys
    
    # Add root directory to Python path for legacy imports
    root_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(root_dir))
    
    import cache_manager
    import telegram_utils
    import settings_manager
    import event_handlers
    
    # Create Telegram client
    session_name = settings.telegram.session_name or "sakaibot_session"
    client = TelegramClient(
        session_name,
        settings.telegram.api_id,
        settings.telegram.api_hash.get_secret_value()
    )
    
    # Connect client
    await client.connect()
    if not await client.is_user_authorized():
        raise CLIError("Telegram authentication required")
    
    return CLICommands(
        state_manager=state_manager,
        menu=menu,
        client=client,
        cache_manager=cache_manager,
        telegram_utils=telegram_utils,
        settings_manager=settings_manager,
        event_handlers=event_handlers
    )


# Legacy function for backward compatibility
async def display_main_menu_loop(
    client,
    cache_manager,
    telegram_utils_module,
    settings_manager_module,
    event_handlers_module,
    openrouter_api_key_main: str,
    openrouter_model_name_main: str,
    max_analyze_messages_main: int,
    ffmpeg_path: Optional[str] = None
) -> None:
    """Legacy function to maintain compatibility with existing code.
    
    This function bridges the old CLI interface with the new Click-based system.
    
    Args:
        client: Telegram client
        cache_manager: Cache manager instance
        telegram_utils_module: Telegram utilities module
        settings_manager_module: Settings manager module
        event_handlers_module: Event handlers module
        openrouter_api_key_main: OpenRouter API key
        openrouter_model_name_main: Model name
        max_analyze_messages_main: Max messages to analyze
        ffmpeg_path: FFmpeg executable path
    """
    try:
        logger.info("Starting legacy CLI compatibility mode")
        
        # Initialize state manager
        state_manager = StateManager(settings_manager_module)
        await state_manager.initialize(
            openrouter_api_key=openrouter_api_key_main,
            openrouter_model_name=openrouter_model_name_main,
            max_analyze_messages=max_analyze_messages_main,
            ffmpeg_path=ffmpeg_path
        )
        
        # Cache group topics if needed
        await state_manager.cache_group_topics(client, telegram_utils_module)
        
        # Create menu and commands
        menu = RichMenu(state_manager)
        commands = CLICommands(
            state_manager=state_manager,
            menu=menu,
            client=client,
            cache_manager=cache_manager,
            telegram_utils=telegram_utils_module,
            settings_manager=settings_manager_module,
            event_handlers=event_handlers_module
        )
        
        # Display header
        menu.display_header()
        
        # Check for first-time setup
        state = state_manager.state
        is_first_run = not any([
            state.selected_target_group,
            state.active_command_to_topic_map,
            state.directly_authorized_pvs
        ])
        
        if is_first_run:
            menu.display_welcome_message()
        
        # Run interactive loop
        await _run_interactive_loop(commands, menu)
        
    except Exception as e:
        logger.error(f"Legacy CLI failed: {e}", exc_info=True)
        console.print(f"[red]CLI failed: {e}[/red]")
        raise


if __name__ == "__main__":
    cli()
