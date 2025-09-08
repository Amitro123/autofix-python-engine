#!/usr/bin/env python3
"""
AutoFix CLI - Simple CLI entrypoint for Python error fixing

Usage:
    python -m autofix.cli script.py                # Run script with auto-fixes
    python -m autofix.cli script.py --verbose      # Verbose output
    python -m autofix.cli script.py --dry-run      # Preview fixes only
    python -m autofix.cli --help                   # Show help
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from python_fixer import PythonFixer
from logging_utils import setup_logging, get_logger
from metrics_and_reports import ReportFormatter


class AutoFixCLI:
    """Simple command-line interface for AutoFix"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file) if config_file else {}
        self.fixer = PythonFixer(config=self.config)
        self.logger = get_logger("cli")
        self.formatter = ReportFormatter(self.logger)
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from JSON/YAML file"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")
            
            content = config_path.read_text(encoding='utf-8')
            
            # Try JSON first
            if config_path.suffix.lower() == '.json':
                return json.loads(content)
            
            # Try YAML if available
            elif config_path.suffix.lower() in ['.yaml', '.yml']:
                try:
                    import yaml
                    return yaml.safe_load(content)
                except ImportError:
                    self.logger.warning("PyYAML not installed. Falling back to JSON parsing for YAML file.")
                    self.logger.info("To use YAML config files, install PyYAML: pip install pyyaml")
                    # Fallback to JSON parsing - might work for simple YAML
                    return json.loads(content)
            
            # Default to JSON parsing
            else:
                return json.loads(content)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {config_file}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading config file {config_file}: {e}")
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser"""
        parser = argparse.ArgumentParser(
            prog="autofix",
            description="Intelligent Python script runner with automatic error fixing",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m autofix.cli script.py              # Run with auto-fixes
  python -m autofix.cli script.py --verbose    # Verbose output
  python -m autofix.cli script.py --dry-run    # Preview fixes only
            """
        )
        
        parser.add_argument(
            "script_path",
            nargs="?",
            help="Python script to run with auto-fixes"
        )
        
        parser.add_argument(
            "--version",
            action="version",
            version="AutoFix 1.0.0"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress non-essential output"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without executing"
        )
        
        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximum number of retry attempts (default: 3)"
        )
        
        return parser
    
    def validate_script_path(self, script_path: str) -> Path:
        """Validate and resolve script path"""
        path = Path(script_path)
        
        if not path.exists():
            self.logger.error(f"Script not found: {script_path}")
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        if not path.is_file():
            self.logger.error(f"Path is not a file: {script_path}")
            raise ValueError(f"Path is not a file: {script_path}")
        
        if path.suffix != ".py":
            self.logger.warning(f"File doesn't have .py extension: {script_path}")
        
        return path.resolve()
    
    def print_summary(self, script_path: str, success: bool):
        """Print execution summary - delegates to formatter"""
        self.formatter.print_summary(script_path, success)
    
    def run(self, args: Optional[list] = None) -> int:
        """Main CLI entry point"""
        try:
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)
            
            # Handle case where no script is provided
            if not parsed_args.script_path:
                parser.print_help()
                return 0
            
            # Configure logging based on arguments
            setup_logging(
                verbose=parsed_args.verbose,
                quiet=parsed_args.quiet,
                use_colors=True
            )
            
            # Update fixer configuration
            self.fixer.max_retries = parsed_args.max_retries
            
            # Validate script path
            try:
                script_path = self.validate_script_path(parsed_args.script_path)
            except FileNotFoundError:
                return 1
            
            # Print banner for non-quiet mode
            if not parsed_args.quiet:
                self.formatter.print_banner(quiet_mode=parsed_args.quiet)
                self.logger.info(f"Running: {script_path}")
                self.logger.info(f"Max retries: {parsed_args.max_retries}")
                print("-" * 50)
            
            try:
                if parsed_args.dry_run:
                    self.logger.info("🔍 DRY RUN MODE - Analyzing potential fixes...")
                    self.fixer.config['dry_run'] = True
                    
                    # Show detailed analysis
                    analysis_results = self.fixer.analyze_potential_fixes(str(script_path))
                    if analysis_results:
                        self.formatter.display_analysis_results(analysis_results)
                    return 0
                
                # Run the script with automatic error fixing
                success = self.fixer.run_script_with_fixes(str(script_path))
                
                # Print summary
                if not parsed_args.quiet:
                    self.print_summary(str(script_path), success)
                
                return 0 if success else 1
            
            except KeyboardInterrupt:
                self.logger.info("\n[AutoFix] Interrupted by user")
                return 130
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return 1
                
        except SystemExit as e:
            # Handle argparse exits gracefully
            return e.code if hasattr(e, 'code') else 1
        except Exception as e:
            self.logger.error(f"CLI Error: {e}", exc_info=True)
            return 1


def main():
    """Entry point for the autofix command"""
    cli = AutoFixCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())