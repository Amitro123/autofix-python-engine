import json

from autofix_core.infrastructure.mcp.fix_error_adapter import FixResult
from autofix_core.infrastructure.mcp.telemetry import log_fix_result


def test_log_fix_result_writes_one_jsonl_line_per_call(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"
    fix_result = FixResult(error_type="ImportError", resolved_by="fix", patched_code="x", diff="d")

    log_fix_result(fix_result, input_chars=42, log_path=log_path)
    log_fix_result(fix_result, input_chars=10, log_path=log_path)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["error_type"] == "ImportError"
    assert record["resolved_by"] == "fix"
    assert record["input_chars"] == 42
    assert record["estimated_tokens_saved"] == 500


def test_log_fix_result_reports_zero_savings_for_suggestion_and_no_match(tmp_path):
    log_path = tmp_path / "mcp_telemetry.jsonl"

    log_fix_result(
        FixResult(error_type="IndexError", resolved_by="suggestion", suggestions=["x"]),
        input_chars=5,
        log_path=log_path,
    )
    log_fix_result(
        FixResult(error_type="TypeError", resolved_by="no_match"),
        input_chars=5,
        log_path=log_path,
    )

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").strip().splitlines()]
    assert all(r["estimated_tokens_saved"] == 0 for r in records)


def test_log_fix_result_never_raises_when_path_is_unwritable(tmp_path):
    unwritable_dir = tmp_path / "does" / "not" / "exist"
    log_path = unwritable_dir / "mcp_telemetry.jsonl"

    # Should not raise even though the parent directory doesn't exist and
    # this function must never create it in a way that could fail loudly.
    log_fix_result(
        FixResult(error_type="ImportError", resolved_by="fix"),
        input_chars=1,
        log_path=log_path,
    )
