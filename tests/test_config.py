"""
Test Configuration Helper
Loads environment variables for tests
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}")

def get_api_key() -> str:
    """Get Gemini API key from environment"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found!\n"
            "Please create .env file with your API key.\n"
            "See .env.example for template."
        )
    
    return api_key

def has_api_key() -> bool:
    """Check if API key is available"""
    return os.getenv('GEMINI_API_KEY') is not None
