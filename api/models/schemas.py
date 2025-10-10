"""Pydantic schemas for validation"""
from pydantic import BaseModel, Field
from typing import Optional, List

class FixRequest(BaseModel): #maybe to add this logic to C:\Users\Dana\autofix-python-engine\autofix\integrations
    code: str = Field(..., min_length=1, description="Python code to fix")
    auto_install: bool = Field(default=False)
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "code": "if True\n    print('hello')",
                "auto_install": False
            }]
        }
    }

class Change(BaseModel):
    line: int
    type: str
    description: str

class FixResponse(BaseModel):
    success: bool
    original_code: str
    fixed_code: Optional[str] = None
    error_type: Optional[str] = None
    changes: List[Change] = []
    execution_time: float
