# -*- coding: utf-8 -*-
import shutil
import os
import tempfile
from pathlib import Path

try:
    from .logging_utils import get_logger
except ImportError:
    from autofix.helpers.logging_utils import get_logger

logger = get_logger("rollback")

class FixTransaction:
    """
    Context manager for file fix transactions
    Creates a backup of the file before fixing it,
    and restores it if the fix fails.
    """
    def __init__(self, file_path: Path, retain_backup: bool = False):
        self.file_path = file_path
        self.backup_path = None
        self.retain_backup = retain_backup 

    def __enter__(self):
        try:
            if not self.file_path.is_file():
                raise FileNotFoundError(f"Original file not found: {self.file_path}")

            self.backup_path = Path(tempfile.mktemp(suffix=".bak"))
            shutil.copy2(self.file_path, self.backup_path)

            logger.info(f"Created backup: {self.file_path} -> {self.backup_path}")
            return self
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.warning("Error during fix. Performing rollback...")
            try:
                if self.backup_path and self.backup_path.is_file():
                    shutil.copy2(self.backup_path, self.file_path)
                    logger.info(f"Restored file from backup: {self.file_path}")
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
            self._cleanup_backup()
            return False
        else:
            if not self.retain_backup:
                self._cleanup_backup()
            else:
                logger.info(f"Backup retained: {self.backup_path}")

    def _cleanup_backup(self):
        if self.backup_path and self.backup_path.is_file():
            try:
                os.remove(self.backup_path)
                logger.info(f"Deleted backup: {self.backup_path}")
            except Exception as e:
                logger.error(f"Failed to delete backup: {e}")
