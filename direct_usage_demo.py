#!/usr/bin/env python3
"""
Direct usage demo of AutoFix without CLI
"""

from autofix import PythonFixer

def main():
    # Create a test script with errors
    test_script = """
def main():
    print("Testing direct AutoFix usage...")
    sleep(1)  # Missing import
    print("Done!")

if __name__ == "__main__":
    main()
"""
    
    # Write test script
    with open("temp_test.py", "w") as f:
        f.write(test_script)
    
    # Use AutoFix directly
    fixer = PythonFixer()
    print("Running AutoFix on temp_test.py...")
    success = fixer.run_script_with_fixes("temp_test.py")
    
    if success:
        print("✅ AutoFix succeeded!")
    else:
        print("❌ AutoFix failed")
    
    # Show the fixed script
    print("\nFixed script content:")
    with open("temp_test.py", "r") as f:
        print(f.read())

if __name__ == "__main__":
    main()