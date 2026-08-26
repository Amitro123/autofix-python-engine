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
