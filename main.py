#!/usr/bin/env python3
"""
SakaiBot - Modern Telegram Userbot with AI Capabilities

Main entry point for running the bot.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)