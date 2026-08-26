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
