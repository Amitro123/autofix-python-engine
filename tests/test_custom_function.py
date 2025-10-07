# Test case for custom function creation
# This will test creating missing functions directly in the script

def process_data(data):
    """Auto - generated function by AutoFix"""
    # TODO: Add implementation
    return f"Processed: {data}"


print("Testing custom function creation...")

try:
    result = process_data("test")  # Should create this function
    print(f"Result: {result}")
except NameError as e:
    print(f"NameError: {e}")
    raise  # Let AutoFix handle this
