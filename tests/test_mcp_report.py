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

    # Fix rate: fix-tier calls / total calls, as a percentage.
    assert "Fix rate: 50.0% (2/4)" in report

    # Per-(error_type, resolved_by) breakdown.
    assert "By error type:" in report
    assert "ImportError: 2 fix" in report
    assert "IndexError: 1 suggestion" in report
    assert "TypeError: 1 no_match" in report


def test_format_report_handles_missing_log_file(tmp_path):
    report = format_report(tmp_path / "does_not_exist.jsonl")
    assert "Total calls: 0" in report


def test_format_report_skips_malformed_lines_without_raising(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"
    good_record = {
        "ts": "t1",
        "error_type": "ImportError",
        "resolved_by": "fix",
        "input_chars": 10,
        "estimated_tokens_saved": 500,
    }
    log_path.write_text(
        json.dumps(good_record) + "\n" + "{not valid json at all\n",
        encoding="utf-8",
    )

    report = format_report(log_path)

    assert "Total calls: 1" in report
    assert "fix: 1" in report
    assert "(skipped 1 malformed record)" in report


def test_format_report_skips_schema_incomplete_records_without_crashing(tmp_path):
    # Syntactically valid JSON that's missing the fields this report
    # aggregates over -- e.g. an older schema version or a hand-edited
    # line. json.loads succeeding on its own doesn't guarantee this shape;
    # before the fix this raised KeyError inside format_report.
    log_path = tmp_path / "mcp_telemetry.jsonl"
    good_record = {
        "ts": "t1",
        "error_type": "ImportError",
        "resolved_by": "fix",
        "input_chars": 10,
        "estimated_tokens_saved": 500,
    }
    incomplete_record = {"ts": "2026-08-26T00:00:00Z"}  # missing everything else

    log_path.write_text(
        json.dumps(good_record) + "\n" + json.dumps(incomplete_record) + "\n",
        encoding="utf-8",
    )

    report = format_report(log_path)  # must not raise KeyError

    assert "Total calls: 1" in report
    assert "fix: 1" in report
    assert "(skipped 1 malformed record)" in report


def test_format_report_skips_non_object_json_values(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"
    good_record = {
        "ts": "t1",
        "error_type": "ImportError",
        "resolved_by": "fix",
        "input_chars": 10,
        "estimated_tokens_saved": 500,
    }
    log_path.write_text(
        json.dumps(good_record) + "\n"
        + json.dumps(["not", "an", "object"]) + "\n"
        + json.dumps("just a string") + "\n",
        encoding="utf-8",
    )

    report = format_report(log_path)

    assert "Total calls: 1" in report
    assert "(skipped 2 malformed records)" in report
