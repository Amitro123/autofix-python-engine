"""AutoFix service - Real integration with AutoFix engine"""
import tempfile
import os
import sys
import subprocess
import time
from typing import Dict, Any
from api.services.gemini_service import GeminiService


class AutoFixService:
    """Service to connect FastAPI to AutoFix CLI"""
    
    def __init__(self):
        """Initialize service with Gemini fallback"""
        self.gemini = GeminiService()
    
    def fix_code(self, code: str, auto_install: bool = False) -> Dict[str, Any]:
        """
        Fix Python code - try AutoFix first, then Gemini with cache
        
        Args:
            code: Python code string
            auto_install: Auto-install missing packages
            
        Returns:
            Dictionary with fix results
        """
        start_time = time.time()
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            original_code = code
            
            # Try AutoFix first
            cmd = [
                sys.executable,
                '-m', 'autofix.cli.autofix_cli_interactive',
                temp_file,
                '--auto-fix'
            ]
            
            if auto_install:
                cmd.append('--auto-install')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Read fixed code
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    fixed_code = f.read()
            else:
                fixed_code = original_code
            
            success = result.returncode == 0
            error_type = self._parse_error_type(result.stdout, result.stderr)
            changes = self._get_changes(original_code, fixed_code, error_type)
            
            # ✅ NEW: Check if code actually changed OR if error detected
            code_unchanged = (original_code == fixed_code)
            
            if (not success or (code_unchanged and error_type != "Unknown")) and self.gemini.is_enabled():
                print(f"🤖 AutoFix didn't fix {error_type}, trying Gemini with cache...")
                
                # Get error message
                error_msg = error_type  # Just use error type!

                # ===== Check cache first! =====
                if self.gemini.cache:
                    cached_result = self.gemini.cache.get(code, error_msg)
                    
                    if cached_result:
                        execution_time = time.time() - start_time
                        print(f"⚡ Cache HIT! Returning in {execution_time:.3f}s")
                        return {
                            'success': True,
                            'original_code': original_code,
                            'fixed_code': cached_result.get('fixed_code'),
                            'error_type': error_type,
                            'method': 'gemini', 
                            'cache_hit': True,
                            'execution_time': execution_time,
                            'changes': [{
                                'line': 1,
                                'type': error_type,
                                'description': f"Fixed by Gemini AI (cached)"
                            }]
                        }

                
                # Cache miss - call Gemini API
                print("Cache miss - calling Gemini API...")
                gemini_fix = self.gemini.fix_with_ai(code, error_msg)
                
                if gemini_fix and gemini_fix != code:
                    # Clean up code blocks
                    gemini_fix = gemini_fix.replace('``````', '').strip()
                    print("✅ Gemini fixed it!")
                    return {  # ← Return immediately!
                        "success": True,
                        "original_code": original_code,
                        "fixed_code": gemini_fix,
                        "error_type": error_type,
                        "method": "gemini",
                        "cache_hit": False,
                        "changes": [{
                            "line": 1,
                            "type": error_type,
                            "description": f"Fixed by Gemini AI: {error_type}"
                        }]
                    }
                else:
                    print("❌ Gemini couldn't fix it either")
                    # Fall through to return AutoFix result

            return {
                "success": success,
                "original_code": original_code,
                "fixed_code": fixed_code if success else None,
                "error_type": error_type,
                "method": "autofix",
                "cache_hit": False,
                "changes": changes
            }
            
        except subprocess.TimeoutExpired:
            # Timeout - try Gemini with cache
            if self.gemini.is_enabled():
                print("⏱️ Timeout, trying Gemini with cache...")
                
                # Check cache first
                if self.gemini.cache:
                    cached_result = self.gemini.cache.get(code, "Execution timeout")
                    if cached_result:
                        print("⚡ Cache HIT for timeout case")
                        return {
                            "success": True,
                            "original_code": code,
                            "fixed_code": cached_result.get('fixed_code'),
                            "error_type": "Timeout",
                            "method": "gemini",
                            "cache_hit": True,
                            "changes": [{"line": 1, "type": "Timeout", "description": "Fixed by Gemini (cached)"}]
                        }
                
                # Cache miss - call Gemini
                gemini_fix = self.gemini.fix_with_ai(code, "Execution timeout")
                if gemini_fix:
                    return {
                        "success": True,
                        "original_code": code,
                        "fixed_code": gemini_fix,
                        "error_type": "Timeout",
                        "method": "gemini",
                        "cache_hit": False,
                        "changes": [{"line": 1, "type": "Timeout", "description": "Fixed by Gemini"}]
                    }
            
            return {
                "success": False,
                "original_code": code,
                "fixed_code": None,
                "error_type": "Timeout",
                "method": "failed",
                "cache_hit": False,
                "changes": []
            }
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {
                "success": False,
                "original_code": code,
                "fixed_code": None,
                "error_type": str(type(e).__name__),
                "method": "failed",
                "cache_hit": False,
                "changes": []
            }
        finally:
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
        
        # Simple change detection
        for i, (orig_line, fix_line) in enumerate(zip(original_lines, fixed_lines)):
            if orig_line != fix_line:
                changes.append({
                    "line": i + 1,
                    "type": error_type,
                    "description": f"Fixed {error_type} on line {i + 1}"
                })
        
        return changes
