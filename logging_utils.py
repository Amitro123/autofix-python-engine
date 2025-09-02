"""
Centralized logging configuration for AutoFix package.
Provides consistent logging setup across all modules.
"""

import logging
import sys
import json
from typing import Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager

try:
    from colorama import Fore, Style, init
    COLORAMA_AVAILABLE = True
    init(autoreset=True)  # Initialize colorama
except ImportError:
    COLORAMA_AVAILABLE = False

# Custom log levels for AutoFix
AUTOFIX_SUCCESS = 25
AUTOFIX_ATTEMPT = 15

logging.addLevelName(AUTOFIX_SUCCESS, "SUCCESS")
logging.addLevelName(AUTOFIX_ATTEMPT, "ATTEMPT")

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(AUTOFIX_SUCCESS):
        self._log(AUTOFIX_SUCCESS, message, args, **kwargs)

def attempt(self, message, *args, **kwargs):
    if self.isEnabledFor(AUTOFIX_ATTEMPT):
        self._log(AUTOFIX_ATTEMPT, message, args, **kwargs)

logging.Logger.success = success
logging.Logger.attempt = attempt


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


class AutoFixFormatter(logging.Formatter):
    """Custom formatter with colors and consistent format"""
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        
        # Color codes for different log levels using colorama
        colors_supported = COLORAMA_AVAILABLE and use_colors

        if colors_supported:
            self.COLORS = {
                'DEBUG': Fore.CYAN,
                'INFO': Fore.GREEN,
                'WARNING': Fore.YELLOW,
                'ERROR': Fore.RED,
                'CRITICAL': Fore.RED + Style.BRIGHT,
                'SUCCESS': Fore.GREEN + Style.BRIGHT,
                'ATTEMPT': Fore.YELLOW,
            }
            self.RESET = Style.RESET_ALL
        else:
            # Fallback ANSI codes
            self.COLORS = {}
            self.RESET = ''
        
        self.use_colors = colors_supported
    
    def format(self, record: logging.LogRecord) -> str:
        # Create base format
        if record.name.startswith('autofix'):
            # Short name for autofix modules
            logger_name = record.name.split('.')[-1]
        else:
            logger_name = record.name
        
        # Format timestamp
        timestamp = self.formatTime(record, '%H:%M:%S') if not hasattr(record, 'full_timestamp') else self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # Apply colors if enabled
        if self.use_colors and record.levelname in self.COLORS:
            level_color = self.COLORS[record.levelname]
            reset = self.RESET
            
            # Special formatting for different message types
            if 'SUCCESS' in record.getMessage().upper() or 'COMPLETED' in record.getMessage().upper():
                message_color = Fore.GREEN + Style.BRIGHT if COLORAMA_AVAILABLE else '\033[1;32m'
            elif 'FAILED' in record.getMessage().upper() or 'ERROR' in record.getMessage().upper():
                message_color = Fore.RED + Style.BRIGHT if COLORAMA_AVAILABLE else '\033[1;31m'
            elif 'FIXING' in record.getMessage().upper() or 'ATTEMPTING' in record.getMessage().upper():
                message_color = Fore.YELLOW + Style.BRIGHT if COLORAMA_AVAILABLE else '\033[1;33m'
            else:
                message_color = ""
            
            formatted_message = f"{level_color}{timestamp} - {logger_name} - {record.levelname}{reset} - {message_color}{record.getMessage()}{reset}"
        else:
            formatted_message = f"{timestamp} - {logger_name} - {record.levelname} - {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            formatted_message += '\n' + self.formatException(record.exc_info)
        
        return formatted_message


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    quiet: bool = False,
    verbose: bool = False,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up centralized logging configuration for AutoFix.
    
    Args:
        level: Base logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        quiet: If True, only show warnings and errors
        verbose: If True, show debug messages
        use_colors: If True, use colored output for console
    
    Returns:
        Configured root logger for autofix
    """
    # Determine effective log level
    if quiet:
        effective_level = logging.WARNING
    elif verbose:
        effective_level = logging.DEBUG
    else:
        effective_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get or create root autofix logger
    logger = logging.getLogger('autofix')
    logger.setLevel(effective_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(effective_level)
    console_handler.setFormatter(AutoFixFormatter(use_colors=use_colors))
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files
        file_handler.setFormatter(AutoFixFormatter(use_colors=False))
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module within autofix.
    
    Args:
        name: Module name (will be prefixed with 'autofix.')
    
    Returns:
        Logger instance
    """
    if not name.startswith('autofix'):
        name = f'autofix.{name}'
    
    return logging.getLogger(name)


@contextmanager
def temporary_log_level(logger: logging.Logger, level: int):
    """
    Temporarily change log level for a specific context.
    
    Args:
        logger: Logger instance to modify
        level: Temporary log level to set
        
    Usage:
        with temporary_log_level(logger, logging.DEBUG):
            # Debug logging enabled here
            logger.debug("Detailed debugging info")
        # Original log level restored
    """
    original_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(original_level)


class ProgressLogger:
    """
    A logger wrapper for tracking progress through multi-step operations.
    
    Usage:
        progress = ProgressLogger(logger, total_steps=5)
        progress.step("Analyzing script...")
        progress.step("Installing packages...")
        # etc.
    """
    def __init__(self, logger: logging.Logger, total_steps: int):
        self.logger = logger
        self.total_steps = total_steps
        self.current_step = 0
    
    def step(self, message: str):
        """Log a progress step with percentage completion."""
        self.current_step += 1
        progress = (self.current_step / self.total_steps) * 100
        self.logger.info(f"[{progress:5.1f}%] {message}")


def configure_external_loggers(level: str = "WARNING"):
    """
    Configure external library loggers to reduce noise.
    
    Args:
        level: Log level for external libraries
    """
    external_loggers = [
        'urllib3',
        'requests',
        'pip',
        'setuptools',
        'wheel',
    ]
    
    log_level = getattr(logging, level.upper(), logging.WARNING)
    
    for logger_name in external_loggers:
        logging.getLogger(logger_name).setLevel(log_level)


def log_system_info(logger: logging.Logger):
    """Log system information for debugging purposes."""
    import platform
    import sys
    
    logger.debug("System Information:")
    logger.debug(f"  Python: {sys.version}")
    logger.debug(f"  Platform: {platform.platform()}")
    logger.debug(f"  Architecture: {platform.architecture()}")
    logger.debug(f"  Processor: {platform.processor()}")


# Convenience function for quick setup
def quick_setup(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """
    Quick logging setup for simple use cases.
    
    Args:
        verbose: Enable debug logging
        quiet: Only show warnings and errors
    
    Returns:
        Configured logger
    """
    return setup_logging(
        level="DEBUG" if verbose else "INFO",
        quiet=quiet,
        verbose=verbose
    )