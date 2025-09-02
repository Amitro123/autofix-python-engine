#!/usr / bin / env python3
"""
AutoFix CLI - Intelligent Python script runner with automatic error fixing #todo:maybe change it to support in multiple languages

Usage:
    autofix script.py                    # Run script with auto - fixes
    autofix script.py --verbose          # Verbose output
    autofix script.py --dry - run          # Show what would be fixed without executing
    autofix script.py --max - retries 5    # Set maximum retry attempts
    autofix --version                    # Show version
    autofix --help                       # Show help
"""

import argparse
import sys
import os
from pathlib import Path
import logging
from typing import Optional

# Import our AI - enhanced multi - language AutoFix functionality
from enhanced_plugin_manager import enhanced_plugin_manager

__version__ = "1.0.0"

# Module-level logger for tests
logger = logging.getLogger(__name__)


class AutoFixCLI:
    """Command - line interface for AutoFix"""

    def __init__(self):
        self.logger = self.setup_logging()
        self.plugin_manager = enhanced_plugin_manager  # Initialize plugin manager

    def setup_logging(self, level=logging.INFO):
        """Setup logging with AutoFix formatting"""
        logger = logging.getLogger("autofix")
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[AutoFix] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def create_parser(self):
        """Create command - line argument parser"""
        parser = argparse.ArgumentParser(
            prog="autofix",
            description="Intelligent Python script runner with automatic error fixing",
            epilog="Examples:\n"
            "  autofix script.py              # Run with auto - fixes\n"
            "  autofix script.py --verbose    # Verbose output\n"
            "  autofix script.py --dry - run    # Preview fixes only",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Positional arguments
        parser.add_argument(
            "script_path", nargs="?", help="Python script to run with auto-fixes"
        )

        # Optional arguments
        parser.add_argument(
            "--version", action="version", version=f"AutoFix {__version__}"
        )

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose output"
        )

        parser.add_argument(
            "--quiet", "-q", action="store_true", help="Suppress non - essential output"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without executing",
        )

        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximum number of retry attempts (default: 3)",
        )

        parser.add_argument(
            "--no-install",
            action="store_true",
            help="Disable automatic package installation",
        )

        parser.add_argument(
            "--no-create-files",
            action="store_true",
            help="Disable automatic file creation",
        )

        parser.add_argument("--config", type=str, help="Path to configuration file")

        parser.add_argument(
            "--language",
            "-l",
            type=str,
            help="Force specific language (python, csharp, nodejs, java)",
        )

        parser.add_argument(
            "--list-plugins",
            action="store_true",
            help="List available language plugins",
        )

        parser.add_argument(
            "--no-ai",
            action="store_true",
            help="Disable AI-enhanced error analysis",
        )

        return parser

    def parse_arguments(self, args=None):
        """Parse command line arguments"""
        parser = self.create_parser()
        return parser.parse_args(args)

    def validate_script_path(self, script_path: str) -> Path:
        """Validate and resolve script path"""
        path = Path(script_path)

        if not path.exists():
            self.logger.error(f"Script not found: {script_path}")
            raise FileNotFoundError(f"Script not found: {script_path}")

        if not path.is_file():
            self.logger.error(f"Path is not a file: {script_path}")
            sys.exit(1)

        if path.suffix != ".py":
            self.logger.warning(f"File doesn't have .py extension: {script_path}")

        return path.resolve()

    def load_config(self, config_path: Optional[str] = None) -> dict:
        """Load configuration from file"""
        config = {
            "max_retries": 3,
            "auto_install": True,
            "auto_create_files": True,
            "verbose": False,
        }

        # Load configuration from file if specified
        if config_path and Path(config_path).exists():
            try:
                import toml
                with open(config_path, 'r') as f:
                    file_config = toml.load(f)
                # Merge file config with defaults
                for section, values in file_config.items():
                    if section in config:
                        config[section].update(values)
                    else:
                        config[section] = values
            except Exception as e:
                self.logger.warning(f"Failed to load config from {config_path}: {e}")
        # else:
        #     # Look for default config files
        #     pass

        return config

    def print_banner(self):
        """Print AutoFix banner"""
        banner = f"""
========================================
          AutoFix v{__version__}
   Intelligent Python Error Fixer
========================================
"""
        self.logger.info(str(banner))

    def print_summary(self, script_path: str, success: bool):
        """Print execution summary"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"\n{'=' * 50}")
        self.logger.info(f"AutoFix Summary: {status}")
        self.logger.info(f"Script: {script_path}")
        self.logger.info(f"{'=' * 50}")

    def run(self, args=None):
        """Main CLI entry point"""
        parser = self.create_parser()
        args = parser.parse_args(args)

        # Handle special commands first
        if args.list_plugins:
            enhanced_plugin_manager.list_plugins()
            return 0

        # Handle case where no script is provided
        if not args.script_path:
            parser.print_help()
            return 0

        # Setup logging level
        if args.verbose:
            self.logger.setLevel(logging.DEBUG)
        elif args.quiet:
            self.logger.setLevel(logging.WARNING)

        # Load configuration
        config = self.load_config(args.config)

        # Override config with command-line args
        if hasattr(args, 'max_retries') and args.max_retries:
            config["max_retries"] = args.max_retries
        if hasattr(args, 'no_install') and args.no_install:
            config["auto_install"] = False
        if hasattr(args, 'no_create_files') and args.no_create_files:
            config["auto_create_files"] = False
        if args.verbose:
            config["verbose"] = True

        # Validate script path
        script_path = self.validate_script_path(args.script_path)

        # Detect language
        detected_language = enhanced_plugin_manager.detect_language(
            str(script_path), args.language
        )
        if not detected_language:
            supported_extensions = (
                enhanced_plugin_manager.base_manager.get_supported_extensions()
            )
            self.logger.info(f"Unsupported file type: {script_path}")
            print(
                f"[AutoFix] Supported extensions: {', '.join(supported_extensions)}"
            )
            self.logger.info("Use --language to force a specific language")
            return 1

        # Print banner for non - quiet mode
        if not args.quiet:
            self.print_banner()
            self.logger.info(f"Running: {script_path}")
            self.logger.info(f"Language: {detected_language}")
            self.logger.info(f"Max retries: {config['max_retries']}")
            print(
                f"Auto - install: {'enabled' if config['auto_install'] else 'disabled'}"
            )
            self.logger.info(f"Auto-create files: {'enabled' if config['auto_create_files'] else 'disabled'}")
            print("-" * 50)

        try:
            if hasattr(args, 'dry_run') and args.dry_run:
                self.logger.info("DRY RUN MODE - No changes will be made")
                print(f"[AutoFix] Would run: {script_path} ({detected_language})")
                return 0

            # Run the script with AI - enhanced multi - language AutoFix or
            # traditional fallback
            import asyncio

            if args.no_ai:
                # Use traditional fallback only
                from prototype import run_script

                try:
                    run_script(str(script_path))
                    success = True
                except Exception:
                    success = False
            else:
                # Use AI - enhanced mode
                success = asyncio.run(
                    enhanced_plugin_manager.run_script_with_ai_autofix(
                        str(script_path), detected_language, config["max_retries"]
                    )
                )

            # Print summary
            if not args.quiet:
                self.print_summary(str(script_path), success)

            return 0 if success else 1

        except KeyboardInterrupt:
            self.logger.info("\n[AutoFix] Interrupted by user")
            return 130
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return 1


def main():
    """Entry point for the autofix command"""
    cli = AutoFixCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())