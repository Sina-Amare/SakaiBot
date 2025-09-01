#!/usr/bin/env python3
"""
Setup script to help users configure SakaiBot for first use.
"""

import os
from pathlib import Path
import shutil


def main():
    """Set up configuration for SakaiBot."""
    print("🤖 SakaiBot Configuration Setup")
    print("=" * 40)
    
    # Check if config already exists
    config_path = Path("data/config.ini")
    if config_path.exists():
        print("✅ Configuration file already exists at data/config.ini")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Keeping existing configuration.")
            return
    
    # Copy example config
    example_path = Path("config.ini.example")
    if not example_path.exists():
        print("❌ config.ini.example not found!")
        print("Please make sure you're running this from the project root directory.")
        return
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Copy the example
    shutil.copy(example_path, config_path)
    print(f"✅ Copied {example_path} to {config_path}")
    
    print("\n📝 Next Steps:")
    print("1. Edit data/config.ini with your credentials:")
    print("   - Get Telegram API ID/Hash from https://my.telegram.org/")
    print("   - Get OpenRouter API key from https://openrouter.ai/")
    print("   - Add your phone number with country code")
    
    print("\n2. Required fields to fill in:")
    print("   [Telegram]")
    print("   api_id = YOUR_API_ID")
    print("   api_hash = YOUR_API_HASH") 
    print("   phone_number = +1234567890")
    print()
    print("   [OpenRouter]")
    print("   api_key = YOUR_OPENROUTER_KEY")
    
    print("\n3. After configuration, run:")
    print("   python -m src.main --debug")
    
    print("\n🔍 Optional: Use environment variables instead:")
    print("   cp .env.example .env")
    print("   # Edit .env with your credentials")
    
    # Check if .env.example exists and offer to copy it too
    env_example = Path(".env.example")
    if env_example.exists():
        create_env = input("\nCreate .env file from example? (y/N): ").lower().strip()
        if create_env == 'y':
            if not Path(".env").exists():
                shutil.copy(env_example, ".env")
                print("✅ Created .env from .env.example")
                print("📝 Don't forget to edit .env with your actual credentials!")
            else:
                print("⚠️  .env already exists, skipping.")


if __name__ == "__main__":
    main()