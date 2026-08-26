# MCP Deterministic Fixer — Design Spec

Date: 2026-08-26
Status: Approved for planning
Owner: amitrosen4@gmail.com

## Purpose

`autofix-python-engine` already contains a deterministic, AST/rule-based
error-fixing pipeline (`PythonFixer` and the handlers under
`autofix_core/shared/handlers/`) that fixes common Python errors
(`ModuleNotFoundError`, `ImportError`, `IndexError`, `KeyError`,
`ZeroDivisionError`, simple `SyntaxError`, etc.) without any LLM call.

Coding agents (Claude Code, Cursor, ...) currently hit these same error
classes constantly and resolve them by round-tripping through their own
LLM: read the traceback, reason about the fix, write a patch. Every one
of those round trips costs real tokens for something a local, sub-second,
zero-token deterministic engine can already do.

This spec defines an MCP server that exposes the existing deterministic
pipeline as a single tool an agent can call *before* reasoning about a
fix itself — a fast, cheap "ground truth" pass — and measures how often
that pass succeeds, as a first data point for evaluating whether this is
worth turning into a real token-economics/FinOps product.

## Goals

- Expose the existing deterministic handler pipeline as an MCP tool
  usable by Claude Code with zero additional config beyond adding the
  server.
- Never execute the caller's code and never call an external LLM API —
  the tool must work fully offline, with no API key.
- Record enough data locally to answer: "what fraction of errors this
  agent hit did the deterministic engine resolve, and roughly how many
  tokens did that avoid?"
- Reuse the existing `PythonFixer`/handler pipeline unchanged — one
  source of truth for fix logic, no duplicated business logic between
  the CLI, the API, and the MCP server.

## Non-goals (this spec)

- **No Gemini/LLM fallback inside the MCP tool.** The calling agent
  (Claude) *is* the fallback — when the deterministic pass finds no fix,
  the tool returns "no match" and the agent proceeds as it does today.
  This also means the MCP tool never touches `GeminiService`,
  `ToolsService`, `DebuggerService`, or `SandboxExecutor` — none of that
  code is on the MCP call path.
- **No sandbox-escape fix.** The Critical RestrictedPython guard bug
  found in code review (`debugger_service.py:375-406`) is real, but it
  only matters on the `execute_code` path, which this spec's MCP tool
  never reaches. It is tracked and fixed as an independent workstream,
  not a prerequisite for this one.
- **No Cursor / Claude Desktop packaging.** MVP targets Claude Code
  only. A stdio-based FastMCP server is client-agnostic by construction,
  so adding other clients later is packaging work, not redesign.
- **No file mutation.** The tool never writes to disk. It returns a
  proposed patch; the calling agent applies it with its own edit tool if
  it chooses to.

## Architecture

New module: `autofix_core/infrastructure/mcp/`, alongside the existing
`infrastructure/api/` and `infrastructure/cli/` adapters — same Clean
Architecture pattern the project already uses elsewhere: a thin
interface adapter that imports and calls the existing pipeline
in-process. No HTTP hop, no separate server process to manage — Claude
Code spawns the MCP server itself over stdio.

```
Claude Code  --stdio(MCP)-->  autofix_core.infrastructure.mcp.server
                                  |
                                  v
                     autofix_core.infrastructure.cli.python_fixer.PythonFixer
                                  |
                                  v
                     autofix_core/shared/handlers/*  (unchanged)
```

**Why in-process instead of an HTTP client to the existing FastAPI
service:** a client-of-an-API design would require the user to have the
API server already running — that breaks zero-config installation for a
tool meant to be added with one `claude mcp add` command. In-process
import has the same effect with none of that operational overhead, and
matches how `infrastructure/api` itself already calls these services.

## Tool surface (MVP: one tool)

**Revised after auditing every handler's actual `apply_fix` return value**
(not just its name/docstring — see "Handler audit" below): most handler
classes are suggestion-only today. The tool surface reflects that
honestly with a three-way `resolved_by`, instead of a binary
resolved/not-resolved that would misrepresent suggestion-only output as
a real fix.

```
fix_error(code: str, error_message: str, file_path: str | None = None) -> FixResult

FixResult:
  error_type: str                 # e.g. "ImportError"
  resolved_by: "fix" | "suggestion" | "no_match"
  patched_code: str | None        # full patched source, only if resolved_by == "fix"
  diff: str | None                # unified diff, only if resolved_by == "fix"
  suggestions: list[str] | None   # structured suggestion text, only if resolved_by == "suggestion"
  explanation: str | None         # one-line human-readable summary
  telemetry: { estimated_tokens_saved: int | None }
```

`code` and `error_message` are required — the calling agent has already
run the script and has both. `file_path` is optional context (used for
messages/relative-import resolution), never read or written by the tool
itself.

A single tool, not one-per-error-type: keeps the surface minimal (YAGNI)
until real usage data says otherwise.

### Handler audit (ground truth for MVP error-type coverage)

Verified by reading every handler's `apply_fix` body, not inferring from
names:

| Error type | Real behavior today | MVP tier |
|---|---|---|
| `ImportError` | `ImportErrorHandler.apply_fix` (`import_error_handler.py:129`) genuinely adds an `import` line via `_add_import_to_script` and returns `True` — a real, diffable text fix. | **`fix`** |
| `IndexError`, `KeyError`, `ZeroDivisionError`, `ValueError`, `FileNotFoundError`, `NameError` | Each handler's `apply_fix` only `print()`s suggestions to stdout and unconditionally `return False`. No code is ever mutated. The suggestion text *does* exist as structured data in `analyze_error()`'s returned `details["suggestions"]`, just never surfaced anywhere outside a print. | **`suggestion`** (surface `details["suggestions"]` as data instead of a print) |
| `ModuleNotFoundError` | `ModuleNotFoundHandler.apply_fix` does real work, but the "fix" is a **side effect** — `pip install` (gated by an allowlist and `auto_install`) or creating a brand-new module file — not an edit to the input `code`. Doesn't fit a diff-of-`code` contract, and installing packages is exactly the kind of execution this tool is designed to avoid. | **Excluded from MVP** (candidate for a later, explicitly side-effecting tool, not `fix_error`) |
| `SyntaxError`, `AttributeError`, `TypeError`, everything else `ErrorType` doesn't map | Mixed/inconsistent (`SyntaxError` handler returns `True` on some branches, `False` on others) or not meaningfully wired. Out of scope for MVP — falls through to `no_match`, same as any truly unrecognized error. | **`no_match`** |

## Data flow

1. Agent calls `fix_error` with the source it already has and the
   traceback/error text it already saw.
2. The adapter parses `error_message` into a `ParsedError`, reusing
   `ErrorParser.parse_error(error_text)` — this string-based parser
   **already exists** (`error_parser.py:49`), so no new parsing entry
   point is needed. It is, however, materially thinner than the
   exception-based `_parse_exception_impl` path: it only special-cases
   `ModuleNotFoundError`/`KeyError`/`ZeroDivisionError` and leaves
   `missing_function` (needed for `NameError`) and other per-type fields
   unset for everything else. Closing that gap for the MVP's actual
   error types (`ImportError`'s `missing_module`/`missing_function`
   extraction, in particular — the one type that needs to be accurate
   since it drives a real patch) is in-scope implementation work; the
   parsing entry point itself is not a redesign.
3. For `ImportError` (the one `fix`-tier type): the adapter writes
   `code` to a private temp file (`tempfile`, deleted after the call),
   and calls `PythonFixer(config={"auto_install": False, "create_files": False})
   .fix_parsed_error(parsed_error)` against it — reusing the existing
   handler dispatch unmodified rather than refactoring handlers to
   operate on in-memory strings. This is the one deliberate shortcut in
   this design: it avoids touching well-tested handler internals for
   MVP, at the cost of a temp-file round trip per call (sub-millisecond,
   irrelevant next to an LLM round trip). `auto_install`/`create_files`
   are forced off regardless of any caller input — this adapter must
   never shell out or create files as a side effect of what is
   documented as a read-only tool.
   For the six `suggestion`-tier types: the adapter calls the matching
   handler's `analyze_error(error_message, file_path)` directly (no temp
   file needed — `analyze_error` only reads `error_output`/`file_path`
   strings, never touches disk) and returns `details["suggestions"]` as
   data. `apply_fix` is never called for these types — it only prints
   and returns `False`, so calling it would add nothing but noise on
   stdout.
4. If the `ImportError` handler reports success, the adapter reads the
   temp file back, computes a unified diff against the original `code`,
   and returns `resolved_by="fix"` with the patch. For a matched
   suggestion-tier type, returns `resolved_by="suggestion"` with the
   suggestion list. If nothing matches (including `ModuleNotFoundError`,
   `SyntaxError`, and any other type — see the handler audit table
   above), returns `resolved_by="no_match"`.
5. Telemetry is recorded (see below) as the last step, after the result
   is already computed — a telemetry failure must never affect the
   returned `FixResult`.

## Token-savings telemetry

Every call appends one JSON line to `~/.autofix/mcp_telemetry.jsonl`
(path configurable via env var):

```json
{"ts": "...", "error_type": "ImportError", "resolved_by": "fix", "input_chars": 842, "estimated_tokens_saved": 500}
```

Because the MCP tool never calls an LLM itself, there is no internal
ground truth to calibrate a token estimate against (unlike a design that
kept the Gemini path). So the estimate is **explicitly an assumption,
not a measurement**: a configurable constant
(`AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX`, default a documented placeholder
e.g. 500) representing "typical tokens an agent spends reasoning about
and patching this class of error." It is applied **only on
`resolved_by="fix"`** calls — a full, applied patch is the one case
that plausibly avoids a whole reasoning-and-edit round trip.
`resolved_by="suggestion"` calls log `estimated_tokens_saved: 0`: the
agent still has to read the suggestion and write the patch itself, so
claiming a token saving there would overstate the tool's value.
`resolved_by="no_match"` calls are logged too (also `0`), so the
success rate itself — the number that actually matters for evaluating
this direction — is never inflated by silently dropping misses.

A separate local script/console-command, `autofix-mcp-report` (a
human-facing report, not an MCP tool — the agent has no use for it),
reads the JSONL and prints: total calls, and count/rate by `resolved_by`
and by error type, and total estimated tokens saved using the
configured constant (with the constant's value shown in the output so
the number is never presented as more precise than it is).

## Error handling

The MCP tool call must never raise into the host agent. The handler
dispatch is wrapped; any exception becomes `resolved_by="no_match"` plus
a logged (not returned) server-side error — matching the defensive
pattern already used by `ToolsService`'s existing tool wrappers.
Telemetry writing is best-effort: wrapped separately, swallows its own
errors.

## Security

No new attack surface: the tool never executes caller-supplied code
(handlers operate via AST parsing and text patching, not `exec`/`eval`),
and it never reaches `DebuggerService`/`SandboxExecutor`. The one
handler that shells out (`ModuleNotFoundHandler`'s package install) is
already gated by the existing `SAFE_PACKAGE_ALLOWLIST` found in review —
unchanged by this feature, `auto_install` stays off by default in the
MCP adapter's `PythonFixer` config.

The sandbox-escape bug (code review finding #1) remains open and
Critical in the existing FastAPI/Gemini path. It is out of scope here
and tracked as an independent fix.

## Testing

- Unit tests for the new adapter (`infrastructure/mcp/server.py`):
  error-text parsing, temp-file lifecycle, diff generation, error
  wrapping — mocking `PythonFixer`/handlers where useful.
- Integration tests using FastMCP's test client, one per `resolved_by`
  outcome:
  - `fix`: a real missing-import case (e.g. `math.sqrt` used without
    `import math`) — asserts `resolved_by == "fix"`, a non-empty `diff`
    that actually applies, and `estimated_tokens_saved > 0`.
  - `suggestion`: a real `IndexError` case — asserts
    `resolved_by == "suggestion"`, a non-empty `suggestions` list, and
    `estimated_tokens_saved == 0`.
  - `no_match`: an error type with no handler coverage (e.g.
    `TypeError`) — asserts `resolved_by == "no_match"`.
- No dependency on `GEMINI_API_KEY` or network access — the whole test
  suite for this feature runs fully offline.

## Distribution

A new console-script entry point in `pyproject.toml`
(`autofix-mcp-server`), installed via `pip`/`pipx`. Added to Claude Code
with:

```
claude mcp add autofix -- autofix-mcp-server
```

## Open questions carried into planning

- Exact fields `ErrorParser.parse_error` needs populated (beyond its
  current `ModuleNotFoundError`/`KeyError`/`ZeroDivisionError` special
  cases) to reliably extract `missing_module`/`missing_function` for
  `ImportError` from text alone — needed since the `fix` tier's
  correctness depends entirely on this extraction.
- Final choice of default value for
  `AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX` — needs a short justification in
  the plan/README, not just a bare number.
