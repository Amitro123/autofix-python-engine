"""In-process adapter that exposes PythonFixer's deterministic handlers
as a read-only, temp-file-scoped operation for the MCP server (Task 6)."""

import difflib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from autofix_core.infrastructure.cli.python_fixer import PythonFixer
from autofix_core.infrastructure.mcp.telemetry import ASSUMED_TOKENS_PER_FIX
from autofix_core.shared.constants import ErrorType
from autofix_core.shared.core.error_parser import ErrorParser
from autofix_core.shared.handlers.index_error_handler import IndexErrorHandler
from autofix_core.shared.handlers.key_error_handler import KeyErrorHandler
from autofix_core.shared.handlers.zero_division_handler import ZeroDivisionHandler
from autofix_core.shared.handlers.value_error_handler import ValueErrorHandler
from autofix_core.shared.handlers.file_not_found_handler import FileNotFoundHandler
from autofix_core.shared.import_suggestions import IMPORT_SUGGESTIONS, MATH_FUNCTIONS


@dataclass
class FixResult:
    error_type: str
    resolved_by: str  # "fix" | "suggestion" | "no_match"
    patched_code: Optional[str] = None
    diff: Optional[str] = None
    suggestions: Optional[list] = None
    explanation: Optional[str] = None
    telemetry: Optional[dict] = None

    def __post_init__(self) -> None:
        # Every FixResult carries a telemetry.estimated_tokens_saved figure
        # per the spec's FixResult contract, computed with the exact same
        # rule telemetry.py uses so the two never drift apart. Only fill it
        # in when the caller didn't already supply one explicitly.
        if self.telemetry is None:
            tokens_saved = ASSUMED_TOKENS_PER_FIX if self.resolved_by == "fix" else 0
            self.telemetry = {"estimated_tokens_saved": tokens_saved}


_FIX_TIER_ERROR_TYPES = {ErrorType.IMPORT_ERROR}

_SUGGESTION_TIER_HANDLERS = {
    ErrorType.INDEX_ERROR: IndexErrorHandler,
    ErrorType.KEY_ERROR: KeyErrorHandler,
    ErrorType.ZERO_DIVISION_ERROR: ZeroDivisionHandler,
    ErrorType.VALUE_ERROR: ValueErrorHandler,
    ErrorType.FILE_NOT_FOUND: FileNotFoundHandler,
}


def _name_error_suggestions(parsed) -> list:
    name = parsed.missing_function or "the undefined name"
    if parsed.missing_function and parsed.missing_function in IMPORT_SUGGESTIONS:
        return [f"Add import: {IMPORT_SUGGESTIONS[parsed.missing_function]}"]
    if parsed.missing_function and parsed.missing_function in MATH_FUNCTIONS:
        return [f"Add import: from math import {parsed.missing_function}"]
    return [
        f"Check spelling of '{name}'",
        f"Define '{name}' before use",
        "Import the module that defines it, if applicable",
    ]


def run_fix_error(code: str, error_message: str, file_path: Optional[str] = None) -> FixResult:
    parser = ErrorParser()
    parsed = parser.parse_error(error_message)
    error_type = ErrorType.from_string(parsed.error_type)

    if error_type in _FIX_TIER_ERROR_TYPES:
        return _run_fix_tier(code, parsed)

    if error_type == ErrorType.NAME_ERROR:
        return FixResult(
            error_type=parsed.error_type,
            resolved_by="suggestion",
            suggestions=_name_error_suggestions(parsed),
        )

    handler_cls = _SUGGESTION_TIER_HANDLERS.get(error_type)
    if handler_cls is not None:
        handler = handler_cls()
        _, _, details = handler.analyze_error(error_message, file_path)
        suggestions = details.get("suggestions") or []
        if suggestions:
            return FixResult(
                error_type=parsed.error_type,
                resolved_by="suggestion",
                suggestions=suggestions,
            )

    return FixResult(error_type=parsed.error_type, resolved_by="no_match")


def _run_fix_tier(code: str, parsed) -> FixResult:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        parsed.file_path = tmp_path
        # quiet=True: ImportErrorHandler.apply_fix (invoked deep inside
        # fix_parsed_error) would otherwise print() on every branch. Under
        # mcp.run() those prints would land on the real stdout fd -- the
        # exact stream the stdio transport uses for JSON-RPC -- corrupting
        # the protocol. This used to be handled with
        # contextlib.redirect_stdout, but that mutates sys.stdout
        # process-globally and is not safe under concurrent calls: two
        # overlapping redirect_stdout windows on different threads can
        # restore each other's saved stream on exit, leaking output into
        # the wrong place or swallowing an unrelated response. quiet=True
        # avoids the problem at the source instead -- the handler never
        # writes to stdout in the first place, so there is nothing to
        # redirect. The shared handler still defaults to quiet=False, so
        # the CLI's print-based UX is unaffected.
        fixer = PythonFixer(config={"auto_install": False, "create_files": False, "quiet": True})
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
