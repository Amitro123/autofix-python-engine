"""FastMCP server exposing the deterministic fix_error tool over stdio."""

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
    tool has nothing for this error - proceed as you normally would)."""
    try:
        result = run_fix_error(
            code=code,
            error_message=error_message,
            file_path=file_path or None,
        )
    except Exception as exc:  # never let an adapter bug crash the caller
        return {
            "error_type": "UnknownError",
            "resolved_by": "no_match",
            "patched_code": None,
            "diff": None,
            "suggestions": None,
            "explanation": f"internal error: {exc}",
        }

    try:
        log_fix_result(result, input_chars=len(code))
    except Exception:
        pass  # telemetry must never affect the tool result

    return asdict(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
