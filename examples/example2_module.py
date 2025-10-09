'''
Example 2: Missing Module
Run: python -m autofix.cli.autofix_cli_interactive examples/example2_module.py --auto-install
'''

import requests  # If not installed, AutoFix will handle it

response = requests.get('https://api.github.com')
print(f'Status: {response.status_code}')
