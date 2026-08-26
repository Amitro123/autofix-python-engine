from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error


def test_import_error_with_no_auto_fix_available_downgrades_to_a_suggestion():
    # 'flask' is a known pip package (KNOWN_PIP_PACKAGES) but is not one of
    # the small set of names ImportErrorHandler can auto-add an import
    # statement for (IMPORT_SUGGESTIONS), so fix_parsed_error returns False
    # here -- but the handler still knows exactly what to suggest. Before
    # the fix this silently became resolved_by="no_match" with nothing
    # returned, discarding guidance the handler had already computed.
    code = "from flask import something_that_does_not_exist\n"
    error_message = (
        "ImportError: cannot import name 'something_that_does_not_exist' "
        "from 'flask' (unknown location)"
    )

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "ImportError"
    assert result.suggestions
    assert any("pip install flask" in s for s in result.suggestions)
    assert result.patched_code is None


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
    # A name with no known import mapping at all -- neither IMPORT_SUGGESTIONS/
    # MATH_FUNCTIONS (confident, now fix-tier) nor MULTI_IMPORT_SUGGESTIONS/the
    # os.path heuristic (ambiguous, still suggestion-tier) -- so this stays a
    # plain suggestion with generic guidance.
    code = "print(totally_unrecognized_name())\n"
    error_message = "NameError: name 'totally_unrecognized_name' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "NameError"
    assert any("totally_unrecognized_name" in s for s in result.suggestions)
    assert result.patched_code is None
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_name_error_with_confident_dict_import_produces_a_fix():
    code = "print(Counter([1, 1, 2]))\n"
    error_message = "NameError: name 'Counter' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "fix"
    assert result.error_type == "NameError"
    assert result.patched_code is not None
    assert "from collections import Counter" in result.patched_code
    assert result.diff is not None
    assert "+from collections import Counter" in result.diff
    assert result.telemetry["estimated_tokens_saved"] > 0


def test_name_error_with_confident_math_function_produces_a_fix():
    code = "x = sqrt(4)\n"
    error_message = "NameError: name 'sqrt' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "fix"
    assert result.error_type == "NameError"
    assert "from math import sqrt" in result.patched_code
    assert result.telemetry["estimated_tokens_saved"] > 0


def test_name_error_with_ambiguous_import_stays_a_suggestion():
    # "dump" maps to json.dump or pickle.dump (MULTI_IMPORT_SUGGESTIONS) --
    # not confident enough to auto-apply either one.
    code = "dump(data, f)\n"
    error_message = "NameError: name 'dump' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.patched_code is None
    assert any("json" in s for s in result.suggestions)
    assert any("pickle" in s for s in result.suggestions)
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_name_error_with_heuristic_match_stays_a_suggestion():
    # "isfile" only matches via the is*file naming heuristic, not a
    # confirmed IMPORT_SUGGESTIONS/MATH_FUNCTIONS entry -- stays a guess,
    # not an auto-applied fix.
    code = "if isfile(path):\n    pass\n"
    error_message = "NameError: name 'isfile' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.patched_code is None
    assert any("isfile" in s for s in result.suggestions)
    assert result.telemetry["estimated_tokens_saved"] == 0


def test_name_error_fix_skips_when_import_already_present():
    # The import is already there and NameError still fired somehow (e.g.
    # a contrived/stale report) -- applying it "again" would be a no-op
    # patch that hides whatever the real problem is. Must fall back to a
    # suggestion, not silently claim a fix that changes nothing.
    code = "from math import sqrt\nx = sqrt(4)\n"
    error_message = "NameError: name 'sqrt' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.patched_code is None
