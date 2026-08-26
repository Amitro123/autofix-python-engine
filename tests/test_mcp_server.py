"""Tests for the FastMCP server exposing the fix_error tool (Task 6)."""

import asyncio

from fastmcp import Client

import autofix_core.infrastructure.mcp.server as server_module
from autofix_core.infrastructure.mcp.server import mcp


def test_fix_error_tool_returns_a_fix_for_import_error():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {
                    "code": "from time import nonexistent_function\n",
                    "error_message": "ImportError: cannot import name 'nonexistent_function' from 'time' (unknown location)",
                },
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "fix"
    assert payload["error_type"] == "ImportError"
    assert "import time" in payload["patched_code"]
    assert payload["telemetry"]["estimated_tokens_saved"] > 0


def test_fix_error_tool_returns_no_match_for_unhandled_error():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {"code": "1/0\n", "error_message": "TypeError: bad operand"},
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "no_match"
    assert payload["telemetry"]["estimated_tokens_saved"] == 0


def test_fix_error_tool_never_raises_on_malformed_input():
    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {"code": "", "error_message": ""},
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "no_match"


def test_fix_error_tool_logs_and_masks_the_exception_when_run_fix_error_raises(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("some sensitive internal detail")

    monkeypatch.setattr(server_module, "run_fix_error", _boom)

    logged_calls = []
    real_log_fix_result = server_module.log_fix_result

    def _spy_log_fix_result(result, input_chars):
        logged_calls.append(result)
        real_log_fix_result(result, input_chars=input_chars)

    monkeypatch.setattr(server_module, "log_fix_result", _spy_log_fix_result)

    async def _run():
        async with Client(mcp) as client:
            return await client.call_tool(
                "fix_error",
                {"code": "irrelevant", "error_message": "irrelevant"},
            )

    result = asyncio.run(_run())
    payload = result.data if hasattr(result, "data") else result

    assert payload["resolved_by"] == "error"
    assert "some sensitive internal detail" not in str(payload)

    assert len(logged_calls) == 1
    assert logged_calls[0].resolved_by == "error"
    assert logged_calls[0].error_type == "UnknownError"
