"""Regression test for stdout corruption of the MCP JSON-RPC stream.

This launches the real MCP server as a subprocess talking real stdio (not
fastmcp's in-memory Client, which never touches a real stdout fd and is
therefore structurally blind to this bug), drives it with raw newline-
delimited JSON-RPC, and asserts every line the subprocess writes to stdout
is valid JSON.

Before the fix (ImportErrorHandler gained a quiet=True mode, threaded down
from fix_error_adapter.py's PythonFixer config), ImportErrorHandler.apply_fix's
bare print() calls write plain-text lines directly to the real stdout fd,
which sits on the exact same stream the stdio transport uses for JSON-RPC
responses. That corrupts the protocol stream for every ImportError call --
the only error type that reaches the "fix" tier, i.e. the whole reason
this MCP tool exists.

An earlier version of this fix used contextlib.redirect_stdout instead of
quiet=True. That was itself broken: redirect_stdout mutates sys.stdout
process-globally, and two overlapping redirect_stdout windows on
different threads/tasks can restore each other's saved stream on exit,
leaking output into the wrong place or swallowing an unrelated response.
quiet=True avoids the problem at the source -- the handler never writes
to stdout at all, so there's no global state to race on. The second test
below sends two overlapping tools/call requests (without waiting for the
first response) specifically to guard against that class of bug
resurfacing.
"""

import json
import os
import subprocess
import sys
import time

INIT_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "stdio-regression-test", "version": "0.1.0"},
    },
}

INITIALIZED_NOTIFICATION = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}

FIX_ERROR_CALL = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "fix_error",
        "arguments": {
            "code": "from time import nonexistent_function\n",
            "error_message": (
                "ImportError: cannot import name 'nonexistent_function' "
                "from 'time' (unknown location)"
            ),
        },
    },
}


def _send(proc, message: dict) -> None:
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _read_lines_for(proc, seconds: float) -> list:
    """Collect whatever lines the subprocess writes to stdout within a
    time budget. Non-blocking-ish: relies on the subprocess flushing
    promptly (the stdio transport does `await stdout.flush()` after every
    write), and simply stops reading once the deadline passes."""
    import selectors

    lines = []
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            events = sel.select(timeout=remaining)
            if not events:
                continue
            line = proc.stdout.readline()
            if not line:
                break
            lines.append(line.rstrip("\n"))
    finally:
        sel.close()
    return lines


def test_all_stdout_lines_from_the_real_server_process_are_valid_json(tmp_path):
    # This is a genuinely separate subprocess, so tests/conftest.py's
    # monkeypatch fixture (which only affects the in-process module state)
    # cannot redirect its telemetry writes. Use the officially supported
    # env var override instead, so this test never touches the user's
    # real ~/.autofix/mcp_telemetry.jsonl.
    env = dict(os.environ)
    env["AUTOFIX_MCP_TELEMETRY_PATH"] = str(tmp_path / "test_telemetry.jsonl")

    proc = subprocess.Popen(
        [sys.executable, "-m", "autofix_core.infrastructure.mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    try:
        _send(proc, INIT_REQUEST)
        init_lines = _read_lines_for(proc, 10)
        assert init_lines, (
            "server produced no stdout output for the initialize request "
            f"(stderr so far: {proc.stderr.read(4000) if proc.poll() is not None else '<still running>'})"
        )

        _send(proc, INITIALIZED_NOTIFICATION)
        _send(proc, FIX_ERROR_CALL)

        more_lines = _read_lines_for(proc, 10)

        all_lines = init_lines + more_lines
        assert all_lines, "server produced no stdout output at all"

        bad_lines = []
        for line in all_lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                bad_lines.append(line)

        assert not bad_lines, (
            "non-JSON line(s) found interleaved in the JSON-RPC stdout stream "
            f"(stdout corruption): {bad_lines!r}\nfull stdout captured: {all_lines!r}"
        )

        # Sanity: we should have actually gotten a response to the tools/call
        # (id == 2), not just the initialize response, otherwise this test
        # isn't really exercising the fix_error/ImportError code path.
        got_tool_response = any(
            (lambda parsed: isinstance(parsed, dict) and parsed.get("id") == 2)(
                json.loads(line)
            )
            for line in all_lines
        )
        assert got_tool_response, (
            f"never saw a response to the tools/call request (id=2); full stdout: {all_lines!r}"
        )
    finally:
        proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def test_overlapping_tool_calls_do_not_corrupt_the_stdout_stream(tmp_path):
    """Send two fix_error calls back-to-back, without waiting for the first
    response before sending the second, so the server may process them
    concurrently (whether via internal threading or otherwise). This is
    the scenario a process-global contextlib.redirect_stdout fix would get
    wrong: overlapping redirect windows can restore each other's saved
    stream on exit. Assert every stdout line is still valid JSON and both
    requests got a response."""
    env = dict(os.environ)
    env["AUTOFIX_MCP_TELEMETRY_PATH"] = str(tmp_path / "test_telemetry.jsonl")

    proc = subprocess.Popen(
        [sys.executable, "-m", "autofix_core.infrastructure.mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    second_call = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "fix_error",
            "arguments": {
                "code": "from time import another_missing_thing\n",
                "error_message": (
                    "ImportError: cannot import name 'another_missing_thing' "
                    "from 'time' (unknown location)"
                ),
            },
        },
    }

    try:
        _send(proc, INIT_REQUEST)
        init_lines = _read_lines_for(proc, 10)
        assert init_lines, "server produced no stdout output for the initialize request"

        _send(proc, INITIALIZED_NOTIFICATION)
        # Send both tool calls immediately, one after the other, without
        # reading a response in between -- this is what makes the two
        # fix_error invocations able to overlap inside the server.
        _send(proc, FIX_ERROR_CALL)
        _send(proc, second_call)

        more_lines = _read_lines_for(proc, 15)

        all_lines = init_lines + more_lines
        assert all_lines, "server produced no stdout output at all"

        bad_lines = []
        parsed_responses = []
        for line in all_lines:
            try:
                parsed_responses.append(json.loads(line))
            except json.JSONDecodeError:
                bad_lines.append(line)

        assert not bad_lines, (
            "non-JSON line(s) found interleaved in the JSON-RPC stdout stream "
            f"under overlapping calls (stdout corruption): {bad_lines!r}\n"
            f"full stdout captured: {all_lines!r}"
        )

        response_ids = {
            parsed.get("id")
            for parsed in parsed_responses
            if isinstance(parsed, dict) and "id" in parsed
        }
        assert {2, 3}.issubset(response_ids), (
            "expected responses to both overlapping tools/call requests "
            f"(id=2 and id=3); got response ids: {response_ids!r}, "
            f"full stdout: {all_lines!r}"
        )
    finally:
        proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
