"""Main CLI entry point for SakaiBot."""

import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.commands import pv, group, auth, monitor, ai, config
from src.cli.utils import setup_environment, display_banner
from src.cli.interactive import start_interactive_menu

console = Console()

@click.group(invoke_without_command=True)
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config-file', type=click.Path(exists=True), help='Path to config file')
@click.pass_context
def cli(ctx, debug, config_file):
    """
    SakaiBot - Advanced Telegram Userbot with AI Capabilities
    
    Use 'sakaibot COMMAND --help' for more information on a command.
    """
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    ctx.obj['CONFIG_FILE'] = config_file
    
    # Setup environment
    setup_environment(debug, config_file)
    
    # If no command provided, offer interactive menu or status
    if ctx.invoked_subcommand is None:
        display_banner()
        
        # Ask user if they want interactive menu or just status
        console.print("\n[cyan]Would you like to:[/cyan]")
        console.print("  [1] 🎛️  Interactive Menu (navigate with numbers)")
        console.print("  [2] 📊 Show Status (default)")
        console.print("  [3] 🚪 Exit")
        
        try:
            choice = input("\nEnter choice (1/2/3) [2]: ").strip() or "2"
            if choice == "1":
                # Start interactive menu
                console.print("[green]Starting interactive menu...[/green]")
                asyncio.run(start_interactive_menu())
                return
            elif choice == "3":
                console.print("[cyan]Goodbye! 👋[/cyan]")
                return
            else:
                # Show status (default)
                show_status()
        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye! 👋[/cyan]")
            return

def show_status():
    """Display current bot status."""
    try:
        from src.core.config import get_settings
        from src.core.settings import SettingsManager
        
        config = get_settings()
        settings_manager = SettingsManager()
        settings = settings_manager.load_user_settings()
        
        # Create status table
        table = Table(title="🤖 SakaiBot Status", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="cyan", width=20)
        table.add_column("Status", width=30)
        table.add_column("Details", style="dim")
        
        # System status
        table.add_row(
            "System",
            "[green]✓ Configured[/green]",
            f"Session: {config.telegram_session_name}"
        )
        
        # AI Provider status
        ai_status = "[green]✓ Active[/green]" if config.is_ai_enabled else "[red]✗ Not configured[/red]"
        ai_details = f"Provider: {config.llm_provider.title()}"
        if config.llm_provider == "gemini":
            ai_details += f" | Model: {config.gemini_model}"
        elif config.llm_provider == "openrouter":
            ai_details += f" | Model: {config.openrouter_model}"
        
        table.add_row("AI Provider", ai_status, ai_details)
        
        # Categorization status
        target_group = settings.get('selected_target_group')
        mappings = settings.get('active_command_to_topic_map', {})
        cat_status = "[green]✓ Configured[/green]" if target_group and mappings else "[yellow]⚠ Partial[/yellow]"
        cat_details = f"Group: {target_group if target_group else 'None'} | Mappings: {len(mappings)}"
        
        table.add_row("Categorization", cat_status, cat_details)
        
        # Authorization status
        auth_pvs = settings.get('directly_authorized_pvs', [])
        auth_details = f"Authorized users: {len(auth_pvs)}"
        
        table.add_row("Authorization", f"[blue]{len(auth_pvs)} users[/blue]", auth_details)
        
        # Cache status
        from pathlib import Path
        pv_cache = Path("cache/pv_cache.json")
        group_cache = Path("cache/group_cache.json")
        
        cache_details = []
        if pv_cache.exists():
            cache_details.append("PV cache: ✓")
        if group_cache.exists():
            cache_details.append("Group cache: ✓")
        
        cache_status = "[green]✓ Available[/green]" if cache_details else "[yellow]⚠ Empty[/yellow]"
        table.add_row("Cache", cache_status, " | ".join(cache_details) if cache_details else "No cache files")
        
        console.print(table)
        
        # Show quick commands
        console.print("\n[bold cyan]Quick Commands:[/bold cyan]")
        console.print("  • sakaibot monitor start    - Start monitoring")
        console.print("  • sakaibot pv list          - List private chats")
        console.print("  • sakaibot group set        - Set target group")
        console.print("  • sakaibot --help           - Show all commands")
        
    except Exception as e:
        console.print(f"[red]Error loading status: {e}[/red]")

# Add command groups
cli.add_command(pv.pv)
cli.add_command(group.group)
cli.add_command(auth.auth)
cli.add_command(monitor.monitor)
cli.add_command(ai.ai)
cli.add_command(config.config)

# Add status command
@cli.command()
@click.pass_context
def status(ctx):
    """Show current bot status and configuration."""
    show_status()

# Add interactive menu command
@cli.command()
@click.pass_context
def menu(ctx):
    """Start interactive menu system."""
    asyncio.run(start_interactive_menu())

# Add setup wizard
@cli.command()
@click.pass_context
def setup(ctx):
    """Run interactive setup wizard."""
    # TODO: Implement setup wizard
    console.print("[yellow]Setup wizard coming soon![/yellow]")
    console.print("Please edit .env file manually for now.")

if __name__ == '__main__':
    cli()