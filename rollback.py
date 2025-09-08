# -*- coding: utf-8 -*-
import shutil
import os
import tempfile
import sys
import platform
from pathlib import Path
from logging_utils import get_logger

logger = get_logger("rollback")

class FixTransaction:
    """
    context manager for file fix transactions
    creates a backup of the file before fixing it
    and restores it if the fix fails

    """
    def __init__(self, file_path: Path, retain_backup: bool = False):
        self.file_path = file_path
        self.backup_path = None
        self.retain_backup = retain_backup 
        
        
    def __enter__(self):
        """
      with block entry
        """
        os_name = platform.system()

        if os_name == "Windows":
   
            pass
        elif os_name == "Linux":

            pass
        elif os_name == "Darwin":  # macOS
            pass

        try:
            #make sure the file exists
            if not self.file_path.is_file():
                raise FileNotFoundError(f"Original file not found: {self.file_path}")

            #create a backup
            self.backup_path = Path(tempfile.mktemp(suffix=".bak"))
            shutil.copy2(self.file_path, self.backup_path)
            
            logger.info(f"created backup: {self.file_path} -> {self.backup_path}")
            return self
        except Exception as e:
            logger.error(f"error creating backup: {e}")
            # if backup fails, there is no point to continue
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit with block - handle rollback or cleanup"""
        if exc_type:
            # Error occurred - rollback
            logger.warning("Error during fix. Performing rollback...")
            try:
                if self.backup_path and self.backup_path.is_file():
                    shutil.copy2(self.backup_path, self.file_path)
                    logger.info(f"Restored file from backup: {self.file_path}")
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
            
            # Always clean up backup after rollback
            self._cleanup_backup()
            return False  # Re-raise the original exception
        else:
            # Success - clean up backup unless retained
            if not self.retain_backup:
                self._cleanup_backup()
            else:
                logger.info(f"Backup retained: {self.backup_path}")

    def _cleanup_backup(self):
        """Clean up backup file"""
        if self.backup_path and self.backup_path.is_file():
            try:
                os.remove(self.backup_path)
                logger.info(f"Deleted backup: {self.backup_path}")
            except Exception as e:
                logger.error(f"Failed to delete backup: {e}")



# --- examples ---

def fix_with_success(file_path: Path):
    """example of successful fix"""
    with FixTransaction(file_path) as transaction:
        logger.info(f"inside transaction. fixing {file_path}...")
        # fix - add line to file
        with open(file_path, 'a') as f:
            f.write("\n# This line was added successfully by the fixer.")
        logger.info("fix succeeded!")

def fix_with_failure(file_path: Path):
    """example of failed fix"""
    try:
        with FixTransaction(file_path) as transaction:
            logger.info(f"inside transaction. fixing {file_path}...")
            # fix - raise error
            raise ValueError("An error occurred during the fix process!")
    except ValueError as e:
        logger.error(f"error: {e}")
        logger.info("rollback should be performed automatically.")

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