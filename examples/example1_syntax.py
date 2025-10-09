'''
Example 1: Missing Colon Fix
Run: python -m autofix.cli.autofix_cli_interactive examples/example1_syntax.py
'''

x = 5

# This will fail - missing colon
if x > 3
    print('x is greater than 3')
else
    print('x is not greater than 3')
