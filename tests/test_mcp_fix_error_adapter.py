from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error


def test_import_error_produces_a_fix():
    code = "from time import nonexistent_function\n"
    error_message = "ImportError: cannot import name 'nonexistent_function' from 'time' (unknown location)"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "fix"
    assert result.error_type == "ImportError"
    assert result.patched_code is not None
    assert "import time" in result.patched_code
    assert result.diff is not None
    assert "+import time" in result.diff or "+ import time" in result.diff
    assert result.telemetry["estimated_tokens_saved"] > 0


def test_unrecognized_error_type_is_no_match():
    code = "1 / 0\n"
    error_message = "TypeError: unsupported operand type(s)"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "no_match"
    assert result.patched_code is None
    assert result.diff is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_index_error_produces_a_suggestion():
    code = "items = [1, 2]\nprint(items[5])\n"
    error_message = "IndexError: list index out of range"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "IndexError"
    assert result.suggestions
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_key_error_produces_a_suggestion():
    code = "d = {'a': 1}\nprint(d['b'])\n"
    error_message = "KeyError: 'b'"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "KeyError"
    assert result.suggestions
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_zero_division_error_produces_a_suggestion():
    code = "x = 1 / 0\n"
    error_message = "ZeroDivisionError: division by zero"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "ZeroDivisionError"
    assert result.suggestions
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_value_error_produces_a_suggestion():
    code = "x = int('abc')\n"
    error_message = "ValueError: invalid literal for int() with base 10: 'abc'"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "ValueError"
    assert result.suggestions
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_file_not_found_error_produces_a_suggestion():
    code = "with open('data.txt') as f:\n    f.read()\n"
    error_message = "FileNotFoundError: [Errno 2] No such file or directory: 'data.txt'"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "FileNotFoundError"
    assert result.suggestions
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_name_error_produces_a_suggestion_with_the_actual_name():
    code = "print(sqrt(4))\n"
    error_message = "NameError: name 'sqrt' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "NameError"
    assert any("sqrt" in s or "math" in s for s in result.suggestions)
    assert result.telemetry["estimated_tokens_saved"] == 0
