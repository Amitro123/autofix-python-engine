"""Regression tests for ModuleNotFoundError in the MCP fix_error adapter.

ModuleNotFoundError previously fell straight through to resolved_by="no_match"
-- it's excluded from the "fix" tier on purpose (its real fix is a side
effect: pip install or creating a new file, not a diff of the input code,
and this tool is read-only by design), but that's no reason to also drop
the text guidance ModuleNotFoundHandler.analyze_error already computes.
"""

from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error


def test_module_not_found_returns_pip_suggestion_for_known_package():
    result = run_fix_error(
        code="import requests\n",
        error_message="ModuleNotFoundError: No module named 'requests'",
    )
    assert result.resolved_by == "suggestion"
    assert result.suggestions
    assert any("pip install requests" in s for s in result.suggestions)


def test_module_not_found_unrecognized_module_suggests_creating_it_locally():
    # ModuleNotFoundHandler.analyze_error (reused here rather than
    # duplicated) does not blindly suggest `pip install <anything>` for a
    # name it doesn't recognize as a real package -- that could be bad
    # advice for a typo or an intentionally-local module name. For a name
    # that isn't a known package, isn't stdlib, and doesn't look like a
    # test/placeholder module, its real, already-tested behavior is to
    # suggest creating it locally.
    result = run_fix_error(
        code="import totally_custom_widget_lib\n",
        error_message="ModuleNotFoundError: No module named 'totally_custom_widget_lib'",
    )
    assert result.resolved_by == "suggestion"
    assert result.suggestions
    assert any("Create local module: totally_custom_widget_lib.py" in s for s in result.suggestions)


def test_module_not_found_without_extractable_module_name_is_no_match():
    # Degenerate message with no quoted module name -- nothing to suggest.
    result = run_fix_error(
        code="import something\n",
        error_message="ModuleNotFoundError: No module named",
    )
    assert result.resolved_by == "no_match"
