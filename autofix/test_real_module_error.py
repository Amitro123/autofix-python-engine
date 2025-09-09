# test_real_module_error.py
import nonexistent_package_xyz_456
print("This should trigger ModuleNotFoundError that AutoFix can handle")
