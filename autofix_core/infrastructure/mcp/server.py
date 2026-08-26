"""FastMCP server exposing the deterministic fix_error tool over stdio."""

import logging
from dataclasses import asdict

from fastmcp import FastMCP

from autofix_core.infrastructure.mcp.fix_error_adapter import FixResult, run_fix_error
from autofix_core.infrastructure.mcp.telemetry import log_fix_result

mcp = FastMCP("autofix-deterministic-fixer")

_logger = logging.getLogger(__name__)


@mcp.tool()
def fix_error(code: str, error_message: str, file_path: str = "") -> dict:
    """Try to resolve a Python error deterministically (no LLM call) before
    reasoning about it yourself. Returns resolved_by: "fix" (a ready-to-apply
    patch), "suggestion" (targeted guidance, no patch), or "no_match" (this
    tool has nothing for this error - proceed as you normally would)."""
    try:
        result = run_fix_error(
            code=code,
            error_message=error_message,
            file_path=file_path or None,
        )
    except Exception:  # never let an adapter bug crash the caller
        # The stdio transport uses real stdout for the JSON-RPC stream (see
        # fix_error_adapter._run_fix_tier), so the raw exception must never
        # be printed there -- log it server-side instead, via `logging`
        # (stderr), and never surface the exception text to the caller.
        _logger.exception("internal error while running fix_error")
        result = FixResult(
            error_type="UnknownError",
            resolved_by="no_match",
            explanation="internal error while processing this request",
        )

    try:
        log_fix_result(result, input_chars=len(code))
    except Exception:
        pass  # telemetry must never affect the tool result

    return asdict(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
