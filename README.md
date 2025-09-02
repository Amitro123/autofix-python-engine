# AutoFix - Python Error Fixing MVP

A minimal, clean Python error fixing tool that automatically detects and fixes common Python errors.

## Features

- **Automatic Error Detection**: Parses Python exceptions into structured error objects
- **Smart Error Fixing**: Handles common error types:
  - `ModuleNotFoundError` - Installs missing packages via pip
  - `ImportError` - Adds missing imports
  - `NameError` - Creates missing functions or adds imports-placeholder only
  - `AttributeError` - Basic attribute error detection
  - `SyntaxError` - Version compatibility detection
- **CLI Interface**: Simple command-line tool for running scripts with auto-fixes
- **Logging**: Configurable logging levels (verbose, quiet modes)
- **Edge Case Handling**: Pip failures, file permissions, Python version issues

## Installation

No external dependencies required - uses only Python standard library.
Requires Python >= 3.9


```bash
# Clone and use directly
git clone <repository-url>
cd autofix-python-engine/
python cli.py script.py
```

## Usage

### Command Line

```bash
# Basic usage
python cli.py script.py

# Verbose output
python cli.py --verbose script.py

# Dry run (show what would be fixed)
python cli.py --dry-run script.py

# Quiet mode
python cli.py --quiet script.py

# Limit retry attempts
python cli.py --max-retries 5 script.py
```

### Programmatic Usage

```python
from python_fixer import PythonFixer
from error_parser import ErrorParser

# Create fixer instance
fixer = PythonFixer()

# Run script with automatic fixes
success = fixer.run_script_with_fixes("my_script.py")

# Parse errors manually
parser = ErrorParser()
parsed_error = parser.parse_exception(exception, "script.py")
```

## Architecture

- **`cli.py`**: Command-line interface and argument parsing
- **`python_fixer.py`**: Core error fixing logic and script execution
- **`error_parser.py`**: Structured error parsing and version detection
- **`logging_utils.py`**: Advanced logging with custom levels (SUCCESS/ATTEMPT), colors, JSON formatting
- **`metrics.py`**: Performance tracking, statistics, and session reporting
- **`helper_functions.py`**: Utility functions for common operations
- **`tests/`**: Unit tests covering error detection, fixing, and CLI behaviors

## Error Types Supported

1. **ModuleNotFoundError**: Automatically installs missing packages
2. **ImportError**: Adds missing import statements
3. **NameError**: Creates placeholder functions or adds imports
4. **AttributeError**: Basic detection and logging
5. **SyntaxError**: Version compatibility warnings

## Testing

```bash
# Run all tests
python -m unittest discover tests -v

# Run specific test module
python tests/test_logging_utils.py

# Run logging demo
python tests/test_logging_demo.py
```

## Example

```python
# demo_script.py with missing import
def main():
    sleep(1)  # NameError: name 'sleep' is not defined
    print("Done!")

if __name__ == "__main__":
    main()
```

```bash
$ python cli.py demo_script.py
13:45:01 - autofix.cli - INFO - Starting AutoFix for: demo_script.py
13:45:01 - autofix.python_fixer - ATTEMPT - Attempting to run script: demo_script.py
13:45:01 - autofix.error_parser - INFO - Parsed NameError: name 'sleep' is not defined
13:45:01 - autofix.python_fixer - ATTEMPT - Adding import: from time import sleep
13:45:01 - autofix.python_fixer - SUCCESS - Import added successfully
13:45:01 - autofix.python_fixer - SUCCESS - Script executed successfully!
Done!
```

## Advanced Features

### Custom Logging Levels
- **SUCCESS**: Bright green for successful operations
- **ATTEMPT**: Yellow for fix attempts
- **JSON formatting**: Structured logging for analysis tools

```python
from logging_utils import get_logger
from metrics import log_duration, record_success

logger = get_logger('autofix')
logger.success("Package installed successfully!")
logger.attempt("Trying to fix import error...")

# Time operations
with log_duration(logger, "Fixing imports"):
    run_fix()
```

### Performance Metrics
- **Operation timing**: Track how long fixes take
- **Success/failure rates**: Monitor fix effectiveness
- **Session reporting**: Comprehensive statistics

```python
from metrics import get_metrics, record_success

# Record outcomes
record_success("import_fix", duration=0.5)
record_failure("package_install", error_type="ImportError")

# Generate report
get_metrics().generate_session_report(logger)
```

## Limitations

- No AI integration (by design for MVP)
- Python-only error fixing
- Basic function generation (placeholder implementations)
- Limited syntax error auto-fixing
- Fixes are heuristic and may not always be correct

## Future Enhancements

- More sophisticated error fixing algorithms
- Support for additional error types
- Enhanced function generation
- Configuration file support
- Package publishing to PyPI
- branch strategy: Separate branches for language support (Python, JavaScript, charp)