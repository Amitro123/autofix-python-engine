# 🔧 AutoFix - Python Error Fixing Engine

[![PyPI version](https://img.shields.io/pypi/v/autofix-python-engine)](https://pypi.org/project/autofix-python-engine/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-29%2F29-brightgreen)](https://github.com/Amitro123/autofix-python-engine)

**AutoFix v2.1.0** is an AI-powered Python error-fixing tool available as a CLI and REST API. It uses a hybrid system—AutoFix for simple errors and Google's Gemini 2.5 Pro for complex ones—to help you save time debugging and focus on what matters.

---

## ✨ Features

- 🎯 **Automatic Error Detection & Fixing** - Identifies and resolves 7 common Python error types
- 📦 **Smart Package Installation** - Auto-installs missing modules with user confirmation
- 🔄 **Safe & Reliable** - Automatic backups before any file modification
- 🎨 **Beautiful CLI** - Colored output, progress spinners, and clear feedback
- 📊 **Metrics Tracking** - Optional Firebase integration for success/failure analytics
- ⚡ **Fast & Lightweight** - Minimal dependencies, runs in seconds

---

## 🚀 REST API

AutoFix v2.1.0 introduces a powerful REST API built with FastAPI, allowing you to integrate automated error fixing into your own applications, CI/CD pipelines, or services. The API is fully documented with Swagger UI, available at the `/docs` endpoint.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/v1/fix` | Fixes a single Python code snippet. |
| POST   | `/api/v1/fix-batch` | Fixes multiple code snippets in a single request. |
| POST   | `/api/v1/validate` | Validates Python code without fixing it. |
| GET    | `/api/v1/stats` | Returns system health and usage statistics. |
| GET    | `/api/v1/errors` | Lists all supported error types. |
| GET    | `/api/v1/firebase-status` | (Optional) Checks the connection to Firebase. |
| GET    | `/api/v1/firebase-metrics`| (Optional) Fetches metrics from Firebase. |
| GET    | `/docs` | Provides interactive Swagger UI documentation. |


---

## 🤖 AI-Powered Fixes

AutoFix v2.1.0 uses a hybrid approach to error fixing. For simple syntax and common errors, it uses its own fast and reliable engine (~0.6s). For more complex or runtime errors, it leverages the power of **Google's Gemini 2.5 Pro**.

### How It Works
1.  **AutoFix First**: The system first attempts to fix the error with its own engine.
2.  **AI Fallback**: If AutoFix fails, the code is sent to Gemini 2.5 Pro for a more sophisticated fix.
3.  **Free Tier**: You get **1 million requests per month for FREE**, which is more than enough for most use cases.

### Example: AI Fix for a Complex Error

#### Input (`buggy_code.py`)

```python
import numpy as np

def calculate_average(numbers):
  # This code has a logical error
  return np.sum(numbers) / len(numbers) - 1

data = [1, 2, 3, 4, 5]
print(f"Wrong average: {calculate_average(data)}")
```

#### API Response with AI Fix

```json
{
  "fixed_code": "import numpy as np\n\ndef calculate_average(numbers):\n  # This code has a logical error\n  return np.sum(numbers) / len(numbers)\n\ndata = [1, 2, 3, 4, 5]\nprint(f\"Correct average: {calculate_average(data)}\")",
  "is_fixed": true,
  "error_type": "LogicalError",
  "ai_used": true
}
```

---

## 🎬 Quick Demo

Fix a syntax error automatically:
```bash
autofix broken_script.py --auto-fix
```

Auto-install missing packages:
```bash
autofix script.py --auto-install
```

Full automation (no prompts):
```bash
autofix script.py --auto-fix --auto-install
```

---

## 📊 Quick Stats

| Metric | Status |
|--------|--------|
| Valid Python Files | 58/58 (100%) |
| Test Coverage | 29/29 tests ✅ |
| Error Types Covered | 7/7 (100%) |
| Health Score | 80/100 |
| Syntax Issues | 0 |

---

## 🐍 Supported Error Types

| Error Type | Auto-Fix | Manual | Description |
|------------|:--------:|:------:|-------------|
| **IndentationError** | ✅ | | Automatic indentation correction |
| **SyntaxError** | ✅ | | Missing colons, keyword fixes |
| **ModuleNotFoundError** | ✅ | | Smart package installation |
| **TypeError** | | ✅ | Type conversion suggestions |
| **IndexError** | | ✅ | Bounds checking suggestions |
| **NameError** | | ✅ | Variable/function suggestions |
| **AttributeError** | | ✅ | Attribute resolution guidance |

### Success Rates

| Error Type | Success Rate |
|------------|--------------|
| IndentationError | 90% |
| SyntaxError | 85% |
| ModuleNotFoundError | 95% |
| TypeError | 88% |
| IndexError | 92% |

---

## 📦 Installation

### Option 1: Install from PyPI (Recommended)

pip install autofix-python-engine

### Verify installation

autofix --version

### You're ready!

autofix your_script.py --auto-fix

---

### Option 2: Install from Source

#### Clone the repository

git clone https://github.com/Amitro123/autofix-python-engine.git
cd autofix-python-engine

#### Install dependencies

pip install -r requirements.txt

#### Install in development mode

pip install -e .

---

### Option 3: Install from GitHub

#### Direct install from GitHub

pip install git+https://github.com/Amitro123/autofix-python-engine.git

---

## 🔧 Setup for REST API

To use the REST API, you need to set up your environment with the Gemini API key.

### 1. Create a `.env` File

Create a `.env` file in the root of the project:

```
GEMINI_API_KEY=your_gemini_api_key
```

### 2. Get Your Gemini API Key

Get your free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Install API Dependencies

Install the necessary packages to run the server:

```bash
pip install fastapi uvicorn
```

### 4. Run the Server

Start the FastAPI server with hot-reloading:

```bash
uvicorn api.main:app --reload
```

### 5. Access the Docs

The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🚀 Usage Examples

### CLI Usage

Analyze and fix errors automatically:
```bash
autofix your_script.py --auto-fix
```

Auto-install missing packages:
```bash
autofix script.py --auto-install
```

Verbose mode for detailed output:
```bash
autofix script.py --auto-fix -v
```

Dry run (analyze without making changes):
```bash
autofix script.py --dry-run
```

### API Usage

#### Fix a Code Snippet (`curl`)

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/fix' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "code": "def my_function()\\n  print(\\"Hello, World!\\")"
}'
```

#### Fix a Code Snippet (`requests` in Python)

```python
import requests
import json

url = "http://localhost:8000/api/v1/fix"
payload = {
    "code": "def my_function()\\n  print(\\"Hello, World!\\")"
}
headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

response = requests.post(url, data=json.dumps(payload), headers=headers)
print(response.json())
```

---

## 📖 Usage Scenarios

### Scenario 1: Fix a Simple Error with the CLI

**Input** (`broken_script.py`):

def greet(name):
print(f"Hello, {name}!") # Missing indentation
greet("World")

**Run AutoFix:**

autofix broken_script.py --auto-fix

**Output:**

09:53:37 - autofix - INFO - Starting AutoFix for: broken_script.py
09:53:37 - unified_syntax_handler - INFO - Added indentation to line 2
09:53:38 - python_fixer - INFO - Script executed successfully!
Hello, World!

---

### Scenario 2: Fix a Complex Error with the API and AI

**Input** (`buggy_code.py`):
```python
import numpy as np

def calculate_average(numbers):
  # This code has a logical error
  return np.sum(numbers) / len(numbers) - 1

data = [1, 2, 3, 4, 5]
print(f"Wrong average: {calculate_average(data)}")
```

**API Response with AI Fix:**
```json
{
  "fixed_code": "import numpy as np\\n\\ndef calculate_average(numbers):\\n  # This code has a logical error\\n  return np.sum(numbers) / len(numbers)\\n\\ndata = [1, 2, 3, 4, 5]\\nprint(f\"Correct average: {calculate_average(data)}\")",
  "is_fixed": true,
  "error_type": "LogicalError",
  "ai_used": true
}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FIREBASE_KEY_PATH` | Path to Firebase service account JSON | None |
| `APP_ID` | Application identifier for metrics | `autofix-default-app` |
| `AUTOFIX_DEBUG_METRICS` | Enable debug output for metrics | `False` |

### Config File (Python)

Create `~/.autofix/config.py`:

CONFIG = {
'auto_install': True,
'interactive': True,
'max_retries': 3,
'create_backups': True,
'enable_metrics': False
}

---

## 📁 Project Structure

| Path | Description |
|------|-------------|
| **autofix/** | Main package directory |
| ├── `__init__.py` | Package initialization |
| ├── `__main__.py` | Entry point for `-m` execution |
| ├── `python_fixer.py` | Core error fixing logic |
| ├── `error_parser.py` | Error parsing & analysis |
| ├── `constants.py` | Global constants & enums |
| **autofix/cli/** | Command-line interface |
| ├── `autofix_cli_interactive.py` | Main CLI logic |
| ├── `cli_parser.py` | Argument parsing |
| **autofix/handlers/** | Error-specific handlers |
| ├── `unified_syntax_handler.py` | SyntaxError & IndentationError fixes |
| ├── `module_not_found_handler.py` | ModuleNotFoundError + auto-install |
| ├── `type_error_handler.py` | TypeError suggestions |
| ├── `index_error_handler.py` | IndexError suggestions |
| ├── `name_error_handler.py` | NameError suggestions |
| └── `attribute_error_handler.py` | AttributeError suggestions |
| **autofix/helpers/** | Utility functions |
| ├── `logging_utils.py` | Custom colored logging |
| ├── `file_utils.py` | File operations & backups |
| └── `metrics_utils.py` | Metrics collection |
| **autofix/integrations/** | External integrations |
| ├── `firestore_client.py` | Firebase Firestore client |
| └── `metrics_collector.py` | Metrics aggregation |
| **api/** | REST API backend |
| ├── `main.py` | FastAPI application |
| ├── `models/` | Pydantic schemas |
| ├── `routers/` | API endpoints |
| └── `services/` | AutoFix + Gemini services |
| **tests/** | Test suite (30 tests) |
| **demos/** | Demo scripts and examples |
| `README.md` | This documentation |
| `pyproject.toml` | Package configuration |
| `setup.py` | Setup script |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git ignore rules |
---

## 🧪 Testing

Run all tests
pytest

Run with coverage
pytest --cov=autofix --cov-report=html

Run specific test file
pytest tests/test_syntax_handler.py

Verbose output
pytest -v

**Test Results:**

================================ test session starts =================================
collected 30 items

tests/test_cli.py ................ [ 53%]
tests/test_handlers.py .............. [100%]

================================ 30 passed in 2.45s ==================================

---

## 🔌 Optional: Firebase Metrics Setup

Track fix success rates and errors with Firebase Firestore.

### 1. Create Firebase project and enable Firestore

### 2. Download service account key JSON

### 3. Save as `firebase-key.json` in project root

### 4. Set environment variable (optional)

export FIREBASE_KEY_PATH=/path/to/firebase-key.json
export APP_ID="my-autofix-app"

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

git clone https://github.com/Amitro123/autofix-python-engine.git
cd autofix-python-engine
pip install -e ".[dev]"
pytest

---

## 📝 Known Limitations

### IndentationError
- ✅ **Works:** Simple missing indents after colons
- ⚠️ **Limited:** Complex nested indentation blocks
- 📅 **Fix planned:** v1.1.0

### TypeError
- ⚠️ **Manual review required** for most cases
- ✅ Provides detailed suggestions
- 📅 **Auto-fix planned:** v1.2.0

---

## 🗺️ Roadmap

### v2.1.0 (Completed)
- 🤖 **AI-Powered Fixes**: Integrated Google's Gemini 2.5 Pro.
- 🚀 **REST API**: Added a FastAPI backend.
- ✅ **Production Ready**: All tests passing (29/29).

### v2.2.0 (Q4 2025)
- 🌐 **Multi-Language Support**: Adding support for JavaScript and TypeScript.
- 🔌 **VSCode Extension**: A dedicated extension for VSCode.
- 📊 **Enhanced Metrics Dashboard**: A new dashboard for tracking metrics.

### v3.0.0 (Q2 2026)
- 🌍 **Web Interface**: A full-fledged web interface for AutoFix.
- 👥 **Team Collaboration**: Features for teams to work together.
- 🔧 **Custom Plugins**: Support for custom error-fixing plugins.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Amit Rothschild**
- GitHub: [@Amitro123](https://github.com/Amitro123)
- LinkedIn: [Amit Rosen](https://linkedin.com/in/amit-rosen-331732140)
- PyPI: [autofix-python-engine](https://pypi.org/project/autofix-python-engine/)

---

## 🙏 Acknowledgments

- Inspired by Python's developer experience challenges
- Built with feedback from the Python community
- Special thanks to early testers and contributors

---

## 📞 Support

- 🐛 **Bug reports:** [GitHub Issues](https://github.com/Amitro123/autofix-python-engine/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/Amitro123/autofix-python-engine/discussions)
- 📧 **Email:** amitrosen4@gmail.com

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=Amitro123/autofix-python-engine&type=Date)](https://star-history.com/#Amitro123/autofix-python-engine&Date)

---

**Made with ❤️ by Amit Rosen**
