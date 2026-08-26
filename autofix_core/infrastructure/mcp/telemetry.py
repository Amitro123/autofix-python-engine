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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DEFAULT_ASSUMED_TOKENS_PER_FIX = 500


def _read_assumed_tokens_per_fix() -> int:
    """Parse AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX defensively.

    This runs at import time (server.py imports the adapter, which imports
    this module), so an unguarded int() here would make the whole MCP
    server fail to start on a single env-var typo -- turning a best-effort
    metric into a startup failure. Warn on stderr (never stdout: this
    module is imported by the MCP server, and stdout is reserved for the
    stdio JSON-RPC transport) and fall back to the default instead.
    """
    raw = os.environ.get("AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX")
    if raw is None:
        return _DEFAULT_ASSUMED_TOKENS_PER_FIX
    try:
        return int(raw)
    except ValueError:
        print(
            f"autofix-mcp: AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX={raw!r} is not a valid "
            f"integer; falling back to {_DEFAULT_ASSUMED_TOKENS_PER_FIX}",
            file=sys.stderr,
        )
        return _DEFAULT_ASSUMED_TOKENS_PER_FIX


ASSUMED_TOKENS_PER_FIX = _read_assumed_tokens_per_fix()


def estimated_tokens_saved_for(resolved_by: str) -> int:
    """The one place this computation lives -- both FixResult.__post_init__
    and log_fix_result call this instead of each re-deriving the same
    `ASSUMED_TOKENS_PER_FIX if resolved_by == "fix" else 0` rule, so the
    two can't quietly drift apart."""
    return ASSUMED_TOKENS_PER_FIX if resolved_by == "fix" else 0

DEFAULT_LOG_PATH = Path(
    os.environ.get("AUTOFIX_MCP_TELEMETRY_PATH", str(Path.home() / ".autofix" / "mcp_telemetry.jsonl"))
)


def log_fix_result(result, input_chars: int, log_path: Optional[Path] = None) -> None:
    path = log_path or DEFAULT_LOG_PATH
    tokens_saved = estimated_tokens_saved_for(result.resolved_by)

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
