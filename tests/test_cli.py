import pytest
import sys
from autofix.cli.cli_parser import create_parser

def test_parse_args_basic():
    parser = create_parser()
    args = parser.parse_args(['script.py'])
    assert args.script_path == 'script.py'
    assert not args.auto_fix
    assert not args.auto_install
    assert args.verbose == 0

def test_parse_args_with_options():
    parser = create_parser()
    args = parser.parse_args(['script.py', '--auto-fix', '--auto-install', '-v'])
    assert args.script_path == 'script.py'
    assert args.auto_fix
    assert args.auto_install
    assert args.verbose == 1
