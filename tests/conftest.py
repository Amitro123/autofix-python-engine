"""
pytest configuration for AutoFix test suite.
Ensures proper module paths and environment setup.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

import pytest
from dotenv import load_dotenv

# Load environment variables for tests
load_dotenv()


@pytest.fixture(scope="session")
def project_root_path():
    """Provide project root path to tests"""
    return project_root


@pytest.fixture(scope="session")
def api_key():
    """Provide API key for tests"""
    import os
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        pytest.skip("GEMINI_API_KEY not set - skipping test")
    return key
