# -*- coding: utf-8 -*-
import shutil
import os
import tempfile
import sys
from pathlib import Path

class FixTransaction:
    """
    context manager for file fix transactions
    creates a backup of the file before fixing it
    and restores it if the fix fails

    """
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.backup_path = None
        
    def __enter__(self):
        """
      with block entry
        """
        try:
            #make sure the file exists
            if not self.file_path.is_file():
                raise FileNotFoundError(f"Original file not found: {self.file_path}")

            #create a backup
            self.backup_path = Path(tempfile.mktemp(suffix=".bak"))
            shutil.copy2(self.file_path, self.backup_path)
            
            print(f"created backup: {self.file_path} -> {self.backup_path}")
            return self
        except Exception as e:
            print(f"error creating backup: {e}", file=sys.stderr)
            # if backup fails, there is no point to continue
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with block exit
        """
        if exc_type:
            # if an error occurred, perform rollback
            print("\n-------------------------------------------")
            print(f"error during fix. performing rollback...")
            try:
                if self.backup_path and self.backup_path.is_file():
                    shutil.copy2(self.backup_path, self.file_path)
                    print(f"restored file: {self.file_path}")
            except Exception as e:
                print(f"warning: rollback failed: {e}", file=sys.stderr)
            
            # delete backup
            if self.backup_path and self.backup_path.is_file():
                os.remove(self.backup_path)
                print(f"deleted backup: {self.backup_path}")

            return False # to ensure the error is not suppressed
        
        # if no error, the fix succeeded - delete backup
        if self.backup_path and self.backup_path.is_file():
            print(f"\nfix succeeded. deleting backup: {self.backup_path}")
            os.remove(self.backup_path)


# --- examples ---

def fix_with_success(file_path: Path):
    """example of successful fix"""
    with FixTransaction(file_path) as transaction:
        print(f"inside transaction. fixing {file_path}...")
        # fix - add line to file
        with open(file_path, 'a') as f:
            f.write("\n# This line was added successfully by the fixer.")
        print("fix succeeded!")

def fix_with_failure(file_path: Path):
    """example of failed fix"""
    try:
        with FixTransaction(file_path) as transaction:
            print(f"inside transaction. fixing {file_path}...")
            # fix - raise error
            raise ValueError("An error occurred during the fix process!")
    except ValueError as e:
        print(f"error: {e}")
        print("rollback should be performed automatically.")

# creating a dummy file for testing
def create_dummy_file(file_path: Path):
    with open(file_path, "w") as f:
        f.write("# This is a dummy file for the FixTransaction demo.\n")
        f.write("print('Hello, World!')\n")

if __name__ == "__main__":
    dummy_file = Path("dummy_script.py")
    
    # 1. example of successful fix
    print("--- example 1: successful fix ---")
    create_dummy_file(dummy_file)
    original_content = dummy_file.read_text()
    fix_with_success(dummy_file)
    final_content = dummy_file.read_text()
    
    # check that content changed 
    print("\noriginal content:")
    print(original_content)
    print("final content:")
    print(final_content)
    
    # 2. example of failed fix (with rollback)
    print("\n--- example 2: failed fix with rollback ---")
    create_dummy_file(dummy_file) # create a new empty file
    original_content_fail = dummy_file.read_text()
    fix_with_failure(dummy_file)
    final_content_fail = dummy_file.read_text()
    
    # check that content returned to original state
    print("\noriginal content before failure:")
    print(original_content_fail)
    print("final content after failure (should be the same):")
    print(final_content_fail)
    
    # clean up
    os.remove(dummy_file)