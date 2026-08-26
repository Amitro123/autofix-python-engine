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


def test_unrecognized_error_type_is_no_match():
    code = "1 / 0\n"
    error_message = "TypeError: unsupported operand type(s)"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "no_match"
    assert result.patched_code is None
    assert result.diff is None
