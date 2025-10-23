"""
Tests for Gemini Cache Service
v2.2.1 - Jules' recommendations
"""
import pytest
import tempfile
from pathlib import Path
from autofix_core.application.services.gemini_cache import GeminiCache, GeminiCacheConfig


def test_cache_miss():
    """Test cache miss scenario"""
    cache = GeminiCache()
    
    result = cache.get("def test(): pass", "SyntaxError")
    
    assert result is None
    assert cache.misses == 1
    assert cache.hits == 0


def test_cache_set_and_get():
    """Test caching and retrieval"""
    cache = GeminiCache()
    
    # Set cache
    code = "def test(): print('hi')"
    error = "SyntaxError: invalid syntax"
    fix_result = {
        'fixed_code': "def test():\n    print('hi')",
        'confidence': 0.9,
        'error_type': 'SyntaxError'
    }
    
    cache.set(code, error, fix_result)
    
    # Get from cache
    cached = cache.get(code, error)
    
    assert cached is not None
    assert cached['fixed_code'] == fix_result['fixed_code']
    assert cached['confidence'] == 0.9
    assert cache.hits == 1


def test_cache_different_code():
    """Test that different code doesn't hit cache"""
    cache = GeminiCache()
    
    # Set cache for code1
    code1 = "def test1(): pass"
    cache.set(code1, "Error1", {'fixed_code': 'fixed1'})
    
    # Try to get code2 (should miss)
    code2 = "def test2(): pass"
    result = cache.get(code2, "Error1")
    
    assert result is None
    assert cache.misses == 1


def test_cache_stats():
    """Test cache statistics"""
    cache = GeminiCache()
    
    # Miss
    cache.get("code1", "error1")
    
    # Set and hit
    cache.set("code2", "error2", {'fixed_code': 'fix'})
    cache.get("code2", "error2")
    
    stats = cache.get_stats()
    
    assert stats['hits'] == 1
    assert stats['misses'] == 1
    assert stats['total_requests'] == 2
    assert stats['enabled'] == True


def test_cache_clear():
    """Test cache clearing"""
    cache = GeminiCache()
    
    # Add some cache entries
    cache.set("code1", "error1", {'fixed_code': 'fix1'})
    cache.set("code2", "error2", {'fixed_code': 'fix2'})
    
    # Clear
    cache.clear()
    
    # Verify cleared
    stats = cache.get_stats()
    assert stats['cache_entries'] == 0
    assert stats['hits'] == 0
    assert stats['misses'] == 0


def test_cache_disabled():
    """Test cache when disabled"""
    config = GeminiCacheConfig()
    config.ENABLE_CACHE = False
    
    cache = GeminiCache(config)
    
    # Set shouldn't do anything
    cache.set("code", "error", {'fixed_code': 'fix'})
    
    # Get should return None
    result = cache.get("code", "error")
    
    assert result is None
    assert cache.get_stats()['enabled'] == False


if __name__ == "__main__":
    # Run tests manually
    print("🧪 Running cache tests...\n")
    
    test_cache_miss()
    print("✅ test_cache_miss")
    
    test_cache_set_and_get()
    print("✅ test_cache_set_and_get")
    
    test_cache_different_code()
    print("✅ test_cache_different_code")
    
    test_cache_stats()
    print("✅ test_cache_stats")
    
    test_cache_clear()
    print("✅ test_cache_clear")
    
    test_cache_disabled()
    print("✅ test_cache_disabled")
    
    print("\n🎉 All cache tests passed!")
