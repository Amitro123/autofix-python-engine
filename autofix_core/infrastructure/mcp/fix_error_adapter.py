"""In-process adapter that exposes PythonFixer's deterministic handlers
as a read-only, temp-file-scoped operation for the MCP server (Task 6)."""

import difflib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from autofix_core.infrastructure.cli.python_fixer import PythonFixer
from autofix_core.infrastructure.mcp.telemetry import estimated_tokens_saved_for
from autofix_core.shared.constants import ErrorType, BACKUP_EXTENSION
from autofix_core.shared.core.error_parser import ErrorParser
from autofix_core.shared.handlers.index_error_handler import IndexErrorHandler
from autofix_core.shared.handlers.key_error_handler import KeyErrorHandler
from autofix_core.shared.handlers.zero_division_handler import ZeroDivisionHandler
from autofix_core.shared.handlers.value_error_handler import ValueErrorHandler
from autofix_core.shared.handlers.file_not_found_handler import FileNotFoundHandler
from autofix_core.shared.handlers.import_error_handler import ImportErrorHandler
from autofix_core.shared.handlers.module_not_found_handler import ModuleNotFoundHandler
from autofix_core.shared.import_suggestions import suggest_import_for_name


@dataclass
class FixResult:
    error_type: str
    resolved_by: str  # "fix" | "suggestion" | "no_match" | "error"
    # This module's own functions (run_fix_error, _run_fix_tier) only ever
    # produce "fix" | "suggestion" | "no_match" -- "error" is a fourth state
    # the MCP server (server.py) constructs directly when the adapter raises
    # unexpectedly, to keep "tool bug" observably distinct from "the engine
    # looked and genuinely has nothing" (see server.py's exception handler).
    patched_code: Optional[str] = None
    diff: Optional[str] = None
    suggestions: Optional[list] = None
    explanation: Optional[str] = None
    telemetry: Optional[dict] = None

    def __post_init__(self) -> None:
        # Every FixResult carries a telemetry.estimated_tokens_saved figure
        # per the spec's FixResult contract. Only fill it in when the
        # caller didn't already supply one explicitly.
        if self.telemetry is None:
            self.telemetry = {"estimated_tokens_saved": estimated_tokens_saved_for(self.resolved_by)}


_FIX_TIER_ERROR_TYPES = {ErrorType.IMPORT_ERROR}

_SUGGESTION_TIER_HANDLERS = {
    ErrorType.INDEX_ERROR: IndexErrorHandler,
    ErrorType.KEY_ERROR: KeyErrorHandler,
    ErrorType.ZERO_DIVISION_ERROR: ZeroDivisionHandler,
    ErrorType.VALUE_ERROR: ValueErrorHandler,
    ErrorType.FILE_NOT_FOUND: FileNotFoundHandler,
}


def _name_error_suggestions(parsed) -> list:
    name = parsed.missing_function
    if name:
        import_suggestions = suggest_import_for_name(name)
        if import_suggestions:
            return [f"Add import: {s}" for s in import_suggestions]
    else:
        name = "the undefined name"
    return [
        f"Check spelling of '{name}'",
        f"Define '{name}' before use",
        "Import the module that defines it, if applicable",
    ]


def run_fix_error(code: str, error_message: str, file_path: Optional[str] = None) -> FixResult:
    """`code` is only read by the "fix" tier (it's what gets patched and
    diffed). The "suggestion" and "no_match" paths never touch it -- they
    work from `error_message` text alone. That's intentional, not a stray
    unused arg: `code` stays part of the signature for a uniform MCP tool
    schema regardless of which tier ends up handling a given error."""
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

    if error_type == ErrorType.MODULE_NOT_FOUND:
        # ModuleNotFoundError is deliberately never a "fix"-tier type: its
        # real fix in this codebase is a side effect (pip install, or
        # creating a new file) rather than a diff of the input code, and
        # this tool is read-only by design (see the spec's handler-audit
        # table). But that's no reason to also leave it as a dead-end
        # no_match -- ModuleNotFoundHandler.analyze_error already computes
        # good text guidance (known-package / stdlib / test-module /
        # create-locally detection); reuse it instead of duplicating that
        # logic here.
        _, suggestion, details = ModuleNotFoundHandler().analyze_error(error_message, file_path)
        if details.get("missing_module"):
            return FixResult(
                error_type=parsed.error_type,
                resolved_by="suggestion",
                suggestions=[suggestion],
            )
        return FixResult(error_type=parsed.error_type, resolved_by="no_match")

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
    # Only ImportErrorHandler has been given a quiet=True mode (see the
    # comment below). PythonFixer.fix_parsed_error dispatches on error
    # type to several other handlers that still bare-print() unconditionally
    # (NameError, AttributeError, TypeError, ...); routing any of those
    # through this function would silently reopen the exact stdout/JSON-RPC
    # corruption bug fixed above, just via a different error type. This
    # assert is the trip wire: _FIX_TIER_ERROR_TYPES must never grow without
    # also auditing (and quieting) whatever handler that new type dispatches
    # to inside PythonFixer.
    assert ErrorType.from_string(parsed.error_type) == ErrorType.IMPORT_ERROR, (
        f"_run_fix_tier only supports ImportError (quiet-mode audited); "
        f"got {parsed.error_type!r}. Do not add other types to "
        f"_FIX_TIER_ERROR_TYPES without adding a matching quiet mode to "
        f"whatever handler PythonFixer.fix_parsed_error dispatches them to."
    )
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
            # fixer.fix_parsed_error returning False for ImportError means
            # ImportErrorHandler.apply_fix ran but couldn't apply a patch --
            # not that it had nothing to say. apply_fix computes concrete
            # guidance in that case (pip install / create-locally / spelling
            # check) but, with quiet=True, only ever communicated it via
            # print(), which is now suppressed. Recompute the same
            # suggestion through analyze_error (cheap: a couple of regexes,
            # no I/O) instead of silently downgrading real guidance to a
            # bare no_match.
            _, suggestion, details = ImportErrorHandler().analyze_error(
                parsed.error_message, tmp_path
            )
            if details.get("missing_module"):
                return FixResult(
                    error_type=parsed.error_type,
                    resolved_by="suggestion",
                    suggestions=[suggestion],
                )
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
        backup = Path(f"{tmp_path}{BACKUP_EXTENSION}")
        if backup.exists():
            backup.unlink()
