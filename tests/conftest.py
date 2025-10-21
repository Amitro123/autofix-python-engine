"""
pytest configuration for AutoFix test suite.

Provides:
- Module path setup for imports
- Environment variable loading
- Shared fixtures for all tests
- Conditional test skipping based on package availability
- Helper utilities for analyzer tests
"""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv


# =============================================================================
# Path Setup
# =============================================================================

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))


# =============================================================================
# Environment Setup
# =============================================================================

# Load environment variables for tests
load_dotenv()


# =============================================================================
# Package Availability Detection
# =============================================================================

HAS_BANDIT = importlib.util.find_spec("bandit") is not None
HAS_RADON = importlib.util.find_spec("radon") is not None


# =============================================================================
# Session-Scoped Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def project_root_path():
    """Provide project root path to tests."""
    return project_root


@pytest.fixture(scope="session")
def api_key():
    """
    Provide Gemini API key for tests.
    
    Skips test if GEMINI_API_KEY is not set in environment.
    """
    import os
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        pytest.skip("GEMINI_API_KEY not set - skipping test")
    return key


@pytest.fixture(scope="session")
def has_bandit() -> bool:
    """Return True when the 'bandit' package is importable in the test environment."""
    return HAS_BANDIT


@pytest.fixture(scope="session")
def has_radon() -> bool:
    """Return True when the 'radon' package is importable in the test environment."""
    return HAS_RADON


# =============================================================================
# Test Helpers
# =============================================================================

def make_completed_process(
    returncode: int = 0, 
    stdout: str = "", 
    stderr: str = ""
) -> SimpleNamespace:
    """
    Helper that creates a simple object resembling subprocess.CompletedProcess.
    
    Used primarily for mocking subprocess.run() results in BanditAnalyzer tests.
    
    Args:
        returncode: Exit code (0 = success, non-zero = error)
        stdout: Standard output content
        stderr: Standard error content
        
    Returns:
        SimpleNamespace with returncode, stdout, stderr attributes
        
    Example:
        >>> result = make_completed_process(0, '{"results": []}', '')
        >>> assert result.returncode == 0
        >>> assert result.stdout == '{"results": []}'
    """
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def completed_process_factory():
    """
    Provide the make_completed_process helper to tests via fixture injection.
    
    Example:
        def test_something(completed_process_factory):
            mock_result = completed_process_factory(0, "output", "")
            # Use mock_result...
    """
    return make_completed_process


# =============================================================================
# Pytest Markers
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "requires_bandit: mark test as requiring bandit package"
    )
    config.addinivalue_line(
        "markers", 
        "requires_radon: mark test as requiring radon package"
    )
    config.addinivalue_line(
        "markers",
        "requires_api_key: mark test as requiring GEMINI_API_KEY"
    )


# =============================================================================
# Test Collection Hooks
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically skip tests based on package availability.
    
    Tests marked with @pytest.mark.requires_bandit will be skipped if bandit is not installed.
    Tests marked with @pytest.mark.requires_radon will be skipped if radon is not installed.
    """
    skip_bandit = pytest.mark.skip(reason="bandit package not installed")
    skip_radon = pytest.mark.skip(reason="radon package not installed")
    
    for item in items:
        if "requires_bandit" in item.keywords and not HAS_BANDIT:
            item.add_marker(skip_bandit)
        if "requires_radon" in item.keywords and not HAS_RADON:
            item.add_marker(skip_radon)
