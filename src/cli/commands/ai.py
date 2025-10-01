"""AI-related commands."""

import click
import asyncio
from rich.table import Table
from rich.panel import Panel
from ..utils import (
    display_error, display_success, display_info,
    ProgressSpinner, prompt_text, console
)

@click.group()
def ai():
    """AI provider management and testing."""
    pass

@ai.command()
@click.option('--prompt', default="Hello, please respond with 'AI is working!'", help='Test prompt')
def test(prompt):
    """Test AI configuration with a simple prompt."""
    asyncio.run(_test_ai(prompt))

async def _test_ai(prompt: str):
    """Test AI implementation."""
    try:
        from src.core.config import get_settings
        from src.ai.processor import AIProcessor
        
        config = get_settings()
        
        if not config.is_ai_enabled:
            display_error(f"{config.llm_provider.title()} is not properly configured")
            display_info("Check your API key in .env file")
            return
        
        ai_processor = AIProcessor(config)
        
        display_info(f"Testing {ai_processor.provider_name} with model {ai_processor.model_name}")
        
        with ProgressSpinner("Sending test prompt...") as spinner:
            try:
                response = await ai_processor.execute_custom_prompt(
                    user_prompt=prompt,
                    max_tokens=100
                )
                spinner.update("Response received!")
            except Exception as e:
                display_error(f"AI test failed: {e}")
                return
        
        console.print("\n[bold cyan]AI Response:[/bold cyan]")
        console.print(Panel(response, border_style="green"))
        
        display_success(f"{ai_processor.provider_name} is working correctly!")
        
    except Exception as e:
        display_error(f"Failed to test AI: {e}")

@ai.command()
def config():
    """Show current AI configuration."""
    asyncio.run(_show_ai_config())

async def _show_ai_config():
    """Show AI configuration implementation."""
    try:
        from src.core.config import get_settings
        
        config = get_settings()
        
        # Create configuration table
        table = Table(title="AI Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", width=40)
        
        # Provider
        table.add_row("Provider", config.llm_provider.title())
        
        # Provider-specific settings
        if config.llm_provider == "gemini":
            table.add_row("Model", config.gemini_model)
            api_key = config.gemini_api_key
            if api_key:
                masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 20 else "***"
                table.add_row("API Key", masked_key)
            else:
                table.add_row("API Key", "[red]Not configured[/red]")
        
        elif config.llm_provider == "openrouter":
            table.add_row("Model", config.openrouter_model)
            api_key = config.openrouter_api_key
            if api_key:
                masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 20 else "***"
                table.add_row("API Key", masked_key)
            else:
                table.add_row("API Key", "[red]Not configured[/red]")
        
        # Status
        if config.is_ai_enabled:
            table.add_row("Status", "[green]✓ Configured[/green]")
        else:
            table.add_row("Status", "[red]✗ Not configured[/red]")
        
        console.print(table)
        
        # Additional services
        console.print("\n[bold cyan]Additional Services:[/bold cyan]")
        
        services = []
        if config.assemblyai_api_key:
            services.append("• AssemblyAI (STT): [green]✓ Configured[/green]")
        else:
            services.append("• AssemblyAI (STT): [dim]Not configured[/dim]")
        
        if config.elevenlabs_api_key:
            services.append("• ElevenLabs (TTS): [green]✓ Configured[/green]")
        else:
            services.append("• ElevenLabs (TTS): [dim]Not configured[/dim]")
        
        for service in services:
            console.print(service)
        
    except Exception as e:
        display_error(f"Failed to show AI config: {e}")

@ai.command()
@click.argument('text')
@click.argument('target_language')
@click.option('--source', default='auto', help='Source language (default: auto)')
def translate(text, target_language, source):
    """Translate text using AI."""
    asyncio.run(_translate_text(text, target_language, source))

async def _translate_text(text: str, target_language: str, source: str):
    """Translate text implementation."""
    try:
        from src.core.config import get_settings
        from src.ai.processor import AIProcessor
        
        config = get_settings()
        
        if not config.is_ai_enabled:
            display_error(f"{config.llm_provider.title()} is not properly configured")
            return
        
        ai_processor = AIProcessor(config)
        
        with ProgressSpinner(f"Translating to {target_language}...") as spinner:
            response = await ai_processor.translate_text_with_phonetics(
                text_to_translate=text,
                target_language=target_language,
                source_language=source
            )
        
        console.print("\n[bold cyan]Translation:[/bold cyan]")
        console.print(Panel(response, border_style="green"))
        
    except Exception as e:
        display_error(f"Translation failed: {e}")

@ai.command()
@click.argument('prompt')
@click.option('--max-tokens', default=1500, help='Maximum response tokens')
@click.option('--temperature', default=0.7, help='Response creativity (0.0-1.0)')
def prompt(prompt, max_tokens, temperature):
    """Send a custom prompt to AI."""
    asyncio.run(_send_prompt(prompt, max_tokens, temperature))

async def _send_prompt(prompt: str, max_tokens: int, temperature: float):
    """Send prompt implementation."""
    try:
        from src.core.config import get_settings
        from src.ai.processor import AIProcessor
        
        config = get_settings()
        
        if not config.is_ai_enabled:
            display_error(f"{config.llm_provider.title()} is not properly configured")
            return
        
        ai_processor = AIProcessor(config)
        
        with ProgressSpinner("Processing prompt...") as spinner:
            response = await ai_processor.execute_custom_prompt(
                user_prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
        
        console.print("\n[bold cyan]AI Response:[/bold cyan]")
        console.print(Panel(response, border_style="green"))
        
    except Exception as e:
        display_error(f"Prompt failed: {e}")