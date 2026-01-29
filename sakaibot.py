#!/usr/bin/env python3
"""
SakaiBot CLI - Modern command-line interface for SakaiBot

This is the new CLI entry point with enhanced features and better user experience.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.cli.main import cli

if __name__ == '__main__':
        cli()
    