#!/usr/bin/env python3
"""
Test runner for SakaiBot.
This script provides an easy way to run different types of tests.
"""

import sys
import os
from pathlib import Path
import argparse
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_system_tests():
    """Run system tests to verify installation."""
    print("Running system tests...")
    print("=" * 60)
    
    test_file = project_root / "tests" / "test_system.py"
    result = subprocess.run([sys.executable, str(test_file)], capture_output=False)
    return result.returncode


def run_unit_tests():
    """Run unit tests using pytest."""
    print("Running unit tests...")
    print("=" * 60)
    
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Install with: pip install pytest pytest-cov")
        return 1
    
    args = [
        "-v",  # Verbose output
        "--cov=src",  # Coverage for src directory
        "--cov-report=term-missing",  # Show missing lines
        str(project_root / "tests" / "unit"),
    ]
    
    return pytest.main(args)


def run_integration_tests():
    """Run integration tests."""
    print("Running integration tests...")
    print("=" * 60)
    
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Install with: pip install pytest")
        return 1
    
    args = [
        "-v",
        str(project_root / "tests" / "integration"),
    ]
    
    return pytest.main(args)


def run_all_tests():
    """Run all tests."""
    print("Running all tests...")
    print("=" * 60)
    
    results = []
    
    # Run system tests
    print("\n📦 SYSTEM TESTS")
    results.append(("System", run_system_tests()))
    
    # Run unit tests
    print("\n🧪 UNIT TESTS")
    results.append(("Unit", run_unit_tests()))
    
    # Run integration tests
    print("\n🔗 INTEGRATION TESTS")
    results.append(("Integration", run_integration_tests()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_type, returncode in results:
        status = "✅ PASSED" if returncode == 0 else "❌ FAILED"
        print(f"{test_type:15} - {status}")
        if returncode != 0:
            all_passed = False
    
    return 0 if all_passed else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run SakaiBot tests")
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["system", "unit", "integration", "all"],
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not running in a virtual environment")
        print("   Consider activating venv: source venv/bin/activate")
        print()
    
    # Run requested tests
    if args.type == "system":
        return run_system_tests()
    elif args.type == "unit":
        return run_unit_tests()
    elif args.type == "integration":
        return run_integration_tests()
    else:
        return run_all_tests()


if __name__ == "__main__":
    sys.exit(main())