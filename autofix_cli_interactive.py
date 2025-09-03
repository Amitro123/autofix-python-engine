import subprocess
import sys
import os
import re
import threading
import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone

# Firebase Admin SDK for production metrics (transparent to users)
try:
    from firebase_admin import credentials, firestore, initialize_app
    import firebase_admin
    
    firebase_key_path = "firebase-key.json"
    if os.path.exists(firebase_key_path):
        with open(firebase_key_path, 'r') as f:
            __firebase_config = json.load(f)
        
        __app_id = os.getenv('APP_ID', 'autofix-default-app')
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(__firebase_config)
            initialize_app(cred)
        db = firestore.client()
        METRICS_ENABLED = True
    else:
        # Graceful fallback when firebase-key.json not present
        db = None
        METRICS_ENABLED = False
except (ModuleNotFoundError, Exception):
    # Graceful fallback when Firebase Admin SDK not available
    db = None
    METRICS_ENABLED = False

@dataclass
class ErrorDetails:
    """Structured error details"""
    error_type: str
    line_number: Optional[int] = None
    suggestion: str = "Fix the error"
    extra_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}

class ErrorHandler(ABC):
    """Abstract base class for error handlers"""
    
    @abstractmethod
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    def extract_details(self, error_output: str) -> ErrorDetails:
        """Extract error details from output"""
        pass
    
    @abstractmethod
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        """Attempt to fix the error"""
        pass
    
    @property
    @abstractmethod
    def error_name(self) -> str:
        """Human-readable error name"""
        pass

class ModuleNotFoundHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "ModuleNotFoundError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        match = re.search(r"No module named '(.*?)'", error_output)
        module_name = match.group(1) if match else None
        
        return ErrorDetails(
            error_type="missing_module",
            suggestion=f"Install missing module: {module_name}" if module_name else "Install missing module",
            extra_data={"module_name": module_name}
        )
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        module_name = details.extra_data.get("module_name")
        if not module_name:
            return False
            
        if module_name == 'metrics':  # Test module
            placeholder_path = os.path.join(os.path.dirname(script_path), "metrics.py")
            return self._create_placeholder_module(module_name, placeholder_path)
        else:
            return self._install_module(module_name)
    
    def _create_placeholder_module(self, module_name: str, file_path: str) -> bool:
        try:
            with open(file_path, 'w') as f:
                f.write(f"# Placeholder for '{module_name}' module\n")
                f.write("def log_duration(func):\n")
                f.write("    def wrapper(*args, **kwargs):\n")
                f.write("        return func(*args, **kwargs)\n")
                f.write("    return wrapper\n")
            return True
        except Exception:
            return False
    
    def _install_module(self, module_name: str) -> bool:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", module_name], 
                         check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    @property
    def error_name(self) -> str:
        return "ModuleNotFoundError"

class TypeErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "TypeError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[-2] if len(line_matches) > 1 else line_matches[0]) if line_matches else None
        
        # Determine specific TypeError
        if "unsupported operand type" in error_output or "can only concatenate" in error_output:
            error_type = "unsupported_operand"
            suggestion = "Fix type mismatch in operation (e.g., string + int)"
        elif "takes" in error_output and "positional argument" in error_output:
            error_type = "argument_count"
            suggestion = "Fix function argument count mismatch"
        elif "missing" in error_output and "required positional argument" in error_output:
            error_type = "missing_argument"
            suggestion = "Missing required function arguments"
        else:
            error_type = "general_type"
            suggestion = "Fix type-related error"
        
        return ErrorDetails(error_type=error_type, line_number=line_number, suggestion=suggestion)
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not details.line_number or details.line_number > len(lines):
                return False
            
            line_idx = details.line_number - 1
            current_line = lines[line_idx]
            fixed_line = current_line
            
            if details.error_type == 'unsupported_operand':
                # Fix string + number concatenation
                fixed_line = re.sub(r'(["\'][^"\']*["\'])\s*\+\s*(\d+)', r'\1 + str(\2)', fixed_line)
                fixed_line = re.sub(r'(\d+)\s*\+\s*(["\'][^"\']*["\'])', r'str(\1) + \2', fixed_line)
                fixed_line = re.sub(r'(\w+)\s*=\s*(\w+)\s*\+\s*(\d+)', r'\1 = \2 + str(\3)', fixed_line)
            
            if fixed_line != current_line:
                lines[line_idx] = fixed_line
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            return False
        except Exception:
            return False
    
    @property
    def error_name(self) -> str:
        return "TypeError"

class IndentationErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "IndentationError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        if "expected an indented block" in error_output:
            error_type = "missing_indentation"
            suggestion = "Add proper indentation to the code block"
        elif "unindent does not match" in error_output:
            error_type = "inconsistent_indentation"
            suggestion = "Fix inconsistent indentation"
        elif "unexpected indent" in error_output:
            error_type = "unexpected_indent"
            suggestion = "Remove unnecessary indentation"
        else:
            error_type = "general_indentation"
            suggestion = "Fix indentation issues"
        
        return ErrorDetails(error_type=error_type, line_number=line_number, suggestion=suggestion)
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if details.error_type == 'missing_indentation' and details.line_number:
                line_idx = details.line_number - 1
                if line_idx < len(lines):
                    current_line = lines[line_idx].strip()
                    if current_line:
                        # Add 4 spaces indentation
                        lines[line_idx] = '    ' + current_line + '\n'
            elif details.error_type == 'inconsistent_indentation':
                # Convert tabs to spaces
                lines = [line.expandtabs(4) for line in lines]
            elif details.error_type == 'unexpected_indent' and details.line_number:
                line_idx = details.line_number - 1
                if line_idx < len(lines):
                    lines[line_idx] = lines[line_idx].lstrip() + '\n'
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except Exception:
            return False
    
    @property
    def error_name(self) -> str:
        return "IndentationError"

class IndexErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "IndexError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        if "list index out of range" in error_output:
            error_type = "list_index_out_of_range"
            suggestion = "Check list length before accessing"
        elif "string index out of range" in error_output:
            error_type = "string_index_out_of_range"
            suggestion = "Check string length before accessing"
        else:
            error_type = "general_index"
            suggestion = "Add bounds checking"
        
        return ErrorDetails(error_type=error_type, line_number=line_number, suggestion=suggestion)
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not details.line_number or details.line_number > len(lines):
                return False
            
            line_idx = details.line_number - 1
            current_line = lines[line_idx]
            
            # Find list/string access patterns and add bounds checking
            access_pattern = r'(\w+)\[(\w+|\d+)\]'
            matches = re.findall(access_pattern, current_line)
            
            fixed_line = current_line
            for obj_name, index_expr in matches:
                unsafe_access = f"{obj_name}[{index_expr}]"
                if index_expr.isdigit():
                    safe_access = f"{obj_name}[{index_expr}] if len({obj_name}) > {index_expr} else None"
                else:
                    safe_access = f"{obj_name}[{index_expr}] if {index_expr} < len({obj_name}) else None"
                fixed_line = fixed_line.replace(unsafe_access, safe_access)
            
            if fixed_line != current_line:
                lines[line_idx] = fixed_line
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            return False
        except Exception:
            return False
    
    @property
    def error_name(self) -> str:
        return "IndexError"

class SyntaxErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "SyntaxError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        return ErrorDetails(
            error_type="syntax_error",
            line_number=line_number,
            suggestion="Fix broken keywords and syntax issues"
        )
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix common broken keywords
            fixes = {
                r'\bi f\b': 'if', r'\bd ef\b': 'def', r'\bc lass\b': 'class',
                r'\be lse\b': 'else', r'\be lif\b': 'elif', r'\bf or\b': 'for',
                r'\bw hile\b': 'while', r'\bt ry\b': 'try', r'\be xcept\b': 'except'
            }
            
            for pattern, replacement in fixes.items():
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
        except Exception:
            return False
    
    @property
    def error_name(self) -> str:
        return "SyntaxError"

class AutoFixer:
    """Main AutoFixer class that orchestrates error detection and fixing"""
    
    def __init__(self):
        self.handlers = [
            ModuleNotFoundHandler(),
            TypeErrorHandler(),
            IndentationErrorHandler(),
            IndexErrorHandler(),
            SyntaxErrorHandler()
        ]
    
    def run_script(self, script_path: str) -> Tuple[bool, Optional[subprocess.CalledProcessError]]:
        """Run script with loading spinner"""
        print(f"INFO: Running script: {script_path}")
        
        spinner_event = threading.Event()
        spinner_thread = threading.Thread(target=self._loading_spinner, args=(spinner_event,))
        spinner_thread.start()

        try:
            result = subprocess.run([sys.executable, script_path], 
                                 capture_output=True, text=True, check=True)
            spinner_event.set()
            spinner_thread.join()
            print("\r" + " " * 30 + "\r", end="")
            print(result.stdout)
            return True, None
        except subprocess.CalledProcessError as e:
            spinner_event.set()
            spinner_thread.join()
            print("\r" + " " * 30 + "\r", end="")
            return False, e
        except FileNotFoundError:
            spinner_event.set()
            spinner_thread.join()
            print(f"ERROR: File not found: {script_path}")
            return False, None
    
    def _loading_spinner(self, stop_event):
        """Console spinner for progress indication"""
        spinner = ['|', '/', '-', '\\']
        i = 0
        while not stop_event.is_set():
            sys.stdout.write(f"\r  Running... {spinner[i % len(spinner)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    def find_handler(self, error_output: str) -> Optional[ErrorHandler]:
        """Find appropriate handler for the error"""
        for handler in self.handlers:
            if handler.can_handle(error_output):
                return handler
        return None
    
    def save_metrics(self, script_path: str, status: str, original_error: str = None, 
                    error_details: Dict[str, Any] = None, message: str = None,
                    fix_attempts: int = 0, fix_duration: float = 0.0, **kwargs):
        """Save metrics transparently to developer's Firebase project"""
        if not METRICS_ENABLED or not db:
            return False
        
        try:
            # Build standardized metrics document
            metrics = {
                "app_id": __app_id,
                "script_path": os.path.basename(script_path),  # Only filename for privacy
                "status": status,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "fix_attempts": fix_attempts,
                "fix_duration": fix_duration
            }
            
            # Add optional fields if provided
            if original_error:
                metrics["original_error"] = original_error
            
            if error_details:
                metrics["error_details"] = error_details
            else:
                metrics["error_details"] = {}
            
            if message:
                metrics["message"] = message
            else:
                # Generate default message based on status
                if status == "success":
                    metrics["message"] = "Script executed successfully"
                elif status == "fix_succeeded":
                    metrics["message"] = f"Successfully fixed {original_error or 'error'}"
                elif status == "fix_failed":
                    metrics["message"] = f"Failed to fix {original_error or 'error'}"
                elif status == "canceled":
                    metrics["message"] = f"User canceled {original_error or 'error'} fix"
                else:
                    metrics["message"] = f"Status: {status}"
            
            # Add any additional fields
            metrics.update(kwargs)
            
            # Save to Firestore: artifacts/{app_id}/metrics
            collection_ref = db.collection('artifacts').document(__app_id).collection('metrics')
            collection_ref.add(metrics)
            
            return True
            
        except Exception as e:
            # Silent failure - don't interrupt user experience
            return False
    
    def process_script(self, script_path: str) -> bool:
        """Main processing logic"""
        if not os.path.exists(script_path):
            print(f"ERROR: Script not found: {script_path}")
            return False

        # Try running the script
        success, error = self.run_script(script_path)
        
        if success:
            print("INFO: Script ran successfully with no errors.")
            self.save_metrics(
                script_path=script_path, 
                status="success",
                message="Script executed without errors"
            )
            return True

        if not error:
            print("INFO: Unknown error occurred.")
            self.save_metrics(
                script_path=script_path, 
                status="failure", 
                original_error="Unknown",
                message="Unknown error occurred during execution"
            )
            return False

        # Find appropriate handler
        handler = self.find_handler(error.stderr)
        
        if not handler:
            print("INFO: Error type not supported for automatic fixing.")
            print("Full error output:")
            print(error.stderr)
            self.save_metrics(
                script_path=script_path, 
                status="unsupported_error",
                error_details={"stderr": error.stderr[:500]},  # Limit size
                message="Error type not supported for automatic fixing"
            )
            return False

        # Extract error details and ask for permission
        details = handler.extract_details(error.stderr)
        
        print(f"INFO: Detected error: {handler.error_name}")
        print(f"INFO: {details.suggestion}")
        if details.line_number:
            print(f"INFO: Error on line {details.line_number}")
        
        user_input = input(f"ACTION REQUIRED: Fix the {handler.error_name}? (y/n): ").strip().lower()
        
        if user_input != 'y':
            print("INFO: Fix canceled by user.")
            self.save_metrics(
                script_path=script_path, 
                status="canceled", 
                original_error=handler.error_name,
                error_details={"error_type": details.error_type, "line_number": details.line_number},
                message=f"User canceled {handler.error_name} fix"
            )
            return False

        # Attempt the fix
        print(f"INFO: Attempting to fix {handler.error_name}...")
        
        if handler.fix_error(script_path, details):
            print(f"INFO: {handler.error_name} fixed. Retrying script execution...")
            
            # Retry the script
            success, _ = self.run_script(script_path)
            if success:
                print("INFO: The issue has been resolved, the script now runs successfully!")
                self.save_metrics(
                    script_path=script_path, 
                    status="fix_succeeded", 
                    original_error=handler.error_name,
                    error_details={
                        "error_type": details.error_type, 
                        "line_number": details.line_number,
                        "fix_applied": True
                    },
                    message=f"Successfully fixed {handler.error_name}",
                    fix_attempts=1
                )
                return True
            else:
                print(f"ERROR: The script still fails after fixing {handler.error_name}.")
                self.save_metrics(
                    script_path=script_path, 
                    status="fix_failed", 
                    original_error=handler.error_name,
                    error_details={
                        "error_type": details.error_type, 
                        "line_number": details.line_number,
                        "fix_applied": True,
                        "still_failing": True
                    },
                    message=f"Fix applied but {handler.error_name} still occurs",
                    fix_attempts=1
                )
                return False
        else:
            print(f"ERROR: Failed to automatically fix {handler.error_name}.")
            self.save_metrics(
                script_path=script_path, 
                status="fix_failed", 
                original_error=handler.error_name,
                error_details={
                    "error_type": details.error_type, 
                    "line_number": details.line_number,
                    "fix_applied": False
                },
                message=f"Failed to apply fix for {handler.error_name}",
                fix_attempts=1
            )
            return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python autofix_cli_interactive.py <script_path>")
        return
    
    fixer = AutoFixer()
    fixer.process_script(sys.argv[1])

if __name__ == "__main__":
    main()