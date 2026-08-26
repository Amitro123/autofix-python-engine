import json
from collections import Counter
from pathlib import Path

from autofix_core.infrastructure.mcp.telemetry import ASSUMED_TOKENS_PER_FIX, DEFAULT_LOG_PATH


def format_report(log_path: Path) -> str:
    if not log_path.exists():
        return "Total calls: 0 (no telemetry recorded yet at {})".format(log_path)

    raw_lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = []
    skipped = 0
    for line in raw_lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            skipped += 1

    total = len(records)

    if total == 0:
        lines = ["Total calls: 0"]
        if skipped:
            lines.append(f"(skipped {skipped} malformed record{'s' if skipped != 1 else ''})")
        return "\n".join(lines)

    by_resolution = Counter(r["resolved_by"] for r in records)
    total_tokens_saved = sum(r["estimated_tokens_saved"] for r in records)
    fix_count = by_resolution.get("fix", 0)
    fix_rate = (fix_count / total) * 100

    by_type_and_resolution = Counter((r["error_type"], r["resolved_by"]) for r in records)

    lines = [
        f"Total calls: {total}",
        f"  fix: {fix_count}",
        f"  suggestion: {by_resolution.get('suggestion', 0)}",
        f"  no_match: {by_resolution.get('no_match', 0)}",
        "",
        f"Fix rate: {fix_rate:.1f}% ({fix_count}/{total})",
        "",
        "By error type:",
    ]
    for (error_type, resolved_by) in sorted(by_type_and_resolution):
        count = by_type_and_resolution[(error_type, resolved_by)]
        lines.append(f"  {error_type}: {count} {resolved_by}")

    lines += [
        "",
        f"Estimated tokens saved: {total_tokens_saved}",
        f"  (assumes {ASSUMED_TOKENS_PER_FIX} tokens per 'fix'-tier call — an assumption, not a measurement;"
        " set AUTOFIX_MCP_ASSUMED_TOKENS_PER_FIX to change it)",
    ]

    if skipped:
        lines.append("")
        lines.append(f"(skipped {skipped} malformed record{'s' if skipped != 1 else ''})")

    return "\n".join(lines)


def main() -> None:
    print(format_report(DEFAULT_LOG_PATH))


if __name__ == "__main__":
    main()
