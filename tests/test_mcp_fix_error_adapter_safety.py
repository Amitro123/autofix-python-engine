"""Regression tests locking in the fix-tier adapter's core safety
invariants: no temp-file or backup-file residue, no caller-overridable
auto_install/create_files, and the caller's real file is never touched.
"""

import tempfile
from pathlib import Path

import pytest

from autofix_core.infrastructure.cli.python_fixer import PythonFixer
from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error

IMPORT_ERROR_CODE = "from time import nonexistent_function\n"
IMPORT_ERROR_MESSAGE = (
    "ImportError: cannot import name 'nonexistent_function' from 'time' (unknown location)"
)


def _snapshot_tempdir() -> set:
    return set(Path(tempfile.gettempdir()).iterdir())


def test_no_temp_file_residue_after_success():
    before = _snapshot_tempdir()

    result = run_fix_error(code=IMPORT_ERROR_CODE, error_message=IMPORT_ERROR_MESSAGE)

    assert result.resolved_by == "fix"
    after = _snapshot_tempdir()
    assert after == before, f"leftover temp file(s) after success: {after - before}"


def test_no_bak_file_residue_after_success():
    before = _snapshot_tempdir()

    result = run_fix_error(code=IMPORT_ERROR_CODE, error_message=IMPORT_ERROR_MESSAGE)

    assert result.resolved_by == "fix"
    after = _snapshot_tempdir()
    bak_files = {p for p in after if p.name.endswith(".autofix.bak")}
    assert not bak_files, f"leftover .autofix.bak file(s): {bak_files}"


def test_temp_file_still_cleaned_up_when_fixer_raises_internally(monkeypatch):
    def _boom(self, error):
        raise RuntimeError("simulated internal fixer failure")

    monkeypatch.setattr(PythonFixer, "fix_parsed_error", _boom)

    before = _snapshot_tempdir()

    # Current behavior: the exception from fix_parsed_error is not caught
    # inside _run_fix_tier (only a `finally` guards temp-file cleanup), so
    # it propagates out of run_fix_error. This test locks in that
    # propagation behavior while proving cleanup still happens -- it does
    # not change or paper over it.
    with pytest.raises(RuntimeError, match="simulated internal fixer failure"):
        run_fix_error(code=IMPORT_ERROR_CODE, error_message=IMPORT_ERROR_MESSAGE)

    after = _snapshot_tempdir()
    assert after == before, f"leftover temp file(s) after an internal fixer exception: {after - before}"


def test_auto_install_and_create_files_are_always_false(monkeypatch):
    captured_configs = []
    real_init = PythonFixer.__init__

    def _spy_init(self, config=None):
        captured_configs.append(dict(config or {}))
        real_init(self, config)

    monkeypatch.setattr(PythonFixer, "__init__", _spy_init)

    run_fix_error(code=IMPORT_ERROR_CODE, error_message=IMPORT_ERROR_MESSAGE)

    assert captured_configs, "PythonFixer was never constructed"
    for config in captured_configs:
        assert config["auto_install"] is False
        assert config["create_files"] is False


def test_callers_real_file_is_never_touched(tmp_path):
    real_file = tmp_path / "caller_script.py"
    original_content = "from time import nonexistent_function\n\nprint('hello')\n"
    real_file.write_text(original_content, encoding="utf-8")

    result = run_fix_error(
        code=IMPORT_ERROR_CODE,
        error_message=IMPORT_ERROR_MESSAGE,
        file_path=str(real_file),
    )

    assert result.resolved_by == "fix"
    assert real_file.read_bytes() == original_content.encode("utf-8")
