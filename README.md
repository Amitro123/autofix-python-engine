# 🔧 AutoFix Python Engine

A lightweight, pure Python error resolution tool that automatically fixes common development issues without AI dependencies.

## 🎯 Features

- **Pure Python Logic** - No AI or external API dependencies
- **Automatic Package Installation** - Detects and installs missing packages via pip
- **Module Creation** - Creates missing local modules with basic structure
- **Import Error Handling** - Fixes invalid imports and missing symbols
- **Name Error Resolution** - Creates placeholder functions for undefined names
- **Basic Syntax Fixes** - Handles common syntax errors like missing colons
- **Test Module Detection** - Recognizes placeholder/test imports and provides guidance

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Amitro123/autofix-python-engine.git
cd autofix-python-engine

# No additional dependencies required - uses only Python standard library
```

## 🚀 Usage

### Command Line
```bash
# Fix a Python script
python autofix_python.py script.py

# Example with a problematic script
python autofix_python.py test_missing_imports.py
```

### What It Fixes

**Missing Packages:**
```python
import requests  # → pip install requests
import pandas    # → pip install pandas
import numpy     # → pip install numpy
```

**Missing Local Modules:**
```python
import my_utils  # → creates my_utils.py with basic structure
```

**Invalid Imports:**
```python
from os import nonexistent_function  # → comments out invalid import
```

**Undefined Functions:**
```python
result = process_data(x)  # → creates placeholder process_data function
```

**Basic Syntax Errors:**
```python
if condition  # → if condition:
def my_func() # → def my_func():
```

## 📋 Supported Error Types

| Error Type | Description | Fix Strategy |
|------------|-------------|--------------|
| `ModuleNotFoundError` | Missing packages/modules | Install via pip or create local module |
| `ImportError` | Invalid imports | Comment out problematic imports |
| `NameError` | Undefined variables/functions | Create placeholder implementations |
| `SyntaxError` | Basic syntax issues | Add missing colons, fix formatting |

## 🔍 Examples

### Example 1: Missing Package
```python
# script.py
import requests
response = requests.get("https://api.github.com")
print(response.json())
```

```bash
$ python autofix_python.py script.py
🔧 AutoFix Python Engine - Pure Python Error Resolution
============================================================
2025-09-01 20:06:15 - autofix-python - INFO - Fixing script: script.py
2025-09-01 20:06:15 - autofix-python - INFO - Installing package: requests
2025-09-01 20:06:18 - autofix-python - INFO - Successfully installed requests
✅ Script fixed successfully!
```

### Example 2: Missing Local Module
```python
# app.py
from utils import helper_function
result = helper_function("test")
print(result)
```

```bash
$ python autofix_python.py app.py
🔧 AutoFix Python Engine - Pure Python Error Resolution
============================================================
2025-09-01 20:06:20 - autofix-python - INFO - Created local module: utils.py
2025-09-01 20:06:20 - autofix-python - INFO - Created placeholder function: helper_function
✅ Script fixed successfully!
```

### Example 3: Test Module Detection
```python
# test.py
import a_non_existent_module
print("This won't run")
```

```bash
$ python autofix_python.py test.py
🔧 AutoFix Python Engine - Pure Python Error Resolution
============================================================
2025-09-01 20:06:22 - autofix-python - WARNING - Module 'a_non_existent_module' appears to be a test/placeholder
2025-09-01 20:06:22 - autofix-python - INFO - Recommendations:
2025-09-01 20:06:22 - autofix-python - INFO -   1. Replace with a real package name
2025-09-01 20:06:22 - autofix-python - INFO -   2. Install a package: pip install <package-name>
2025-09-01 20:06:22 - autofix-python - INFO -   3. Create a local module file if intentional
❌ Could not fix all errors
```

## 🛠️ Known Package Mappings

The engine includes mappings for common packages:

```python
{
    'cv2': 'opencv-python',
    'PIL': 'Pillow', 
    'sklearn': 'scikit-learn',
    'yaml': 'PyYAML',
    'bs4': 'beautifulsoup4',
    # ... and many more
}
```

## 🔧 Configuration

The engine works out of the box with sensible defaults:
- **Max retries**: 3 attempts per script
- **Timeout**: 30 seconds per script execution
- **Package timeout**: 60 seconds per pip install

## 🎯 Design Philosophy

- **Lightweight**: Single file, no external dependencies
- **Fast**: Pure Python logic without API calls
- **Safe**: Creates backups and validates changes
- **Educational**: Provides clear logging of all actions taken

## 🚫 Limitations

- **No AI Analysis**: Uses pattern matching, not intelligent code understanding
- **Basic Syntax Fixes**: Only handles simple syntax errors
- **No Complex Logic**: Cannot generate sophisticated implementations
- **Python Only**: Focused solely on Python error resolution

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Related Projects

- **AutoFix Engine**: Full AI-enhanced multi-language system at [autofix-engine](https://github.com/Amitro123/autofix-engine)

---

**AutoFix Python Engine** - Simple, fast, reliable Python error fixing without the complexity.
