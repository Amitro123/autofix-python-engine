from pathlib import Path

from autofix_core.shared.handlers.import_error_handler import ImportErrorHandler


def test_apply_fix_adds_suggested_import(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text("from time import nonexistent_function\n", encoding="utf-8")

    handler = ImportErrorHandler()
    error_message = "cannot import name 'nonexistent_function' from 'time' (unknown location)"

    _, _, details = handler.analyze_error(error_message, str(script))
    result = handler.apply_fix("ImportError", str(script), details)

    assert result is True
    assert "import time" in script.read_text(encoding="utf-8")


def test_apply_fix_returns_false_when_module_unresolvable(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text("import totally_unknown_thing_xyz\n", encoding="utf-8")

    handler = ImportErrorHandler()
    error_message = "No module named 'totally_unknown_thing_xyz'"

    _, _, details = handler.analyze_error(error_message, str(script))
    result = handler.apply_fix("ImportError", str(script), details)

    assert result is False
