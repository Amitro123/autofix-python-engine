from autofix_core.shared.core.error_parser import ErrorParser


def test_parse_error_extracts_name_error_missing_function():
    parser = ErrorParser()
    output = (
        'Traceback (most recent call last):\n'
        '  File "script.py", line 3, in <module>\n'
        '    print(sqrt(4))\n'
        "NameError: name 'sqrt' is not defined\n"
    )

    parsed = parser.parse_error(output)

    assert parsed.error_type == "NameError"
    assert parsed.missing_function == "sqrt"
