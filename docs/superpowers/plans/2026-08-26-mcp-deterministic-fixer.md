# MCP Deterministic Fixer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing deterministic Python-error-fixing pipeline as a single MCP tool (`fix_error`) that Claude Code can call before spending its own tokens reasoning about common errors, and record enough local telemetry to evaluate whether that actually saves tokens.

**Architecture:** A new `autofix_core/infrastructure/mcp/` adapter layer wraps the existing `PythonFixer`/handler pipeline in-process (no HTTP, no subprocess execution of caller code). One handler (`ImportErrorHandler`) produces real diffable patches; six others are suggestion-only today and are surfaced as structured suggestion text instead of a patch; everything else falls through to "no match." A FastMCP server exposes this as one tool over stdio; a separate local console script reports on collected telemetry.

**Tech Stack:** Python (repo floor is 3.8; this feature requires 3.10+ — see Task 6), `fastmcp` (new dependency), `pytest` (existing).

**Spec:** `docs/superpowers/specs/2026-08-26-mcp-deterministic-fixer-design.md`

## Global Constraints

- The MCP adapter must never execute caller-supplied code (no `exec`/`eval`/`runpy`) and must never shell out (`ModuleNotFoundError`'s pip-install path is excluded from this feature entirely — see spec's handler audit table).
- `fix_error` never writes to the caller's real files — all file I/O happens against a private `tempfile` that is always cleaned up, even on error.
- `resolved_by` is exactly one of `"fix"`, `"suggestion"`, `"no_match"` — never a bare boolean.
- `estimated_tokens_saved` is only ever non-zero when `resolved_by == "fix"`.
- Telemetry writing must never affect the returned `FixResult`, even if the write fails.
- `AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX` defaults to `500` (documented rationale in Task 5: rough sum of typical traceback-reading + fix-reasoning + patch-writing tokens in an agentic loop), overridable via environment variable.

---

### Task 1: Fix `ImportErrorHandler` so `apply_fix` actually runs

`ImportErrorHandler.apply_fix` (`autofix_core/shared/handlers/import_error_handler.py`) is the one handler this feature depends on for real patches, and it is currently broken: `__init__` never sets `self.import_suggestions`, `self.stdlib_modules`, `self.known_pip_packages`, `self.module_to_package`, `self.multi_import_suggestions`, `self.math_functions`, or `self.dry_run`, even though every method reads them off `self`. `apply_fix` also calls `self.add_import_to_script(...)` (line 129) but the method is defined as `_add_import_to_script` (line 182) — a name that doesn't exist on the object. Both bugs mean any call into `apply_fix` that reaches past the first two guard clauses raises `AttributeError` today. `_add_import_to_script` also calls `self._backup_file(...)` and `self._read_file_content(...)`, neither of which exist on this class (they exist on the unrelated `PythonFixer` class in `python_fixer.py:422` and `python_fixer.py:...`, using the pattern `f"{file_path}.autofix.bak"` + `shutil.copy2`).

**Files:**
- Modify: `autofix_core/shared/handlers/import_error_handler.py`
- Test: `tests/test_import_error_handler.py` (new file)

**Interfaces:**
- Produces: `ImportErrorHandler().apply_fix("ImportError", file_path: str, details: dict) -> bool`, where `details` comes from `ImportErrorHandler().analyze_error(error_message: str, file_path: str) -> tuple[bool, str, dict]`. Task 3 consumes both methods exactly as they exist today (this task only makes them not crash).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_import_error_handler.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_import_error_handler.py -v`
Expected: `test_apply_fix_adds_suggested_import` FAILs with `AttributeError: 'ImportErrorHandler' object has no attribute 'import_suggestions'` (or similar, depending on which missing attribute is hit first). `test_apply_fix_returns_false_when_module_unresolvable` may already pass by accident (it returns `False` before touching the missing attributes) — that's fine, it documents current-and-correct behavior.

- [ ] **Step 3: Fix `__init__` and the method-name typo**

In `autofix_core/shared/handlers/import_error_handler.py`, replace the `__init__` method:

```python
    def __init__(self, dry_run: bool = False):
        self.logger = get_logger("import_error_handler")
        self.dry_run = dry_run
        self.import_suggestions = IMPORT_SUGGESTIONS
        self.stdlib_modules = STDLIB_MODULES
        self.known_pip_packages = KNOWN_PIP_PACKAGES
        self.module_to_package = MODULE_TO_PACKAGE
        self.multi_import_suggestions = MULTI_IMPORT_SUGGESTIONS
        self.math_functions = MATH_FUNCTIONS
```

In `apply_fix`, fix the call site (around line 129):

```python
            if self._add_import_to_script(import_statement, file_path):
```

(was `self.add_import_to_script(...)`).

Add the two missing helper methods (place them near `_add_import_to_script`, matching the pattern already used in `python_fixer.py`):

```python
    def _backup_file(self, file_path: str) -> str:
        """Create backup before modifying file"""
        backup_path = f"{file_path}.autofix.bak"
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _read_file_content(self, file_path: str) -> str:
        """Read file content with UTF-8 encoding"""
        return Path(file_path).read_text(encoding="utf-8")
```

(`Path` is already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_import_error_handler.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add autofix_core/shared/handlers/import_error_handler.py tests/test_import_error_handler.py
git commit -m "fix: ImportErrorHandler.apply_fix crashed on every call (missing attrs, typo'd method name)"
```

---

### Task 2: Teach `ErrorParser.parse_error` to extract the `NameError` name

`ErrorParser.parse_error(error_output: str)` (`autofix_core/shared/core/error_parser.py:49`) is the string-based parser this feature uses (it already exists — no new parsing entry point needed). It special-cases `ModuleNotFoundError`, `KeyError`, and `ZeroDivisionError` but not `NameError`, so `ParsedError.missing_function` stays `None` for a text-only `NameError`. `PythonFixer._fix_name_error` (`python_fixer.py`) reads `error.missing_function` directly (`missing_name = error.missing_function or "unknown"`), so today a text-only `NameError` degrades to a suggestion that says "Undefined name: 'unknown'" — accurate but useless. The exception-based path already has the correct regex in `_parse_name_error` (`r"name '([^']+)' is not defined"`); this task ports it into `parse_error`.

**Files:**
- Modify: `autofix_core/shared/core/error_parser.py`
- Test: `tests/test_error_parser.py` (new file — the repo has a pre-existing `tests_error_parser.py` that pytest never collects because it doesn't match the `test_*.py` glob; leave that file alone, it's an unrelated pre-existing issue)

**Interfaces:**
- Produces: `ErrorParser().parse_error(error_output: str) -> ParsedError` now sets `missing_function` for `NameError` text. Task 4 consumes this to fill in the `suggestion` tier's `NameError` case.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_error_parser.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_error_parser.py -v`
Expected: FAIL — `assert None == "sqrt"`.

- [ ] **Step 3: Add the `NameError` case**

In `autofix_core/shared/core/error_parser.py`, inside `parse_error`, add a branch alongside the existing `KeyError`/`ZeroDivisionError` special cases (after the `missing_module` block, before the final default `return`):

```python
        if error_type == "NameError":
            name_match = re.search(r"name '([^']+)' is not defined", error_message)
            missing_function = name_match.group(1) if name_match else None

            return ParsedError(
                error_type="NameError",
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                missing_function=missing_function
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_error_parser.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autofix_core/shared/core/error_parser.py tests/test_error_parser.py
git commit -m "feat: ErrorParser.parse_error extracts NameError's missing name from text"
```

---

### Task 3: Build the `fix_error` adapter core — `fix` tier and `no_match`

Pure-Python adapter with no MCP dependency (easy to unit test): given `code` and `error_message` text, parse the error, and for `ImportError` run the now-working `PythonFixer`/`ImportErrorHandler` path against a private temp copy of `code`, returning a diff. Everything not yet wired (all other error types) falls through to `no_match` — Task 4 adds the `suggestion` tier without touching this task's `fix`/`no_match` logic.

**Files:**
- Create: `autofix_core/infrastructure/mcp/__init__.py` (empty)
- Create: `autofix_core/infrastructure/mcp/fix_error_adapter.py`
- Test: `tests/test_mcp_fix_error_adapter.py`

**Interfaces:**
- Consumes: `ErrorParser().parse_error(error_output: str) -> ParsedError` (Task 2), `PythonFixer(config: dict).fix_parsed_error(error: ParsedError) -> bool` (`autofix_core/infrastructure/cli/python_fixer.py`), `ErrorType.from_string(s: str)` (`autofix_core/shared/constants.py`).
- Produces: `FixResult` dataclass and `run_fix_error(code: str, error_message: str, file_path: str | None = None) -> FixResult`, both importable from `autofix_core.infrastructure.mcp.fix_error_adapter`. Task 4 extends `run_fix_error`; Task 6 calls it unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_fix_error_adapter.py
from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error


def test_import_error_produces_a_fix():
    code = "from time import nonexistent_function\n"
    error_message = "cannot import name 'nonexistent_function' from 'time' (unknown location)"

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcp_fix_error_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'autofix_core.infrastructure.mcp'`.

- [ ] **Step 3: Create the package and the adapter**

```python
# autofix_core/infrastructure/mcp/__init__.py (leave this file empty)
```

```python
# autofix_core/infrastructure/mcp/fix_error_adapter.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_fix_error_adapter.py -v`
Expected: both PASS. If the diff assertion fails because of exact whitespace in unified-diff output, inspect `result.diff` directly and adjust the substring checked (not the diff generation) — `difflib.unified_diff` output format is standard, the test just needs to match it.

- [ ] **Step 5: Commit**

```bash
git add autofix_core/infrastructure/mcp/ tests/test_mcp_fix_error_adapter.py
git commit -m "feat: add fix_error adapter core (fix tier + no_match, ImportError only)"
```

---

### Task 4: Add the `suggestion` tier (six handlers)

Wire `IndexErrorHandler`, `KeyErrorHandler`, `ZeroDivisionHandler`, `ValueErrorHandler`, `FileNotFoundHandler`, and `NameError` (handled inline in `python_fixer.py`, not via a separate handler class) into `run_fix_error`, returning their `analyze_error(...)`-computed suggestion list instead of calling `apply_fix` (which only prints and always returns `False` for these types).

**Files:**
- Modify: `autofix_core/infrastructure/mcp/fix_error_adapter.py`
- Test: `tests/test_mcp_fix_error_adapter.py` (extend)

**Interfaces:**
- Consumes: `IndexErrorHandler().analyze_error(error_output: str, file_path: str) -> tuple[str, str, dict]` and the same signature on `KeyErrorHandler`, `ZeroDivisionHandler`, `ValueErrorHandler`, `FileNotFoundHandler` (all in `autofix_core/shared/handlers/`); `ParsedError.missing_function` for `NameError` (Task 2).
- Produces: `run_fix_error` now also returns `resolved_by="suggestion"` with a populated `suggestions: list[str]`. Signature unchanged from Task 3.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_mcp_fix_error_adapter.py
def test_index_error_produces_a_suggestion():
    code = "items = [1, 2]\nprint(items[5])\n"
    error_message = "IndexError: list index out of range"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "IndexError"
    assert result.suggestions
    assert result.patched_code is None


def test_name_error_produces_a_suggestion_with_the_actual_name():
    code = "print(sqrt(4))\n"
    error_message = "NameError: name 'sqrt' is not defined"

    result = run_fix_error(code=code, error_message=error_message)

    assert result.resolved_by == "suggestion"
    assert result.error_type == "NameError"
    assert any("sqrt" in s or "math" in s for s in result.suggestions)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcp_fix_error_adapter.py -v`
Expected: both new tests FAIL — `resolved_by == "no_match"` instead of `"suggestion"`.

- [ ] **Step 3: Add the suggestion-tier dispatch**

In `autofix_core/infrastructure/mcp/fix_error_adapter.py`, add the imports and dispatch table, and call it before falling through to `no_match`:

```python
from autofix_core.shared.handlers.index_error_handler import IndexErrorHandler
from autofix_core.shared.handlers.key_error_handler import KeyErrorHandler
from autofix_core.shared.handlers.zero_division_handler import ZeroDivisionHandler
from autofix_core.shared.handlers.value_error_handler import ValueErrorHandler
from autofix_core.shared.handlers.file_not_found_handler import FileNotFoundHandler
from autofix_core.shared.import_suggestions import IMPORT_SUGGESTIONS, MATH_FUNCTIONS

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
```

Replace the `if error_type not in _FIX_TIER_ERROR_TYPES:` branch in `run_fix_error`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_fix_error_adapter.py -v`
Expected: all four tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add autofix_core/infrastructure/mcp/fix_error_adapter.py tests/test_mcp_fix_error_adapter.py
git commit -m "feat: add suggestion tier to fix_error adapter (IndexError, KeyError, ZeroDivisionError, ValueError, FileNotFoundError, NameError)"
```

---

### Task 5: Telemetry — JSONL logging and token-savings estimate

Every `run_fix_error` call should be logged, without ever affecting the caller's result. This task adds a standalone, best-effort logging function; Task 6 wires it into the MCP tool call.

**Files:**
- Create: `autofix_core/infrastructure/mcp/telemetry.py`
- Test: `tests/test_mcp_telemetry.py`

**Interfaces:**
- Consumes: `FixResult` (Task 3/4).
- Produces: `log_fix_result(result: FixResult, input_chars: int, log_path: Optional[Path] = None) -> None`, importable from `autofix_core.infrastructure.mcp.telemetry`. Task 6 calls this after every `run_fix_error` call. Also produces the module-level constant `ASSUMED_TOKENS_PER_FIX: int` (default `500`, overridable via the `AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX` env var), consumed by Task 7's report script.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_telemetry.py
import json

from autofix_core.infrastructure.mcp.fix_error_adapter import FixResult
from autofix_core.infrastructure.mcp.telemetry import log_fix_result


def test_log_fix_result_writes_one_jsonl_line_per_call(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"
    fix_result = FixResult(error_type="ImportError", resolved_by="fix", patched_code="x", diff="d")

    log_fix_result(fix_result, input_chars=42, log_path=log_path)
    log_fix_result(fix_result, input_chars=10, log_path=log_path)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["error_type"] == "ImportError"
    assert record["resolved_by"] == "fix"
    assert record["input_chars"] == 42
    assert record["estimated_tokens_saved"] == 500


def test_log_fix_result_reports_zero_savings_for_suggestion_and_no_match(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"

    log_fix_result(
        FixResult(error_type="IndexError", resolved_by="suggestion", suggestions=["x"]),
        input_chars=5,
        log_path=log_path,
    )
    log_fix_result(
        FixResult(error_type="TypeError", resolved_by="no_match"),
        input_chars=5,
        log_path=log_path,
    )

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").strip().splitlines()]
    assert all(r["estimated_tokens_saved"] == 0 for r in records)


def test_log_fix_result_never_raises_when_path_is_unwritable(tmp_path):
    unwritable_dir = tmp_path / "does" / "not" / "exist"
    log_path = unwritable_dir / "mcp_telemetry.jsonl"

    # Should not raise even though the parent directory doesn't exist and
    # this function must never create it in a way that could fail loudly.
    log_fix_result(
        FixResult(error_type="ImportError", resolved_by="fix"),
        input_chars=1,
        log_path=log_path,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcp_telemetry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'autofix_core.infrastructure.mcp.telemetry'`.

- [ ] **Step 3: Write the telemetry module**

```python
# autofix_core/infrastructure/mcp/telemetry.py
"""Best-effort local telemetry for the fix_error MCP tool.

estimated_tokens_saved is an explicit assumption, not a measurement: the
MCP tool never calls an LLM itself, so there is no internal ground truth
to calibrate against. ASSUMED_TOKENS_PER_FIX approximates the tokens an
agent would otherwise spend reading the traceback, reasoning about the
fix, and writing the patch itself — roughly 100-300 tokens of error
context plus 200-400 tokens of reasoning-and-patch output for a typical
one-line import fix. It is applied only to resolved_by == "fix", where a
full patch plausibly avoids that whole round trip; "suggestion" and
"no_match" always log 0, since the agent still does the real work itself.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ASSUMED_TOKENS_PER_FIX = int(os.environ.get("AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX", "500"))

DEFAULT_LOG_PATH = Path(
    os.environ.get("AUTOFIX_MCP_TELEMETRY_PATH", str(Path.home() / ".autofix" / "mcp_telemetry.jsonl"))
)


def log_fix_result(result, input_chars: int, log_path: Optional[Path] = None) -> None:
    path = log_path or DEFAULT_LOG_PATH
    tokens_saved = ASSUMED_TOKENS_PER_FIX if result.resolved_by == "fix" else 0

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "error_type": result.error_type,
        "resolved_by": result.resolved_by,
        "input_chars": input_chars,
        "estimated_tokens_saved": tokens_saved,
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # telemetry must never break the caller's fix_error result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_telemetry.py -v`
Expected: all three PASS.

- [ ] **Step 5: Commit**

```bash
git add autofix_core/infrastructure/mcp/telemetry.py tests/test_mcp_telemetry.py
git commit -m "feat: add best-effort JSONL telemetry for fix_error calls"
```

---

### Task 6: FastMCP server exposing `fix_error`

Wires Tasks 3-5 behind a single FastMCP tool, over stdio. Adds `fastmcp` as a project dependency.

**Files:**
- Create: `autofix_core/infrastructure/mcp/server.py`
- Modify: `pyproject.toml` (add `fastmcp` dependency, bump `requires-python`, add `autofix-mcp-server` console script)
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `run_fix_error` (Task 3/4), `log_fix_result` (Task 5).
- Produces: a module-level FastMCP instance `mcp` in `autofix_core.infrastructure.mcp.server`, and a `main()` entry point that calls `mcp.run()`.

- [ ] **Step 1: Install fastmcp and confirm its Python floor**

```bash
pip install fastmcp
python -c "import fastmcp; print(fastmcp.__version__)"
pip show fastmcp | grep -i "Requires-Python\|Requires:"
```

Note the actual minimum Python version fastmcp reports. This plan assumes 3.10+; if the installed version reports something different, use that real value in Step 4 instead of guessing.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_mcp_server.py
import asyncio

from fastmcp import Client

from autofix_core.infrastructure.mcp.server import mcp


def test_fix_error_tool_returns_a_fix_for_import_error():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {
                    "code": "from time import nonexistent_function\n",
                    "error_message": "cannot import name 'nonexistent_function' from 'time' (unknown location)",
                },
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "fix"
    assert payload["error_type"] == "ImportError"
    assert "import time" in payload["patched_code"]


def test_fix_error_tool_returns_no_match_for_unhandled_error():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {"code": "1/0\n", "error_message": "TypeError: bad operand"},
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "no_match"


def test_fix_error_tool_never_raises_on_malformed_input():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {"code": "", "error_message": ""},
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "no_match"
```

If the installed `fastmcp`'s `CallToolResult` shape differs from `result.data`/plain-dict access assumed above, adjust the two lines that unwrap `result` to match what `client.call_tool` actually returns for this version — the assertions on `payload[...]` are what matters and shouldn't need to change.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_mcp_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'autofix_core.infrastructure.mcp.server'`.

- [ ] **Step 4: Write the server**

```python
# autofix_core/infrastructure/mcp/server.py
from dataclasses import asdict

from fastmcp import FastMCP

from autofix_core.infrastructure.mcp.fix_error_adapter import run_fix_error
from autofix_core.infrastructure.mcp.telemetry import log_fix_result

mcp = FastMCP("autofix-deterministic-fixer")


@mcp.tool()
def fix_error(code: str, error_message: str, file_path: str = "") -> dict:
    """Try to resolve a Python error deterministically (no LLM call) before
    reasoning about it yourself. Returns resolved_by: "fix" (a ready-to-apply
    patch), "suggestion" (targeted guidance, no patch), or "no_match" (this
    tool has nothing for this error — proceed as you normally would)."""
    try:
        result = run_fix_error(
            code=code,
            error_message=error_message,
            file_path=file_path or None,
        )
    except Exception as exc:  # never let an adapter bug crash the caller
        result = None
        payload = {
            "error_type": "UnknownError",
            "resolved_by": "no_match",
            "patched_code": None,
            "diff": None,
            "suggestions": None,
            "explanation": f"internal error: {exc}",
        }

    if result is not None:
        payload = asdict(result)
        try:
            log_fix_result(result, input_chars=len(code))
        except Exception:
            pass  # telemetry must never affect the tool result

    return payload


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add the dependency and console script**

In `pyproject.toml`, change:

```toml
requires-python = ">=3.8"
```

to (replace `3.10` with whatever Step 1 actually reported, if different):

```toml
requires-python = ">=3.10"
```

Change:

```toml
dependencies = []
```

to:

```toml
dependencies = ["fastmcp>=2.0"]
```

Add a second script under `[project.scripts]` (leave the existing broken `autofix = ...` line as-is — it is a pre-existing, unrelated issue out of scope for this feature):

```toml
[project.scripts]
autofix = "autofix.cli.autofix_cli_interactive:main"
autofix-mcp-server = "autofix_core.infrastructure.mcp.server:main"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_mcp_server.py -v`
Expected: all three PASS.

- [ ] **Step 7: Commit**

```bash
git add autofix_core/infrastructure/mcp/server.py pyproject.toml tests/test_mcp_server.py
git commit -m "feat: add FastMCP server exposing fix_error as an MCP tool"
```

---

### Task 7: `autofix-mcp-report` console script

Human-facing summary of the telemetry log — not an MCP tool.

**Files:**
- Create: `autofix_core/infrastructure/mcp/report.py`
- Modify: `pyproject.toml` (add console script)
- Test: `tests/test_mcp_report.py`

**Interfaces:**
- Consumes: the JSONL format written by `log_fix_result` (Task 5) and `ASSUMED_TOKENS_PER_FIX` (Task 5).
- Produces: `format_report(log_path: Path) -> str` (pure function, easy to test) and `main()` (prints it, reads `DEFAULT_LOG_PATH` if no argument given).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_report.py
import json

from autofix_core.infrastructure.mcp.report import format_report


def test_format_report_summarizes_calls_by_resolution(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"
    records = [
        {"ts": "t1", "error_type": "ImportError", "resolved_by": "fix", "input_chars": 10, "estimated_tokens_saved": 500},
        {"ts": "t2", "error_type": "ImportError", "resolved_by": "fix", "input_chars": 10, "estimated_tokens_saved": 500},
        {"ts": "t3", "error_type": "IndexError", "resolved_by": "suggestion", "input_chars": 10, "estimated_tokens_saved": 0},
        {"ts": "t4", "error_type": "TypeError", "resolved_by": "no_match", "input_chars": 10, "estimated_tokens_saved": 0},
    ]
    log_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    report = format_report(log_path)

    assert "Total calls: 4" in report
    assert "fix: 2" in report
    assert "suggestion: 1" in report
    assert "no_match: 1" in report
    assert "1000" in report  # total estimated tokens saved


def test_format_report_handles_missing_log_file(tmp_path):
    report = format_report(tmp_path / "does_not_exist.jsonl")
    assert "Total calls: 0" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcp_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'autofix_core.infrastructure.mcp.report'`.

- [ ] **Step 3: Write the report module**

```python
# autofix_core/infrastructure/mcp/report.py
import json
from collections import Counter
from pathlib import Path

from autofix_core.infrastructure.mcp.telemetry import ASSUMED_TOKENS_PER_FIX, DEFAULT_LOG_PATH


def format_report(log_path: Path) -> str:
    if not log_path.exists():
        return "Total calls: 0 (no telemetry recorded yet at {})".format(log_path)

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_resolution = Counter(r["resolved_by"] for r in records)
    total_tokens_saved = sum(r["estimated_tokens_saved"] for r in records)

    lines = [
        f"Total calls: {len(records)}",
        f"  fix: {by_resolution.get('fix', 0)}",
        f"  suggestion: {by_resolution.get('suggestion', 0)}",
        f"  no_match: {by_resolution.get('no_match', 0)}",
        "",
        f"Estimated tokens saved: {total_tokens_saved}",
        f"  (assumes {ASSUMED_TOKENS_PER_FIX} tokens per 'fix'-tier call — an assumption, not a measurement;"
        " set AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX to change it)",
    ]
    return "\n".join(lines)


def main() -> None:
    print(format_report(DEFAULT_LOG_PATH))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_report.py -v`
Expected: both PASS.

- [ ] **Step 5: Add the console script and commit**

In `pyproject.toml`, add to `[project.scripts]`:

```toml
autofix-mcp-report = "autofix_core.infrastructure.mcp.report:main"
```

```bash
git add autofix_core/infrastructure/mcp/report.py pyproject.toml tests/test_mcp_report.py
git commit -m "feat: add autofix-mcp-report console script"
```

---

### Task 8: Wire it up for real and document installation

Manual end-to-end smoke test plus the one doc a user needs to actually install this.

**Files:**
- Modify: `README.md` (append a new section; do not touch existing content — the file has pre-existing staleness unrelated to this feature)

**Interfaces:** None (this task produces no new code, only verifies the previous tasks and documents usage).

- [ ] **Step 1: Install the package locally and register the MCP server with Claude Code**

```bash
pip install -e .
claude mcp add autofix -- autofix-mcp-server
```

- [ ] **Step 2: Manually verify the tool is visible and works**

In a Claude Code session in this repo, ask it to call the `fix_error` tool (or trigger it naturally by pointing at a script with a fixable `ImportError`) and confirm a patch comes back. Then check telemetry was recorded:

```bash
autofix-mcp-report
```

Expected: output shows `Total calls: 1`, `fix: 1`, and a non-zero estimated-tokens-saved line.

- [ ] **Step 3: Add a README section**

Append to `README.md` (after existing content, as a new top-level section — do not edit anything above it):

```markdown
## MCP Server (experimental)

`autofix-python-engine` can run as a local [MCP](https://modelcontextprotocol.io)
server that exposes its deterministic, zero-token error-fixing handlers as a
single tool, `fix_error`, for coding agents like Claude Code to call before
spending their own tokens reasoning about a common error.

Install and register with Claude Code:

\`\`\`bash
pip install -e .
claude mcp add autofix -- autofix-mcp-server
\`\`\`

The tool never executes your code and never writes to your files — it takes
the code and error text the agent already has, and returns either a ready
patch (`resolved_by: "fix"`), a targeted suggestion (`resolved_by: "suggestion"`),
or nothing (`resolved_by: "no_match"`), in which case the agent proceeds as
it normally would.

Every call is logged locally to `~/.autofix/mcp_telemetry.jsonl`. Run
`autofix-mcp-report` to see a summary, including an estimated token-savings
figure (an explicit assumption, not a measurement — see the report's own
output for the constant it uses).

Today `fix_error` produces a real patch (`"fix"`) only for `ImportError`;
`IndexError`, `KeyError`, `ZeroDivisionError`, `ValueError`, `FileNotFoundError`,
and `NameError` return a `"suggestion"` instead of a patch. Everything else
returns `"no_match"`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document the MCP server (fix_error tool + autofix-mcp-report)"
```

---

## Self-Review Notes

- **Spec coverage:** Tool surface (Task 3+4+6), telemetry (Task 5+7), distribution (Task 6 Step 5, Task 8), security constraints — `auto_install`/`create_files` forced off (Task 3), no execution of caller code (Task 3/4 never call `apply_fix` on suggestion-tier handlers, only `analyze_error`), no file mutation of caller's real files (Task 3 uses a temp file exclusively) — testing plan (fix/suggestion/no_match cases in Task 3/4/6), all covered.
- **Bonus findings folded in:** `ImportErrorHandler.apply_fix` was completely broken (Task 1) — discovered by reading the actual method bodies rather than trusting names/docstrings, and necessary because it's the one handler the `fix` tier depends on.
- **Type consistency:** `FixResult` fields (`error_type`, `resolved_by`, `patched_code`, `diff`, `suggestions`, `explanation`) are defined once in Task 3 and used identically in Tasks 4, 5, 6, 7 — no renames introduced.
- **Not in this plan:** the sandbox-escape fix and `ModuleNotFoundError` support are explicitly out of scope per the spec — tracked as separate, independent work.
