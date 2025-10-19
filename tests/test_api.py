import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_root():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    # Update expectation to match new message
    assert "AutoFix API" in data["message"]
    assert "version" in data


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_fix_endpoint_success():
    """
    Test the main fix endpoint.
    Note: May fail if Gemini API is overloaded (503) or rate limited (429).
    """
    response = client.post(
        "/api/v1/fix",
        json={"code": "if True:\nprint('hello')"}
    )
    
    # Allow test to pass if API is unavailable (not a code issue)
    if response.status_code in [503, 429]:
        pytest.skip(f"Gemini API unavailable: {response.status_code}")
    
    assert response.status_code == 200
    
    data = response.json()
    
    # If API error, skip test
    if not data.get("success") and ("overloaded" in str(data).lower() or "quota" in str(data).lower()):
        pytest.skip("Gemini API temporary issue - not a code bug")
    
    assert data["success"] == True
    assert "fixed_code" in data
    assert "method" in data


def test_validate_code_valid():
    response = client.post("/api/v1/validate", json={"code": "print('hello')"})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == True

def test_validate_code_invalid():
    response = client.post("/api/v1/validate", json={"code": "if True print('hello')"})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] == False

def test_supported_errors():
    response = client.get("/api/v1/errors")
    assert response.status_code == 200
    data = response.json()
    assert len(data["errors"]) == 12

def test_stats():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "api_version" in data

def test_fix_batch():
    batch = [
        {"code": "def test():\nprint('ok')", "error": "SyntaxError", "auto_install": False}
    ]
    response = client.post("/api/v1/fix-batch", json=batch)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

def test_firebase_status():
    response = client.get("/api/v1/firebase-status")
    assert response.status_code == 200

def test_firebase_metrics():
    response = client.get("/api/v1/firebase-metrics")
    assert response.status_code == 200


class TestDebugAPI:
    """Tests for the /api/v1/debug endpoints."""

    def test_debug_health(self):
        """Test the health check endpoint for the debug service."""
        response = client.get("/api/v1/debug/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "DebuggerService"

    def test_execute_code_success(self):
        """Test successful code execution."""
        response = client.post(
            "/api/v1/debug/execute",
            json={"code": "x = 10\ny = 20\nprint(x + y)"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "30" in data["output"]
        assert "variables" in data
        assert "x" in data["variables"]

    def test_execute_code_error(self):
        """Test code execution that results in an error."""
        response = client.post(
            "/api/v1/debug/execute",
            json={"code": "print(1 / 0)"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ZeroDivisionError"

    def test_trace_code_success(self):
        """Test successful code tracing."""
        response = client.post(
            "/api/v1/debug/trace",
            json={"code": "a = 1\nb = 2\nc=a+b"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "c" in data["variables_at_end"]
        assert data["variables_at_end"]["c"]["value"] == 3

    def test_last_execution_workflow(self):
        """Test the get and clear last execution endpoints."""
        # First, run a trace to create a "last execution"
        client.post(
            "/api/v1/debug/trace",
            json={"code": "x = 'test'"}
        )

        # Now, get the last execution
        response_get = client.get("/api/v1/debug/last-execution")
        assert response_get.status_code == 200
        data_get = response_get.json()
        assert data_get["success"] is True
        assert "x" in data_get["variables_at_end"]

        # Delete the last execution
        response_delete = client.delete("/api/v1/debug/last-execution")
        assert response_delete.status_code == 200
        assert response_delete.json()["message"] == "Last execution cleared"

        # Verify it's gone
        response_get_after_delete = client.get("/api/v1/debug/last-execution")
        assert response_get_after_delete.status_code == 404
