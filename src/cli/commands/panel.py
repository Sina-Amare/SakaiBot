"""`sakaibot panel` — launch the local web control panel.

Mirrors `monitor start`: it acquires the ONE shared Telegram client via
`get_telegram_client()` (which refuses to start a second instance, protecting
the session), optionally registers the live monitoring handlers so the bot
keeps working in chats, then serves the web dashboard on the same event loop.
"""

import asyncio

import click

from ..utils import (
    console,
    display_error,
    display_info,
    display_success,
    get_settings_manager,
    get_telegram_client,
)


@click.command()
@click.option("--port", default=None, type=int, help="Port to serve the panel on (default 8765).")
@click.option("--no-monitoring", is_flag=True, default=False, help="Run as a pure private console (bot does NOT process chat commands).")
@click.option("--real-photos", is_flag=True, default=False, help="Fetch real profile photos (lazy + cached). Default is initials only.")
@click.option("--verbose", is_flag=True, default=False, help="Verbose monitoring output.")
def panel(port, no_monitoring, real_photos, verbose):
    """Launch the premium local web control panel."""
    try:
        asyncio.run(_run_panel(port, not no_monitoring, real_photos, verbose))
    except KeyboardInterrupt:
        console.print("\n[cyan]Panel stopped.[/cyan]")


async def _run_panel(port, with_monitoring, real_photos, verbose):
    from src.core.config import get_settings
    from src.cli.state import CLIState
    from src.cli.utils import set_shared_client, clear_shared_client
    from src.panel.config import PanelConfig
    from src.panel.state import build_panel_state
    from src.panel.runner import start_panel
    from src.ai.processor import AIProcessor
    from src.ai.stt import SpeechToTextProcessor
    from src.ai.tts import TextToSpeechProcessor

    config = get_settings()

    client, client_manager = await get_telegram_client()
    if not client:
        return
    set_shared_client(client, client_manager)

    # Shared AI core (used by both the panel and, if enabled, monitoring).
    ai_processor = AIProcessor(config)
    stt_processor = SpeechToTextProcessor()
    tts_processor = TextToSpeechProcessor()

    registered = []
    analyze_started = False

    try:
        if with_monitoring:
            from src.telegram.event_handlers import EventHandlers
            from src.panel.monitor_runtime import register_monitoring
            from src.ai.analyze_queue import analyze_queue

            settings_manager = await get_settings_manager()
            settings = settings_manager.load_user_settings()
            cli_state = CLIState(config)
            cli_state.selected_target_group = settings.get("selected_target_group")
            cli_state.active_command_to_topic_map = settings.get("active_command_to_topic_map", {})
            cli_state.directly_authorized_pvs = settings.get("directly_authorized_pvs", [])

            event_handlers = EventHandlers(
                ai_processor=ai_processor,
                stt_processor=stt_processor,
                tts_processor=tts_processor,
                ffmpeg_path=config.ffmpeg_path_resolved,
            )
            registered = register_monitoring(
                client,
                event_handlers,
                selected_target_group=cli_state.selected_target_group,
                active_command_to_topic_map=cli_state.active_command_to_topic_map,
                directly_authorized_pvs=cli_state.directly_authorized_pvs,
                verbose=verbose,
            )
            await analyze_queue.start_cleanup_task()
            analyze_started = True
            display_info("Monitoring active: the bot still responds to chat commands.")

        panel_config = PanelConfig.from_env(
            port=port,
            real_photos=True if real_photos else None,
            with_monitoring=with_monitoring,
        )
        state = build_panel_state(
            client=client,
            client_manager=client_manager,
            config=config,
            ai_processor=ai_processor,
            stt_processor=stt_processor,
            tts_processor=tts_processor,
            panel_config=panel_config,
        )
        handle = await start_panel(state)

        url = f"http://{panel_config.host}:{panel_config.port}"
        console.rule("[bold cyan]SakaiBot Control Panel[/bold cyan]")
        display_success(f"Panel running at {url}")
        console.print(f"  [bold]Token:[/bold] [yellow]{panel_config.token}[/yellow]")
        console.print(f"  [bold]Open:[/bold]  [green]{url}/?token={panel_config.token}[/green]")
        console.print("  Press Ctrl+C to stop.\n")

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            display_info("Shutting down panel...")
            await handle.stop()
    finally:
        if registered:
            from src.panel.monitor_runtime import unregister_monitoring

            unregister_monitoring(client, registered)
        if analyze_started:
            from src.ai.analyze_queue import analyze_queue

            await analyze_queue.stop_cleanup_task()
        clear_shared_client()
        if client_manager:
            await client_manager.disconnect()
        display_info("Panel stopped.")
