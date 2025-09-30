from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional

class BaseHandler(ABC):
    """Abstract base handler for all error types"""
    
    @abstractmethod
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        """Analyze error and return (error_type, suggestion, details)"""
        pass
    
    @abstractmethod
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        """Apply the fix and return success status"""
        pass
