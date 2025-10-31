"""Configuration management commands."""

import click
import os
from pathlib import Path
from rich.table import Table
from rich.syntax import Syntax
from ..utils import (
    display_error, display_success, display_info, display_warning,
    confirm_action, console
)

@click.group()
def config():
    """Manage bot configuration."""
    pass

@config.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all configuration values')
def show(show_all):
    """Display current configuration."""
    try:
        from src.core.config import get_settings
        
        config = get_settings()
        
        # Create configuration table
        table = Table(title="SakaiBot Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Setting", style="green", width=25)
        table.add_column("Value", width=40)
        
        # Telegram settings
        table.add_row("Telegram", "API ID", str(config.telegram_api_id))
        table.add_row("", "API Hash", config.telegram_api_hash[:10] + "..." if len(config.telegram_api_hash) > 15 else "***")
        table.add_row("", "Phone Number", config.telegram_phone_number)
        table.add_row("", "Session Name", config.telegram_session_name)
        
        # LLM settings
        table.add_row("LLM", "Provider", config.llm_provider.title())
        
        if config.llm_provider == "gemini":
            table.add_row("", "Gemini Model", config.gemini_model)
            if config.gemini_api_key:
                key_display = config.gemini_api_key[:10] + "..." if show_all else "***"
                table.add_row("", "Gemini API Key", key_display)
        elif config.llm_provider == "openrouter":
            table.add_row("", "OpenRouter Model", config.openrouter_model)
            if config.openrouter_api_key:
                key_display = config.openrouter_api_key[:10] + "..." if show_all else "***"
                table.add_row("", "OpenRouter API Key", key_display)
        
        # UserBot settings
        table.add_row("UserBot", "Max Analyze Messages", str(config.userbot_max_analyze_messages))
        
        # Paths
        if config.paths_ffmpeg_executable:
            table.add_row("Paths", "FFmpeg", config.paths_ffmpeg_executable)
        
        # Environment
        table.add_row("Environment", "Environment", config.environment)
        table.add_row("", "Debug Mode", str(config.debug))
        
        console.print(table)
        
        # Show file locations
        console.print("\n[bold cyan]Configuration Files:[/bold cyan]")
        console.print(f"  • Main config: {Path('.env').absolute()}")
        console.print(f"  • User settings: {Path('data/sakaibot_user_settings.json').absolute()}")
        console.print(f"  • Session: {Path('data/' + config.telegram_session_name + '.session').absolute()}")
        
        if not show_all:
            display_info("Use --all to show full configuration values")
        
    except Exception as e:
        display_error(f"Failed to show configuration: {e}")

@config.command()
def validate():
    """Validate configuration settings."""
    try:
        from src.core.config import get_settings
        
        errors = []
        warnings = []
        successes = []
        
        try:
            config = get_settings()
            successes.append("Configuration loaded successfully")
        except Exception as e:
            display_error(f"Failed to load configuration: {e}")
            return
        
        # Check Telegram settings
        if config.telegram_api_id and config.telegram_api_id > 0:
            successes.append("Telegram API ID is valid")
        else:
            errors.append("Invalid Telegram API ID")
        
        if config.telegram_api_hash and len(config.telegram_api_hash) > 10:
            successes.append("Telegram API Hash is present")
        else:
            errors.append("Invalid Telegram API Hash")
        
        if config.telegram_phone_number and config.telegram_phone_number.startswith("+"):
            successes.append("Phone number format is valid")
        else:
            errors.append("Phone number must start with +")
        
        # Check LLM configuration
        if config.llm_provider in ["openrouter", "gemini"]:
            successes.append(f"LLM provider '{config.llm_provider}' is valid")
            
            if config.is_ai_enabled:
                successes.append(f"{config.llm_provider.title()} API key is configured")
            else:
                warnings.append(f"{config.llm_provider.title()} API key is not configured (AI features disabled)")
        else:
            errors.append(f"Unknown LLM provider: {config.llm_provider}")
        
        # Check paths
        if config.paths_ffmpeg_executable:
            path = Path(config.paths_ffmpeg_executable)
            if path.exists() or config.paths_ffmpeg_executable.startswith("C:\\"):
                successes.append("FFmpeg path is configured")
            else:
                warnings.append(f"FFmpeg not found at: {config.paths_ffmpeg_executable}")
        else:
            warnings.append("FFmpeg path not configured (audio features may not work)")
        
        # Check directories
        directories = {
            "data": Path("data"),
            "cache": Path("cache"),
            "logs": Path("logs")
        }
        
        for name, path in directories.items():
            if path.exists():
                successes.append(f"Directory '{name}/' exists")
            else:
                warnings.append(f"Directory '{name}/' does not exist (will be created)")
        
        # Display results
        if successes:
            console.print("\n[bold green]✓ Valid:[/bold green]")
            for msg in successes:
                console.print(f"  • {msg}")
        
        if warnings:
            console.print("\n[bold yellow]⚠ Warnings:[/bold yellow]")
            for msg in warnings:
                console.print(f"  • {msg}")
        
        if errors:
            console.print("\n[bold red]✗ Errors:[/bold red]")
            for msg in errors:
                console.print(f"  • {msg}")
            display_error("Configuration has errors that need to be fixed")
        else:
            display_success("Configuration is valid!")
        
    except Exception as e:
        display_error(f"Validation failed: {e}")

@config.command()
def edit():
    """Open configuration file in default editor."""
    try:
        env_path = Path(".env")
        
        if not env_path.exists():
            display_error(".env file not found")
            return
        
        # Try to open in default editor
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            os.startfile(str(env_path))
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(env_path)])
        else:  # Linux
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(env_path)])
        
        display_success(f"Opened {env_path} in editor")
        
    except Exception as e:
        display_error(f"Failed to open editor: {e}")
        display_info(f"You can manually edit: {Path('.env').absolute()}")

@config.command()
def example():
    """Show example configuration."""
    example_config = """
# Telegram Configuration
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890
TELEGRAM_SESSION_NAME=sakaibot_session

# LLM Provider Configuration
LLM_PROVIDER=gemini  # or openrouter

# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY_TTS=your_gemini_tts_api_key_here  # Optional: TTS-specific key (priority over GEMINI_API_KEY)
GEMINI_MODEL=gemini-2.5-flash

# OpenRouter Configuration (Alternative)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash

# UserBot Configuration
USERBOT_MAX_ANALYZE_MESSAGES=10000

# Paths
PATHS_FFMPEG_EXECUTABLE=/usr/local/bin/ffmpeg

# Environment
ENVIRONMENT=production
DEBUG=false
"""
    
    syntax = Syntax(example_config, "bash", theme="monokai", line_numbers=True)
    console.print("\n[bold cyan]Example .env Configuration:[/bold cyan]")
    console.print(syntax)
    
    display_info("Copy and modify this example to create your .env file")