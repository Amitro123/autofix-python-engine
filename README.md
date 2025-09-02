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
cd autofix/
python -m cli script.py
```

## Usage

### Command Line

```bash
# Basic usage
python -m autofix.cli script.py

# Verbose output
python -m autofix.cli --verbose script.py

# Dry run (show what would be fixed)
python -m autofix.cli --dry-run script.py

# Quiet mode
python -m autofix.cli --quiet script.py

# Limit retry attempts
python -m autofix.cli --max-retries 5 script.py
```

### Programmatic Usage

```python
from autofix import PythonFixer, ErrorParser

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
- **`logging_utils.py`**: Centralized logging configuration with colored output
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
python -m pytest autofix/tests/ -v

# Run specific test module
python -m pytest autofix/tests/test_python_fixer.py -v
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
$ python -m autofix.cli demo_script.py
[AutoFix] Running: demo_script.py
[AutoFix] Error detected: NameError: name 'sleep' is not defined
[AutoFix] Adding import: from time import sleep
[AutoFix] Error fixed, retrying script execution...
[AutoFix] Script executed successfully!
Done!
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