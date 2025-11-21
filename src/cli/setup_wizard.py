"""Interactive setup wizard for SakaiBot."""

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

console = Console()

def run_setup_wizard():
    """Guides the user through the initial configuration process."""
    console.print(Panel(
        Text("Welcome to the SakaiBot Setup Wizard!", justify="center", style="bold cyan"),
        title="SakaiBot Setup",
        border_style="green"
    ))

    console.print("\nThis wizard will help you create your .env file with the necessary credentials.")
    console.print("You can press Ctrl+C at any time to exit.\n")

    # 1. Get Telegram Credentials
    console.print(Panel("Step 1: Telegram API Credentials", style="bold yellow"))
    console.print("You can get these from my.telegram.org.")

    api_id = Prompt.ask("[cyan]Enter your Telegram API ID[/cyan]")
    api_hash = Prompt.ask("[cyan]Enter your Telegram API Hash[/cyan]")
    phone_number = Prompt.ask("[cyan]Enter your Telegram Phone Number (with country code)[/cyan]")

    # 2. Get LLM Provider
    console.print(Panel("Step 2: AI Provider Configuration", style="bold yellow"))
    llm_provider = Prompt.ask(
        "[cyan]Choose your LLM provider[/cyan]",
        choices=["gemini", "openrouter"],
        default="gemini"
    )

    # 3. Get API Key
    api_key = ""
    if llm_provider == "gemini":
        api_key = Prompt.ask("[cyan]Enter your Google Gemini API Key[/cyan]")
    else:
        api_key = Prompt.ask("[cyan]Enter your OpenRouter API Key[/cyan]")

    # 4. Create .env file content
    env_content = f"""# Telegram API Credentials
TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}
TELEGRAM_PHONE_NUMBER={phone_number}

# LLM Provider Selection
LLM_PROVIDER={llm_provider}
"""

    if llm_provider == "gemini":
        env_content += f"GEMINI_API_KEY={api_key}\n"
    else:
        env_content += f"OPENROUTER_API_KEY={api_key}\n"

    # 5. Confirm and Save
    console.print("\n" + "="*50)
    console.print(Text("Configuration Summary", justify="center", style="bold green"))
    console.print(env_content)
    console.print("="*50 + "\n")

    if Confirm.ask("[cyan]Do you want to save this configuration to .env?[/cyan]", default=True):
        try:
            with open(".env", "w") as f:
                f.write(env_content)
            console.print("\n[green]✅ .env file created successfully![/green]")
            console.print("You can now start the bot with 'sakaibot monitor start'.")
        except IOError as e:
            console.print(f"\n[red]Error: Failed to write .env file: {e}[/red]")
    else:
        console.print("\n[yellow]Setup cancelled. No changes were made.[/yellow]")

if __name__ == '__main__':
    run_setup_wizard()
