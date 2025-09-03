#!/usr/bin/env python3
"""
Run all demo test scripts with the interactive CLI
"""

import subprocess
import sys
import os
from pathlib import Path

def run_demo_tests():
    """Run all demo test scripts"""
    demo_scripts = [
        "tests/test_missing _module_demo.py",
        "tests/test_fabric_demo.py", 
        "tests/test_colorama_demo.py",
        "tests/test_real_package.py",
        "tests/test_clean_demo.py"
    ]
    
    print("🧪 Running all demo tests with interactive CLI...")
    print("=" * 50)
    
    for script in demo_scripts:
        if os.path.exists(script):
            print(f"\n🎯 Testing: {script}")
            print("-" * 30)
            
            # Run with 'y' response for automatic testing
            try:
                result = subprocess.run(
                    f'echo y | python autofix_cli_interactive.py "{script}"',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
                    
            except Exception as e:
                print(f"ERROR running {script}: {e}")
        else:
            print(f"⚠️  Script not found: {script}")
    
    print("\n✅ All demo tests completed!")

if __name__ == "__main__":
    run_demo_tests()
