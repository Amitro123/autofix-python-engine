# AutoFix Demos

Example scripts to demonstrate AutoFix capabilities.

## Usage

\\\ash
# Run any demo with AutoFix:
python -m autofix.cli.autofix_cli_interactive demos/demo_missing_module.py --auto-install
\\\

## Demos

1. **demo_missing_module.py** - Missing numpy module
2. **demo_syntax_error.py** - Missing colon after function definition
3. **demo_index_error.py** - List index out of range
4. **demo_type_error.py** - String concatenation with integer

## Expected Results

### demo_missing_module.py
- Detects: ModuleNotFoundError
- Fixes: Installs numpy automatically
- Output: Mean and standard deviation

### demo_syntax_error.py
- Detects: SyntaxError (missing colon)
- Suggests: Add colon after function definition
- Note: Manual fix required

### demo_index_error.py
- Detects: IndexError
- Suggests: Check array bounds
- Note: Manual fix required

### demo_type_error.py
- Detects: TypeError
- Suggests: Convert int to string
- Note: Manual fix required
