# AutoFix Examples

Quick examples to try AutoFix.

## How to Run

\\\ash
# Example 1: Fix syntax error (missing colon)
python -m autofix.cli.autofix_cli_interactive examples/example1_syntax.py

# Example 2: Handle missing module
python -m autofix.cli.autofix_cli_interactive examples/example2_module.py --auto-install

# Example 3: Fix indentation
python -m autofix.cli.autofix_cli_interactive examples/example3_indent.py
\\\

## What to Expect

Each example demonstrates a different error type:
- **example1_syntax.py** - Missing colon (auto-fixed)
- **example2_module.py** - Missing import (auto-installed or stubbed)
- **example3_indent.py** - Indentation error (auto-fixed)

## After Running

Check the .bak files to see the original versions!
