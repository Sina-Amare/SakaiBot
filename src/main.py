#!/usr/bin/env python3
"""
SakaiBot - Advanced Telegram Userbot with AI Capabilities

Main entry point for the application.
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings, Settings
from src.core.constants import APP_NAME, APP_VERSION, SYSTEM_MESSAGES
from src.core.exceptions import SakaiBotError, ConfigurationError
from src.utils.logging import setup_logging, get_logger, shutdown_logging
from src.telegram.client import create_telegram_client, SakaiBotTelegramClient
from src.cli.interface import cli

# Initialize console for rich output
console = Console()

# Global client instance for signal handling
_client: Optional[SakaiBotTelegramClient] = None
_shutdown_flag = False


def signal_handler(signum: int, frame) -> None:
    """
    Handle shutdown signals gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global _shutdown_flag
    if not _shutdown_flag:
        _shutdown_flag = True
        console.print("\n[yellow]Received shutdown signal. Cleaning up...[/yellow]")
        if _client and _client.is_connected():
            asyncio.create_task(_client.disconnect())
        shutdown_logging()
        sys.exit(0)


async def initialize_bot(settings: Settings) -> SakaiBotTelegramClient:
    """
    Initialize the Telegram bot client.
    
    Args:
        settings: Application settings
        
    Returns:
        Initialized Telegram client
        
    Raises:
        ConfigurationError: If initialization fails
    """
    logger = get_logger(__name__)
    
    try:
        # Create Telegram client
        client = create_telegram_client(settings)
        
        # Connect to Telegram
        await client.connect()
        await client.authenticate()
        
        logger.info(f"{APP_NAME} initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise ConfigurationError(f"Bot initialization failed: {e}")


async def run_bot(settings: Settings, debug: bool = False) -> None:
    """
    Main bot runtime loop.
    
    Args:
        settings: Application settings
        debug: Enable debug mode
    """
    global _client
    logger = get_logger(__name__)
    
    try:
        # Initialize bot
        console.print(Panel.fit(
            Text(f"{APP_NAME} v{APP_VERSION}", justify="center", style="bold cyan"),
            title="Starting",
            border_style="cyan"
        ))
        
        _client = await initialize_bot(settings)
        
        # Show success message
        console.print("[green]✓[/green] Bot connected successfully!")
        me = await _client.get_me()
        username = me.username if hasattr(me, 'username') else me.phone
        console.print(f"[cyan]Logged in as:[/cyan] {username}")
        
        # Start CLI interface if not in headless mode
        if not settings.environment == "production":
            # Import and start interactive CLI
            from src.cli.interactive_menu import start_interactive_cli
            
            # Run CLI and bot concurrently
            cli_task = asyncio.create_task(start_interactive_cli(_client, settings))
            bot_task = asyncio.create_task(_client.run_until_disconnected())
            
            # Wait for either to complete
            done, pending = await asyncio.wait(
                [cli_task, bot_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel the other task
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        else:
            # Production mode - no CLI
            console.print("\n[cyan]Bot is running. Press Ctrl+C to stop.[/cyan]")
            await _client.run_until_disconnected()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except SakaiBotError as e:
        logger.error(f"Bot error: {e}")
        console.print(f"[red]Error:[/red] {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error:[/red] {e}")
    finally:
        if _client:
            await _client.disconnect()
        console.print("[yellow]Bot stopped.[/yellow]")


@click.command()
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode'
)
@click.option(
    '--config',
    type=click.Path(),
    default='data/config.ini',
    help='Path to configuration file'
)
@click.option(
    '--env-file',
    type=click.Path(),
    default=None,
    help='Path to environment file (optional)'
)
@click.version_option(version=APP_VERSION, prog_name=APP_NAME)
def main(debug: bool, config: str, env_file: Optional[str]) -> None:
    """
    SakaiBot - Advanced Telegram Userbot with AI Capabilities
    
    This bot provides AI-powered message processing, speech-to-text conversion,
    chat analysis, and automated message categorization capabilities.
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load settings
        settings = get_settings()
        
        # Set debug mode
        if debug:
            settings.debug = True
            settings.logging.level = "DEBUG"
        
        # Setup logging
        setup_logging(
            log_level=settings.logging.level,
            log_dir=Path(settings.paths.logs_dir),
            json_format=settings.environment == "production",
            enable_console=debug,
            enable_file=True,
            async_logging=True
        )
        
        logger = get_logger(__name__)
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        
        # Run the bot
        asyncio.run(run_bot(settings, debug))
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print("\n[yellow]Please check your configuration:[/yellow]")
        console.print("1. Copy config.ini.example to data/config.ini")
        console.print("2. Fill in your Telegram API credentials")
        console.print("3. Add your OpenRouter API key")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Fatal Error:[/red] {e}")
        sys.exit(1)
    finally:
        shutdown_logging()


if __name__ == "__main__":
    main()