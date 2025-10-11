import argparse

def create_parser():
    """Create unified argument parser for AutoFix CLI"""
    parser = argparse.ArgumentParser(
        prog="autofix",
        description="AutoFix Python Engine - Intelligent script runner with automatic error fixing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autofix_cli_interactive.py script.py              # Interactive mode (default)
  python autofix_cli_interactive.py script.py --auto-fix   # Auto-fix with prompts
  python autofix_cli_interactive.py script.py --batch --auto-install  # Full automation
  python autofix_cli_interactive.py script.py --dry-run -vv    # Preview fixes with debug
        """
    )
    
    # Required arguments
    parser.add_argument(
        "script_path",
        nargs="?",
        help="Python script to run with auto-fixes"
    )
    
    # Mode selection
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="Run in batch mode (non-interactive)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (default)"
    )
    
    # Fix behavior
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically apply fixes without asking"
    )
    
    parser.add_argument(
        "--dry-run",  # מcli.py - פיצ'ר מעולה!
        action="store_true",
        help="Show what would be fixed without executing"
    )
    
    # Package installation
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install missing packages without asking"
    )
    
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Never install packages, only suggest fixes"
    )
    
    # Retry behavior
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts (default: 3)"
    )
    
    # Output control
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity level (-v, -vv, -vvv)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-essential output"
    )
    
    # Utility
    parser.add_argument(
        "--version",
        action="version",
        version="AutoFix Python Engine v2.1.0"
    )
    
    return parser

def validate_args(args):
    #Mutual exclusivity 
    if args.auto_install and args.no_install:
        return "Error: --auto-install and --no-install are mutually exclusive"

    if args.max_retries < 1:
        return "Error: --max-retries must be positive"
    
    if args.max_retries > 10:
        return "Warning: --max-retries > 10 might be excessive"
    
    return None

def validate_script_path(script_path: str, logger):
    from pathlib import Path
    
    path = Path(script_path)
    if not path.exists():
        logger.error(f"Script not found: {script_path}")
        return False
    
    if not path.is_file():
        logger.error(f"Path is not a file: {script_path}")
        return False
    
    if path.suffix != ".py":
        logger.warning(f"File doesn't have .py extension: {script_path}")
    
    return True
