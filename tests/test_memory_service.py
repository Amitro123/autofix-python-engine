"""
Comprehensive tests for MemoryService
Tests basic functionality, quality filtering, and Firebase integration
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from api.services.memory_service import MemoryService

class TestMemoryServiceBasic:
    """Test basic memory service functionality"""
    
    @pytest.fixture
    def temp_memory_service(self):
        """Create temporary memory service for testing"""
        temp_dir = tempfile.mkdtemp()
        service = MemoryService(persist_directory=temp_dir)
        yield service
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_initialization(self, temp_memory_service):
        """Test service initialization"""
        assert temp_memory_service is not None
        assert temp_memory_service.collection is not None
        assert temp_memory_service.collection.count() == 0
    
    def test_store_fix(self, temp_memory_service):
        """Test storing a fix"""
        fix_id = temp_memory_service.store_fix(
            original_code="x = [1, 2, 3]\nprint(x[5])",
            error_type="IndexError",
            fixed_code="x = [1, 2, 3]\nif len(x) > 5:\n    print(x[5])",
            method="test"
        )
        
        assert fix_id is not None
        assert temp_memory_service.collection.count() == 1
    
    def test_store_multiple_fixes(self, temp_memory_service):
        """Test storing multiple fixes"""
        # Store 3 different fixes
        fix1 = temp_memory_service.store_fix(
            "x = [1]\nprint(x[5])",
            "IndexError",
            "x = [1]\nprint(x[0])",
            "test"
        )
        
        fix2 = temp_memory_service.store_fix(
            "x = 'hello'\ny = x + 5",
            "TypeError",
            "x = 'hello'\ny = x + '5'",
            "test"
        )
        
        fix3 = temp_memory_service.store_fix(
            "x = {}\nprint(x['key'])",
            "KeyError",
            "x = {}\nprint(x.get('key', 'default'))",
            "test"
        )
        
        assert all([fix1, fix2, fix3])
        assert temp_memory_service.collection.count() == 3
    
    def test_search_similar_basic(self, temp_memory_service):
        """Test basic similarity search"""
        # Store a fix
        temp_memory_service.store_fix(
            original_code="x = [1, 2, 3]\nprint(x[10])",
            error_type="IndexError",
            fixed_code="x = [1, 2, 3]\nprint(x[2])",
            method="test"
        )
        
        # Search for similar
        similar_code = "y = [5, 6, 7]\nprint(y[100])"
        results = temp_memory_service.search_similar(
            similar_code,
            "IndexError",
            k=1
        )
        
        assert len(results) > 0
        assert results[0]['error_type'] == "IndexError"
        assert 'fixed_code' in results[0]
    
    def test_search_no_results(self, temp_memory_service):
        """Test search with no matching results"""
        # Store IndexError fix
        temp_memory_service.store_fix(
            "x = [1]\nprint(x[5])",
            "IndexError",
            "x = [1]\nprint(x[0])",
            "test"
        )
        
        # Search for different error type
        results = temp_memory_service.search_similar(
            "y = 'test'\nz = y + 5",
            "TypeError",
            k=3
        )
        
        # Should return empty since no TypeError examples
        assert len(results) == 0
    
    def test_search_multiple_results(self, temp_memory_service):
        """Test search returning multiple results"""
        # Store 3 similar IndexError fixes
        for i in range(3):
            temp_memory_service.store_fix(
                f"x = [1, 2]\nprint(x[{i+10}])",
                "IndexError",
                f"x = [1, 2]\nprint(x[{i}])",
                "test"
            )
        
        # Search
        results = temp_memory_service.search_similar(
            "arr = [1, 2, 3]\nprint(arr[999])",
            "IndexError",
            k=3
        )
        
        assert len(results) == 3
        assert all(r['error_type'] == 'IndexError' for r in results)
    
    def test_get_stats(self, temp_memory_service):
        """Test getting statistics"""
        # Store some fixes
        temp_memory_service.store_fix("code1", "Error1", "fixed1", "test")
        temp_memory_service.store_fix("code2", "Error2", "fixed2", "test")
        
        stats = temp_memory_service.get_stats()
        
        assert stats['total_examples'] == 2
        assert stats['collection_name'] == "autofix_memory"
    
    def test_store_with_metadata(self, temp_memory_service):
        """Test storing fix with custom metadata"""
        fix_id = temp_memory_service.store_fix(
            "code",
            "TestError",
            "fixed",
            "custom",
            metadata={'custom_field': 'custom_value', 'priority': 'high'}
        )
        
        assert fix_id is not None
        
        # Retrieve and check metadata
        result = temp_memory_service.collection.get(ids=[fix_id])
        metadata = result['metadatas'][0]
        
        assert metadata['custom_field'] == 'custom_value'
        assert metadata['priority'] == 'high'


class TestMemoryServiceValidation:
    """Test validation and quality filtering"""
    
    @pytest.fixture
    def temp_memory_service(self):
        """Create temporary memory service"""
        temp_dir = tempfile.mkdtemp()
        service = MemoryService(persist_directory=temp_dir)
        yield service
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_store_fix_with_validation_success(self, temp_memory_service):
        """Test storing validated successful fix"""
        validation_result = {
            'success': True,
            'execution_time': 0.5,
            'tests_passed': True
        }
        
        fix_id = temp_memory_service.store_fix_with_validation(
            "broken_code",
            "TestError",
            "fixed_code",
            validation_result
        )
        
        assert fix_id is not None
        assert temp_memory_service.collection.count() == 1
    
    def test_store_fix_with_validation_failure(self, temp_memory_service):
        """Test that failed fixes are not stored"""
        validation_result = {
            'success': False,
            'error': 'Fix did not work'
        }
        
        fix_id = temp_memory_service.store_fix_with_validation(
            "broken_code",
            "TestError",
            "bad_fix",
            validation_result
        )
        
        assert fix_id is None
        assert temp_memory_service.collection.count() == 0
    
    def test_duplicate_fix_handling(self, temp_memory_service):
        """Test storing duplicate fixes"""
        code = "x = []\nprint(x[0])"
        error = "IndexError"
        fixed = "x = []\nif x:\n    print(x[0])"
        
        # Store same fix twice
        fix_id1 = temp_memory_service.store_fix(code, error, fixed, "test")
        fix_id2 = temp_memory_service.store_fix(code, error, fixed, "test")
        
        # Should have same ID (update, not duplicate)
        assert fix_id1 == fix_id2


class TestMemoryServiceWithFirebase:
    """Test Firebase integration for quality tracking"""
    
    @pytest.fixture
    def mock_firebase(self):
        """Create mock Firebase client"""
        mock = Mock()
        mock.initialize_example_metrics = Mock()
        mock.get_example_metrics = Mock()
        mock.get_avg_success_rate = Mock(return_value=0.85)
        mock.get_total_retrievals = Mock(return_value=150)
        return mock
    
    @pytest.fixture
    def temp_memory_service_with_firebase(self, mock_firebase):
        """Create memory service with mock Firebase"""
        temp_dir = tempfile.mkdtemp()
        service = MemoryService(
            persist_directory=temp_dir,
            firebase_client=mock_firebase
        )
        yield service
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_store_initializes_firebase_metrics(
        self, 
        temp_memory_service_with_firebase,
        mock_firebase
    ):
        """Test that storing a fix initializes Firebase metrics"""
        fix_id = temp_memory_service_with_firebase.store_fix(
            "code",
            "TestError",
            "fixed",
            "test"
        )
        
        # Verify Firebase was called
        mock_firebase.initialize_example_metrics.assert_called_once()
        call_args = mock_firebase.initialize_example_metrics.call_args
        assert call_args[0][0] == fix_id
    
    def test_search_with_quality_filtering(
        self,
        temp_memory_service_with_firebase,
        mock_firebase
    ):
        """Test quality-filtered search"""
        # Store 3 fixes
        fix_ids = []
        for i in range(3):
            fix_id = temp_memory_service_with_firebase.store_fix(
                f"code{i}",
                "TestError",
                f"fixed{i}",
                "test"
            )
            fix_ids.append(fix_id)
        
        # Mock different quality metrics
        def get_metrics(fix_id):
            index = fix_ids.index(fix_id)
            return {
                'times_retrieved': 10,
                'times_successful': [9, 5, 8][index],  # 90%, 50%, 80%
                'times_failed': [1, 5, 2][index]
            }
        
        mock_firebase.get_example_metrics = get_metrics
        
        # Search with quality filter (min 70%)
        results = temp_memory_service_with_firebase.search_similar_with_quality(
            "similar_code",
            "TestError",
            k=3,
            min_success_rate=0.7
        )
        
        # Should filter out the 50% one
        assert len(results) <= 2
        assert all(r.get('success_rate', 0) >= 0.7 for r in results)
    
    def test_stats_with_firebase(
        self,
        temp_memory_service_with_firebase,
        mock_firebase
    ):
        """Test statistics with Firebase integration"""
        # Store some fixes
        temp_memory_service_with_firebase.store_fix("c1", "E1", "f1", "test")
        temp_memory_service_with_firebase.store_fix("c2", "E2", "f2", "test")
        
        stats = temp_memory_service_with_firebase.get_stats()
        
        assert stats['total_examples'] == 2
        assert stats['avg_success_rate'] == 0.85
        assert stats['total_retrievals'] == 150
    
    def test_cleanup_low_quality_examples(
        self,
        temp_memory_service_with_firebase,
        mock_firebase
    ):
        """Test removing low-quality examples"""
        # Store 3 fixes
        fix_ids = []
        for i in range(3):
            fix_id = temp_memory_service_with_firebase.store_fix(
                f"code{i}",
                "TestError",
                f"fixed{i}",
                "test"
            )
            fix_ids.append(fix_id)
        
        # Mock metrics: one good (90%), two bad (30%, 40%)
        def get_metrics(fix_id):
            index = fix_ids.index(fix_id)
            if index == 0:
                return {'times_retrieved': 10, 'times_successful': 9}
            elif index == 1:
                return {'times_retrieved': 10, 'times_successful': 3} # 30% ← Below 50%
            else:
                return {'times_retrieved': 10, 'times_successful': 4} # 40% ← Below 50%
        
        mock_firebase.get_example_metrics = get_metrics
        mock_firebase.delete_example_metrics = Mock()
        
        # Cleanup (min success rate 50%)
        removed = temp_memory_service_with_firebase.cleanup_low_quality_examples(
            min_success_rate=0.5,
            min_usage=10
        )
        
        # Should remove 2 low-quality examples
        assert removed == 2
        assert temp_memory_service_with_firebase.collection.count() == 1


class TestMemoryServiceEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def temp_memory_service(self):
        """Create temporary memory service"""
        temp_dir = tempfile.mkdtemp()
        service = MemoryService(persist_directory=temp_dir)
        yield service
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_empty_code(self, temp_memory_service):
        """Test handling empty code"""
        fix_id = temp_memory_service.store_fix(
            "",
            "TestError",
            "fixed",
            "test"
        )
        
        # Should still work (generate ID from empty string)
        assert fix_id is not None
    
    def test_very_long_code(self, temp_memory_service):
        """Test handling very long code"""
        long_code = "x = 1\n" * 10000  # Very long code
        
        fix_id = temp_memory_service.store_fix(
            long_code,
            "TestError",
            "fixed",
            "test"
        )
        
        assert fix_id is not None
    
    def test_special_characters_in_code(self, temp_memory_service):
        """Test handling special characters"""
        code_with_special = "x = '🚀'\nprint(x + '✨')\n# émojis"
        
        fix_id = temp_memory_service.store_fix(
            code_with_special,
            "TestError",
            "fixed",
            "test"
        )
        
        assert fix_id is not None
    
    def test_search_with_k_larger_than_available(self, temp_memory_service):
        """Test search when k > available examples"""
        # Store only 1 fix
        temp_memory_service.store_fix("code", "TestError", "fixed", "test")
        
        # Search for 10
        results = temp_memory_service.search_similar(
            "code",
            "TestError",
            k=10
        )
        
        # Should return only 1
        assert len(results) == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
