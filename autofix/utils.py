# utils.py
import re
from typing import Optional
from .constants import ValidationPatterns
from .import_suggestions import MODULE_TO_PACKAGE

class ModuleValidation:
    @classmethod
    def is_likely_test_module(cls, module_name: str) -> bool:
        if not module_name:
            return False
            
        module_lower = module_name.lower()
        
        # Check exact regex patterns first (more precise)
        for pattern in ValidationPatterns.TEST_MODULE_PATTERNS:
            if re.match(pattern, module_lower):
                return True
        
        # Fallback to substring check
        return any(indicator in module_lower 
                  for indicator in ValidationPatterns.TEST_MODULE_INDICATORS)
    
    @classmethod
    def resolve_package_name(cls, module_name: str) -> Optional[str]:
        """Resolve module name to actual package name"""
        return MODULE_TO_PACKAGE.get(module_name)
