# MCP `fix_error` Roadmap

Scope: the MCP server exposing the deterministic `fix_error` tool
(`autofix_core/infrastructure/mcp/`). Not the wider `autofix-python-engine`
product roadmap (see `ROADMAP.md` at the repo root for that, though it
predates this feature and is tracked separately).

Origin: an external assessment ("What This MCP Server Should Be — An
Honest Assessment & Blueprint", 2026-08-26) reviewed PR #22 (merged) and
PR #23 (then-open) and proposed a target state. This doc keeps only the
items that were **not yet implemented** when that assessment was folded
in, so it doesn't restate work already merged. Check off items here as
they land; when a section is fully done, delete it rather than leaving a
stale checklist — this file should never be a second place capability
claims can drift from the code (see "Governance" below).

## Already done (for context — not the point of this file)

Verified against `main` before writing this doc, not assumed:

- Four-state `resolved_by` contract: `"fix"` / `"suggestion"` /
  `"no_match"` / `"error"` (the `"error"` state was the last piece,
  landed alongside this doc).
- `ModuleNotFoundError` → `"suggestion"` (reuses `ModuleNotFoundHandler.analyze_error`).
- `ImportError` on a recognized-but-not-auto-importable module →
  `"suggestion"` instead of a silent `"no_match"` that discarded the
  handler's own guidance.
- Stdio-safety enforced at the `_run_fix_tier` boundary (`assert`
  guarding that only the audited, `quiet`-mode-aware `ImportError` path
  can ever reach it).
- Token-savings computation consolidated into one function
  (`telemetry.estimated_tokens_saved_for`), used by both `FixResult` and
  `log_fix_result`.
- `NameError` on a name that resolves to exactly one confident import
  (`IMPORT_SUGGESTIONS`/`MATH_FUNCTIONS` — e.g. `Counter`, `sqrt`) →
  `"fix"` tier, with the dedupe guard against re-patching an import
  that's already present. Ambiguous names (`MULTI_IMPORT_SUGGESTIONS`,
  e.g. `dump`) and the `os.path` naming heuristic stay `"suggestion"` —
  not confident enough to auto-apply.
- `autofix-mcp-report` already breaks down calls by `(error_type,
  resolved_by)` and reports a fix-rate percentage — the raw material the
  "telemetry-driven roadmap" idea below needs already exists.

## P1 — next (real coverage gains, each needs its own safety review)

- [ ] **Accept a full multi-line traceback as input, not just a hand-parsed
      one-liner.** `ErrorParser.parse_error` already scans all lines for a
      `File "..."` pattern and the trailing `Type: message` line, so this
      may already work end-to-end — this task is "verify with a real
      multi-line traceback test, then document it," not necessarily new
      parsing code. If a gap turns up, fix it there.
- [ ] **`AttributeError` known-pattern suggestions** (e.g. `plt.hold` and
      other patterns the CLI already special-cases). Needs: confirm
      whether a dedicated handler class exists for this or whether the
      logic only lives inline in `python_fixer.py`'s `_fix_attribute_error`
      — if the latter, extracting an `analyze_error`-shaped helper first
      (matching the pattern the other suggestion-tier handlers use) is
      probably the right shape, not duplicating detection logic in the
      adapter.

## P2 — later

- [ ] **Registry-driven capability matrix.** A single source of truth
      (error type → tier → what's returned) that both the `fix_error` tool
      docstring and the README's coverage table are generated from, instead
      of two hand-maintained lists that can drift. Worth it once coverage
      grows past what's easy to eyeball (roughly: once P1 above lands).
- [ ] **Use the telemetry data, not just collect it.** The report already
      shows `no_match` share by error type — the follow-through this item
      actually needs is a person (or a future session) periodically reading
      that output on real usage and using it to prioritize the next P1/P2
      item, not new code.
- [ ] **Consolidate remaining duplicated logic:**
  - `ImportErrorHandler._backup_file` / `_read_file_content` vs the
    identically-named methods on `PythonFixer` — two three-line methods on
    unrelated classes; a shared mixin was judged premature when this was
    first flagged (see the implementation ledger for this feature) and
    still is unless a third caller shows up.
  - `NameError` suggestion text: the CLI's legacy `_fix_name_error` (prints
    via `python_fixer.py`) and the adapter's `_name_error_suggestions`
    (`fix_error_adapter.py`) independently derive similar guidance from
    `IMPORT_SUGGESTIONS`/`MATH_FUNCTIONS`. Not urgent — different output
    channels (print vs. structured list) make a shared implementation less
    obviously a win than the token-savings dedup was — but worth a look if
    either path changes.

## Explicit non-goals (carried forward, still true)

Preserved so a future change doesn't accidentally cross these without a
deliberate decision to do so:

- **No LLM fallback inside this tool.** The calling agent is the fallback
  on `"no_match"`. Adding one here would compete with the agent's own
  reasoning instead of covering its blind spots, and would break the
  zero-token pitch this tool exists for.
- **No fix-tier expansion beyond a small set of provably deterministic
  transforms.** `"fix"` is a promise (a patch the caller can trust without
  re-checking); each candidate (import insertion, import-for-name, maybe a
  missing-colon repair) needs its own correctness argument before joining
  the tier, the same way `ImportError`'s did.
- **Never execute caller code, never write the caller's real files, never
  install anything.** The read-only, side-effect-free contract is the
  product, not an implementation detail.
- **Never claim measured precision for token savings.** `estimated_tokens_saved`
  stays an explicitly-labeled assumption; `ASSUMED_TOKENS_PER_FIX` stays a
  directional heuristic, not something to quietly start presenting as data.
- **No new tools before this one is well used.** Add a second MCP tool
  (e.g. something `explain`-shaped) only once telemetry on `fix_error`
  itself shows a real gap a second tool would close — not speculatively.

## Governance notes (process, not code — for whoever picks these up)

- Before merging any change that touches `_run_fix_tier` or adds a new
  entry to `_FIX_TIER_ERROR_TYPES`: confirm no `print()` is reachable from
  any code path `run_fix_error` can invoke for that type. The `assert` in
  `_run_fix_tier` catches the dispatch-level version of this; it doesn't
  catch a new bug introduced *inside* `ImportErrorHandler` itself.
- This file is a living roadmap, not a spec — it's expected to shrink as
  items land and grow as telemetry surfaces new gaps. If it goes stale
  (an item here already shipped, or the actual behavior no longer matches
  what "Already done" claims), fix the drift in the same change that
  notices it, the same discipline the README and tool docstring already
  get.
