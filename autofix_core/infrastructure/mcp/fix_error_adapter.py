"""In-process adapter that exposes PythonFixer's deterministic handlers
as a read-only, temp-file-scoped operation for the MCP server (Task 6)."""

import difflib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from autofix_core.infrastructure.cli.python_fixer import PythonFixer
from autofix_core.shared.constants import ErrorType
from autofix_core.shared.core.error_parser import ErrorParser


@dataclass
class FixResult:
    error_type: str
    resolved_by: str  # "fix" | "suggestion" | "no_match"
    patched_code: Optional[str] = None
    diff: Optional[str] = None
    suggestions: Optional[list] = None
    explanation: Optional[str] = None


_FIX_TIER_ERROR_TYPES = {ErrorType.IMPORT_ERROR}


def run_fix_error(code: str, error_message: str, file_path: Optional[str] = None) -> FixResult:
    parser = ErrorParser()
    parsed = parser.parse_error(error_message)
    error_type = ErrorType.from_string(parsed.error_type)

    if error_type not in _FIX_TIER_ERROR_TYPES:
        return FixResult(error_type=parsed.error_type, resolved_by="no_match")

    return _run_fix_tier(code, parsed)


def _run_fix_tier(code: str, parsed) -> FixResult:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        parsed.file_path = tmp_path
        fixer = PythonFixer(config={"auto_install": False, "create_files": False})
        fixed = fixer.fix_parsed_error(parsed)

        if not fixed:
            return FixResult(error_type=parsed.error_type, resolved_by="no_match")

        patched_code = Path(tmp_path).read_text(encoding="utf-8")
        diff = "".join(
            difflib.unified_diff(
                code.splitlines(keepends=True),
                patched_code.splitlines(keepends=True),
                fromfile="original",
                tofile="patched",
            )
        )
        return FixResult(
            error_type=parsed.error_type,
            resolved_by="fix",
            patched_code=patched_code,
            diff=diff,
            explanation=f"Applied deterministic fix for {parsed.error_type}",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        backup = Path(f"{tmp_path}.autofix.bak")
        if backup.exists():
            backup.unlink()
