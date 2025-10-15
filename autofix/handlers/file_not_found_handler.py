from autofix.core.base_handler import ErrorHandler
from typing import Tuple, Dict
import re


class FileNotFoundHandler(ErrorHandler):
    """Handler for FileNotFoundError - provides suggestions"""
    
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can handle the error"""
        return "FileNotFoundError" in error_output or "No such file or directory" in error_output
    
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        """Analyze FileNotFoundError and provide details"""
        
        # Extract line number
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        # Extract file path that wasn't found
        # Pattern: FileNotFoundError: [Errno 2] No such file or directory: 'data.txt'
        filepath_match = re.search(r"'([^']+)'", error_output)
        missing_file = filepath_match.group(1) if filepath_match else "unknown"
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "missing_file": missing_file,
            "suggestions": [
                f"Check if file exists before opening: Path('{missing_file}').exists()",
                f"Create the file if it doesn't exist",
                f"Verify file path - current: '{missing_file}'",
                f"Check file permissions",
                "Use try/except to handle missing files gracefully"
            ],
            "file_path": file_path,
            "example_fix": self._generate_example_fix(missing_file)
        }
        
        return "file_not_found", f"File '{missing_file}' not found", details
    
    def _generate_example_fix(self, filepath: str) -> str:
        """Generate example fix code"""
        return f"""
💡 Example Fix:

# Before (crashes if file missing):
with open('{filepath}') as f:
    data = f.read()

# After Option 1 - Check if exists:
from pathlib import Path

if Path('{filepath}').exists():
    with open('{filepath}') as f:
        data = f.read()
else:
    print(f"File not found: {filepath}")
    # Or create it:
    Path('{filepath}').touch()

# After Option 2 - Use try/except:
try:
    with open('{filepath}') as f:
        data = f.read()
except FileNotFoundError:
    print(f"File not found: {filepath}")
    data = ""  # default value

# After Option 3 - Create if missing:
from pathlib import Path
file_path = Path('{filepath}')
if not file_path.exists():
    file_path.write_text("")  # Create empty file
with open(file_path) as f:
    data = f.read()
"""
    
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        """Provide suggestions - cannot auto-fix file system issues"""
        
        print(f"\n{'='*60}")
        print(f"FileNotFoundError detected in {file_path}")
        print(f"{'='*60}")
        print(f"Missing file: '{details.get('missing_file')}'")
        
        if details.get('line_number'):
            print(f"Line: {details['line_number']}")
        
        print("\n📝 Suggestions:")
        for i, suggestion in enumerate(details.get('suggestions', []), 1):
            print(f"  {i}. {suggestion}")
        
        if 'example_fix' in details:
            print(details['example_fix'])
        
        print("\nFileNotFoundError requires manual review - PARTIAL result")
        print(f"{'='*60}\n")
        return False
