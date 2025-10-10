"""AutoFix service - Real integration with AutoFix engine"""
import tempfile
import os
import sys
import subprocess
from typing import Dict, Any

class AutoFixService:
    """Service to connect FastAPI to AutoFix CLI"""
    
    def __init__(self):
        """Initialize service"""
        pass
    
    def fix_code(self, code: str, auto_install: bool = False) -> Dict[str, Any]:
        """
        Fix Python code using the real AutoFix engine
        
        Args:
            code: Python code string
            auto_install: Auto-install missing packages
            
        Returns:
            Dictionary with fix results
        """
        # Create temp file with the code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Save original code
            original_code = code
            
            # Run AutoFix CLI on the temp file
            cmd = [
                sys.executable,  # python
                '-m', 'autofix.cli.autofix_cli_interactive',
                temp_file,
                '--auto-fix'
            ]
            
            if auto_install:
                cmd.append('--auto-install')
            
            # Execute AutoFix
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Read the fixed code
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    fixed_code = f.read()
            else:
                fixed_code = original_code
            
            # Determine if fix was successful
            success = result.returncode == 0
            
            # Parse error type from output
            error_type = self._parse_error_type(result.stdout, result.stderr)
            
            # Get changes
            changes = self._get_changes(original_code, fixed_code, error_type)
            
            return {
                "success": success,
                "original_code": original_code,
                "fixed_code": fixed_code if success else None,
                "error_type": error_type,
                "changes": changes
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "original_code": code,
                "fixed_code": None,
                "error_type": "Timeout",
                "changes": []
            }
        except Exception as e:
            return {
                "success": False,
                "original_code": code,
                "fixed_code": None,
                "error_type": str(type(e).__name__),
                "changes": []
            }
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def _parse_error_type(self, stdout: str, stderr: str) -> str:
        """Parse error type from AutoFix output"""
        output = stdout + stderr
        
        error_types = [
            "SyntaxError",
            "IndentationError",
            "ModuleNotFoundError",
            "TypeError",
            "IndexError",
            "NameError",
            "AttributeError"
        ]
        
        for error_type in error_types:
            if error_type in output:
                return error_type
        
        return "Unknown"
    
    def _get_changes(self, original: str, fixed: str, error_type: str) -> list:
        """Get list of changes made"""
        if original == fixed:
            return []
        
        changes = []
        
        original_lines = original.split('\n')
        fixed_lines = fixed.split('\n')
        
        for i, (orig_line, fixed_line) in enumerate(zip(original_lines, fixed_lines), 1):
            if orig_line != fixed_line:
                changes.append({
                    "line": i,
                    "type": error_type or "Unknown",
                    "description": f"Changed: '{orig_line.strip()}' → '{fixed_line.strip()}'"
                })
        
        return changes if changes else [
            {
                "line": 1,
                "type": error_type or "Unknown",
                "description": "Code was modified"
            }
        ]
