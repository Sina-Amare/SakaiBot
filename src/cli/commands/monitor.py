"""Monitoring commands."""

import sys
import click
import asyncio
import signal
from datetime import datetime
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from ..utils import (
    get_telegram_client, get_settings_manager,
    display_error, display_success, display_info, display_warning,
    normalize_command_mappings, console
)

# Global monitoring state
monitoring_active = False
monitoring_task = None

@click.group()
def monitor():
    """Monitor and process Telegram events."""
    pass

@monitor.command()
@click.option('--verbose', is_flag=True, help='Show detailed monitoring output')
def start(verbose):
    """Start global monitoring for commands and messages."""
    asyncio.run(_start_monitoring(verbose))

async def _start_monitoring(verbose: bool):
    """Start monitoring implementation."""
    global monitoring_active, monitoring_task
    
    try:
        # Check prerequisites
        from src.core.config import get_settings
        from src.cli.state import CLIState
        
        config = get_settings()
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        # Create CLI state for validation
        cli_state = CLIState(config)
        cli_state.selected_target_group = settings.get('selected_target_group')
        cli_state.active_command_to_topic_map = settings.get('active_command_to_topic_map', {})
        cli_state.directly_authorized_pvs = settings.get('directly_authorized_pvs', [])
        
        if not cli_state.can_start_monitoring:
            display_error("Cannot start monitoring. Requirements not met:")
            if not cli_state.can_categorize:
                display_info("  • For categorization: Set target group and define command mappings")
            if not cli_state.can_use_ai:
                provider = config.llm_provider if config else "LLM"
                provider_name = "Gemini" if provider == "gemini" else "OpenRouter" if provider == "openrouter" else provider.title()
                display_info(f"  • For AI features: Ensure {provider_name} API key is set in config")
            return
        
        # Initialize components
        client, client_manager = await get_telegram_client()
        if not client:
            return
        
        # Create monitoring display
        display_success("Starting global monitoring...")

        # Show monitoring status
        status_lines = []
        if cli_state.can_categorize:
            status_lines.append(f"Categorization: Target group set, {len(cli_state.active_command_to_topic_map)} mappings")
        if cli_state.can_use_ai:
            status_lines.append(f"AI Features: {config.llm_provider.title()} provider active")
        if cli_state.directly_authorized_pvs:
            status_lines.append(f"Authorized PVs: {len(cli_state.directly_authorized_pvs)} users")
        
        for line in status_lines:
            display_info(line)
        
        # Setup event handlers
        try:
            from src.telegram.handlers import EventHandlers
            from src.ai.processor import AIProcessor
            from src.ai.stt import SpeechToTextProcessor
            from src.ai.tts import TextToSpeechProcessor
            from src.telegram.utils import TelegramUtils
            from src.utils.cache import CacheManager
            
            ai_processor = AIProcessor(config)
            stt_processor = SpeechToTextProcessor()
            tts_processor = TextToSpeechProcessor()
            telegram_utils = TelegramUtils()
            cache_manager = CacheManager()
            
            event_handlers = EventHandlers(
                ai_processor=ai_processor,
                stt_processor=stt_processor,
                tts_processor=tts_processor,
                ffmpeg_path=config.ffmpeg_path_resolved
            )
            
            # Verify event_handlers was initialized properly
            if not hasattr(event_handlers, 'process_command_logic') or event_handlers.process_command_logic is None:
                raise RuntimeError("EventHandlers.process_command_logic is not initialized")
                
        except Exception as e:
            display_error(f"Failed to initialize event handlers: {e}")
            if client_manager:
                await client_manager.disconnect()
            return
        
        # Register handlers
        from telethon import events
        
        # Owner handler for outgoing messages
        owner_pattern = r'^/\w+'
        owner_filter = events.NewMessage(
            pattern=owner_pattern,
            outgoing=True,
            forwards=False
        )
        
        async def owner_handler(event):
            """Handle owner commands."""
            if verbose:
                console.print(f"[cyan]Owner command detected: {event.text[:50]}...[/cyan]")
            
            replied_message = await event.message.get_reply_message() if event.message.is_reply else None
            
            await event_handlers.process_command_logic(
                message_to_process=event.message,
                client=client,
                current_chat_id_for_response=event.chat_id,
                is_confirm_flow=False,
                your_confirm_message=None,
                actual_message_for_categorization_content=replied_message,
                cli_state_ref={
                    'selected_target_group': cli_state.selected_target_group,
                    'active_command_to_topic_map': cli_state.active_command_to_topic_map,
                    'is_monitoring_active': True
                },
                is_direct_auth_user_command=False
            )
        
        client.add_event_handler(owner_handler, owner_filter)
        
        # Authorized user handlers
        auth_handlers = []
        if cli_state.directly_authorized_pvs:
            for auth_pv_id in cli_state.directly_authorized_pvs:
                auth_filter = events.NewMessage(
                    pattern=owner_pattern,
                    from_users=[auth_pv_id],
                    incoming=True,
                    forwards=False
                )
                
                async def auth_handler(event):
                    """Handle authorized user commands."""
                    if verbose:
                        console.print(f"[green]Authorized command from {event.sender_id}: {event.text[:50]}...[/green]")
                    
                    # Process command directly without confirmation for authorized users
                    replied_message = await event.message.get_reply_message() if event.message.is_reply else None
                    
                    await event_handlers.process_command_logic(
                        message_to_process=event.message,
                        client=client,
                        current_chat_id_for_response=event.chat_id,
                        is_confirm_flow=False,
                        your_confirm_message=None,
                        actual_message_for_categorization_content=replied_message,
                        cli_state_ref={
                            'selected_target_group': cli_state.selected_target_group,
                            'active_command_topic_map': cli_state.active_command_to_topic_map,
                            'is_monitoring_active': True
                        },
                        is_direct_auth_user_command=True  # Mark as authorized user command
                    )
                
                client.add_event_handler(auth_handler, auth_filter)
                auth_handlers.append((auth_handler, auth_filter))
        
        monitoring_active = True
        display_success("Monitoring started. Press Ctrl+C to stop.")
        
        # Keep monitoring active
        try:
            while monitoring_active:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup handlers
            client.remove_event_handler(owner_handler, owner_filter)
            for handler, filter in auth_handlers:
                client.remove_event_handler(handler, filter)
            
            monitoring_active = False
            display_info("Monitoring stopped")
            
            if client_manager:
                await client_manager.disconnect()
        
    except Exception as e:
        display_error(f"Failed to start monitoring: {e}")
        monitoring_active = False

@monitor.command()
def stop():
    """Stop global monitoring."""
    global monitoring_active, monitoring_task
    
    if not monitoring_active:
        display_info("Monitoring is not active")
        return
    
    monitoring_active = False
    if monitoring_task:
        monitoring_task.cancel()
    
    display_success("Monitoring stopped")

@monitor.command()
def status():
    """Show current monitoring status."""
    asyncio.run(_show_monitoring_status())

async def _show_monitoring_status():
    """Show monitoring status implementation."""
    global monitoring_active
    
    if not sys.stdout.isatty():
        print("Monitoring status:")
        # Plain text output
        return

    try:
        from src.core.config import get_settings
        from src.cli.state import CLIState
        
        config = get_settings()
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        # Create status table
        table = Table(title="Monitoring Status", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="cyan", width=25)
        table.add_column("Status", width=20)
        table.add_column("Details", style="dim")
        
        # Monitoring state
        mon_status = "[green]✓ Active[/green]" if monitoring_active else "[red]✗ Inactive[/red]"
        table.add_row("Monitoring", mon_status, "")
        
        # Categorization
        target_group = settings.get('selected_target_group')
        mappings = normalize_command_mappings(settings.get('active_command_to_topic_map', {}))
        
        if target_group and mappings:
            cat_status = "[green]✓ Ready[/green]"
            cat_details = f"{len(mappings)} command mappings"
        elif target_group:
            cat_status = "[yellow]⚠ Partial[/yellow]"
            cat_details = "No command mappings"
        else:
            cat_status = "[red]✗ Not configured[/red]"
            cat_details = "Set target group first"
        
        table.add_row("Categorization", cat_status, cat_details)
        
        # AI Features
        if config.is_ai_enabled:
            ai_status = "[green]✓ Ready[/green]"
            ai_details = f"{config.llm_provider.title()} provider"
        else:
            ai_status = "[red]✗ Not configured[/red]"
            ai_details = "API key required"
        
        table.add_row("AI Features", ai_status, ai_details)
        
        # Authorization
        auth_pvs = settings.get('directly_authorized_pvs', [])
        auth_status = f"[blue]{len(auth_pvs)} users[/blue]"
        auth_details = "Can send commands for approval" if auth_pvs else "No authorized users"
        
        table.add_row("Authorized PVs", auth_status, auth_details)
        
        console.print(table)
        
        # Show requirements if not ready
        cli_state = CLIState(config)
        cli_state.selected_target_group = target_group
        cli_state.active_command_to_topic_map = mappings
        
        if not cli_state.can_start_monitoring:
            console.print("\n[yellow]Requirements to start monitoring:[/yellow]")
            if not cli_state.can_categorize:
                console.print("  • Set target group: sakaibot group set")
                console.print("  • Add command mappings: sakaibot group map --add")
            if not cli_state.can_use_ai:
                console.print(f"  • Configure {config.llm_provider.title()} API key in .env")
        
    except Exception as e:
        display_error(f"Failed to show monitoring status: {e}")
