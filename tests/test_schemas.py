import pytest
from pydantic import ValidationError
from api.models.schemas import FixRequest, FixResponse, Change

class TestSchemas:
    """Test Pydantic schemas for API validation"""

    def test_fix_request_schema_valid(self):
        """Test valid FixRequest creation"""
        request = FixRequest(code="print('hello')", auto_install=False)
        assert request.code == "print('hello')"
        assert request.auto_install == False

    def test_fix_request_schema_default_auto_install(self):
        """Test FixRequest with default auto_install"""
        request = FixRequest(code="print('test')")
        assert request.code == "print('test')"
        assert request.auto_install == False

    def test_fix_request_validation_empty_code(self):
        """Test FixRequest rejects empty code"""
        with pytest.raises(ValidationError):
            FixRequest(code="", auto_install=False)

    def test_fix_request_validation_wrong_type(self):
        """Test FixRequest type validation"""
        with pytest.raises(ValidationError):
            FixRequest(code="test", auto_install="not_bool")

    def test_fix_response_schema(self):
        """Test FixResponse creation"""
        changes = [Change(line=1, type="syntax", description="Fixed syntax")]
        response = FixResponse(
            success=True,
            original_code="if True\nprint('hello')",
            fixed_code="if True:\n    print('hello')",
            error_type="SyntaxError",
            method="autofix",
            changes=changes,
            execution_time=0.5
        )
        assert response.success == True
        assert response.method == "autofix"
        assert len(response.changes) == 1

    def test_fix_response_schema_minimal(self):
        """Test FixResponse with minimal required fields"""
        response = FixResponse(
            success=False,
            original_code="broken code",
            execution_time=1.0
        )
        assert response.success == False
        assert response.fixed_code is None
        assert response.error_type is None
        assert response.changes == []

    def test_change_schema(self):
        """Test Change model"""
        change = Change(line=5, type="indentation", description="Fixed indentation")
        assert change.line == 5
        assert change.type == "indentation"
        assert change.description == "Fixed indentation"

    def test_batch_request_schema(self):
        """Test batch request as list of FixRequest"""
        batch = [
            FixRequest(code="print('first')"),
            FixRequest(code="print('second')", auto_install=True)
        ]
        assert len(batch) == 2
        assert batch[0].code == "print('first')"
        assert batch[1].auto_install == True
