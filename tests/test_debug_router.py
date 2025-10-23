"""
Tests for debug router authentication and security.

Added based on GitHub Copilot security review recommendations.
Tests verify that debug endpoints require proper authentication.
"""

import os
from fastapi.testclient import TestClient
from autofix_core.infrastructure.api.routers.debug import router as debug_router
from fastapi import FastAPI, Depends
from autofix_core.application.services.debugger_service import DebuggerService
from unittest.mock import MagicMock
import pytest

app = FastAPI()
app.include_router(debug_router)


class FakeDebugger:
    """Mock debugger for testing without real execution."""
    
    def execute(self, code, timeout=5):
        """Fake execute - always succeeds."""
        from autofix_core.application.services.debugger_service import ExecutionResult
        return ExecutionResult(
            success=True,
            output="ok",
            error=None,
            error_type=None,
            variables={},
            execution_time=0.01,
            timeout=False
        )
    
    def execute_with_trace(self, code, timeout=5):
        """Fake trace - always succeeds."""
        return {
            "success": True,
            "stdout": "o",
            "stderr": "",
            "variables_at_end": {},
            "variables_at_error": None,
            "error_type": None,
            "error_message": None,
            "error_line": None,
            "stack_trace": None,
            "execution_context": None
        }


def get_fake_debugger():
    """Dependency override for testing."""
    return FakeDebugger()


def test_debug_routes_require_flag(monkeypatch):
    """Test that debug endpoints require DEBUG_API_ENABLED flag."""
    # Ensure debug disabled
    monkeypatch.delenv("DEBUG_API_ENABLED", raising=False)
    monkeypatch.delenv("DEBUG_API_KEY", raising=False)
    
    client = TestClient(app)
    r = client.post("/api/v1/debug/execute", json={"code": "x=1"})
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


def test_debug_routes_require_key(monkeypatch):
    """Test that debug endpoints require API key even when enabled."""
    # Enable debug but no key => still blocked
    monkeypatch.setenv("DEBUG_API_ENABLED", "1")
    monkeypatch.delenv("DEBUG_API_KEY", raising=False)
    
    client = TestClient(app)
    r = client.post("/api/v1/debug/execute", json={"code": "x=1"})
    assert r.status_code == 403
    assert "key" in r.json()["detail"].lower()


def test_debug_routes_with_valid_key(monkeypatch):
    """Test that debug endpoints work with valid authentication."""
    monkeypatch.setenv("DEBUG_API_ENABLED", "1")
    monkeypatch.setenv("DEBUG_API_KEY", "secret")
    
    # Override dependency to return fake debugger
    from autofix_core.infrastructure.api.dependencies import get_debugger_service
    app.dependency_overrides[get_debugger_service] = get_fake_debugger
    
    try:
        client = TestClient(app)
        headers = {"X-Debug-API-Key": "secret"}
        r = client.post(
            "/api/v1/debug/execute",
            json={"code": "x=1"},
            headers=headers
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
    finally:
        # Cleanup
        app.dependency_overrides.clear()


def test_debug_routes_with_invalid_key(monkeypatch):
    """Test that invalid API key is rejected."""
    monkeypatch.setenv("DEBUG_API_ENABLED", "1")
    monkeypatch.setenv("DEBUG_API_KEY", "correct-secret")
    
    client = TestClient(app)
    headers = {"X-Debug-API-Key": "wrong-secret"}
    r = client.post(
        "/api/v1/debug/execute",
        json={"code": "x=1"},
        headers=headers
    )
    assert r.status_code == 403
    assert "Invalid" in r.json()["detail"]


def test_debug_router_sanitizes_exceptions(monkeypatch):
    """Test that internal exceptions are sanitized before returning to client."""
    monkeypatch.setenv("DEBUG_API_ENABLED", "1")
    monkeypatch.setenv("DEBUG_API_KEY", "secret")
    
    # Make debugger raise with sensitive data
    class BadDebugger:
        def execute(self, *args, **kwargs):
            raise RuntimeError("internal secret: password=abcd123")
    
    from autofix_core.infrastructure.api.dependencies import get_debugger_service
    app.dependency_overrides[get_debugger_service] = lambda: BadDebugger()
    
    try:
        client = TestClient(app)
        headers = {"X-Debug-API-Key": "secret"}
        r = client.post(
            "/api/v1/debug/execute",
            json={"code": "x=1"},
            headers=headers
        )
        assert r.status_code == 500
        
        # Response should be generic - no internal details
        detail = r.json().get("detail", "")
        assert "Internal server error" in detail
        assert "password" not in detail
        assert "abcd123" not in detail
    finally:
        app.dependency_overrides.clear()
