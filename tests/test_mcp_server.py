"""Tests for the FastMCP server exposing the fix_error tool (Task 6)."""

import asyncio

from fastmcp import Client

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
