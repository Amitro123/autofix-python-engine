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
