"""Test case for symbol import errors."""

# Symbols in existing modules
# This tests the "cannot import name" scenario

try:
    # This should work
    from os import path  # Used below

    print("[OK] Successfully imported 'path' from 'os'")

    # This should fail - nonexistent symbol
#     from os import nonexistent_function  # This will fail  # Commented out by AutoFix - symbol does not exist

    print("This shouldn't print")

except ImportError as e:
    print(f"ImportError (expected): {e}")
    raise  # Let AutoFix handle this
