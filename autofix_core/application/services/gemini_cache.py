"""
Gemini Response Cache Service
Based on Jules' recommendations for AutoFix v2.2.1

Caches successful Gemini fixes to:
- Reduce API costs
- Improve response time
- Better user experience
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
from autofix_core.shared.helpers.logging_utils import get_logger


logger = get_logger(__name__)



class GeminiCacheConfig:
    """Cache configuration"""
    
    # Cache directory
    CACHE_DIR = Path(".gemini_cache")
    
    # Cache settings
    ENABLE_CACHE = True
    CACHE_TTL_DAYS = 30  # 30 days TTL (reasonable default)
    MAX_CACHE_SIZE_MB = 100  # 100 MB max
    
    # Metrics
    ENABLE_METRICS = True

    # Versioning
    MODEL_NAME = "default-model"


class GeminiCache:
    """
    File-based cache for Gemini API responses
    
    Jules' recommendations:
    - Cache key: hash(code + error_message)
    - Storage: File-based (simple and effective)
    - Benefits: Lower costs, faster response
    """
    
    def __init__(self, config: Optional[GeminiCacheConfig] = None):
        self.config = config or GeminiCacheConfig()
        
        # Always initialize
        self.hits = 0
        self.misses = 0
        self.cache_dir = self.config.CACHE_DIR
        
        if not self.config.ENABLE_CACHE:
            logger.info("Cache disabled")
            return
        
        # Create dir only if enabled
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"Cache initialized at {self.cache_dir}")
        self._check_model_version()


    
    def _check_model_version(self):
        """Check for model version mismatch and clear cache if needed"""
        version_file = self.cache_dir / ".model_version"

        try:
            if version_file.exists():
                stored_version = version_file.read_text().strip()
                if stored_version != self.config.MODEL_NAME:
                    logger.warning(
                        f"Model mismatch: cache has '{stored_version}',"
                        f" current is '{self.config.MODEL_NAME}'. Clearing cache."
                    )
                    self.clear()
                    version_file.write_text(self.config.MODEL_NAME)
            else:
                logger.info("No model version file, creating...")
                version_file.write_text(self.config.MODEL_NAME)
        except Exception as e:
            logger.error(f"Version check error: {e}")

    def _get_cache_key(self, code: str, error_message: str) -> str:
        """
        Generate cache key from code + error
        
        Jules: hash(code + error_message) is elegant!
        """
        content = f"{code}|||{error_message}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key"""
        return self.cache_dir / f"{key}.json"
    
    def get(self, code: str, error_message: str) -> Optional[Dict]:
        """
        Get cached fix if exists and not expired
        
        Returns:
            Cached result dict or None if cache miss
        """
        if not self.config.ENABLE_CACHE:
            return None
        
        try:
            key = self._get_cache_key(code, error_message)
            cache_file = self._get_cache_file(key)
            
            if not cache_file.exists():
                self.misses += 1
                logger.debug(f"Cache miss: {key[:8]}...")
                return None
            
            # Read cached data
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check expiry (TTL)
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            age = datetime.now() - cached_time
            
            if age > timedelta(days=self.config.CACHE_TTL_DAYS):
                logger.info(f"Cache expired: {key[:8]}... (age: {age.days} days)")
                cache_file.unlink()  # Delete expired cache
                self.misses += 1
                return None
            
            # Cache hit!
            self.hits += 1
            logger.success(f"Cache HIT: {key[:8]}... (age: {age.days} days)")
            
            return cached_data['result']
            
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            self.misses += 1
            return None
    
    def set(self, code: str, error_message: str, result: Dict):
        """
        Save successful fix to cache
        
        Args:
            code: Original code
            error_message: Error message
            result: Gemini response dict
        """
        if not self.config.ENABLE_CACHE:
            return
        
        try:
            key = self._get_cache_key(code, error_message)
            cache_file = self._get_cache_file(key)
            
            # Prepare cache entry
            cache_entry = {
                'result': result,
                'cached_at': datetime.now().isoformat(),
                'code_hash': key[:16],  # For debugging
                'code_length': len(code),
                'error_type': result.get('error_type', 'unknown')
            }
            
            # Write to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2)
            
            logger.success(f"Cache SET: {key[:8]}...")
            
            # Check cache size
            self._check_cache_size()
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def _check_cache_size(self):
        """Check and enforce cache size limit"""
        try:
            total_size = sum(
                f.stat().st_size 
                for f in self.cache_dir.glob("*.json")
            )
            
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > self.config.MAX_CACHE_SIZE_MB:
                logger.warning(f"Cache size ({size_mb:.1f} MB) exceeds limit ({self.config.MAX_CACHE_SIZE_MB} MB)")
                self._cleanup_old_cache()
        
        except Exception as e:
            logger.error(f"Cache size check error: {e}")
    
    def _cleanup_old_cache(self):
        """Remove oldest cache entries"""
        try:
            cache_files = sorted(
                self.cache_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime
            )
            
            # Remove oldest 25% of cache
            remove_count = len(cache_files) // 4
            
            for cache_file in cache_files[:remove_count]:
                cache_file.unlink()
                logger.debug(f"Removed old cache: {cache_file.name}")
            
            logger.success(f"Cleaned up {remove_count} old cache entries")
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def clear(self):
        """Clear all cache"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            logger.success("Cache cleared")
            self.hits = 0
            self.misses = 0
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        # Early return for disabled cache
        if not self.config.ENABLE_CACHE:
            return {
                'enabled': False,
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total,
                'hit_rate': f"{hit_rate:.1f}%",
                'cache_entries': 0,
                'cache_size_mb': '0.00',
                'ttl_days': self.config.CACHE_TTL_DAYS
            }
        
        # Rest of the method...
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'enabled': True,
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_entries': len(cache_files),
            'cache_size_mb': f"{total_size / (1024 * 1024):.2f}",
            'ttl_days': self.config.CACHE_TTL_DAYS
        }


# Example usage
if __name__ == "__main__":
    cache = GeminiCache()
    
    # Example 1: Cache miss
    result = cache.get("def test(): print('hi')", "SyntaxError")
    print(f"Result: {result}")  # None
    
    # Example 2: Cache set
    cache.set(
        "def test(): print('hi')",
        "SyntaxError",
        {'fixed_code': "def test():\n    print('hi')", 'confidence': 0.9}
    )
    
    # Example 3: Cache hit
    result = cache.get("def test(): print('hi')", "SyntaxError")
    print(f"Result: {result}")  # {'fixed_code': ..., 'confidence': 0.9}
    
    # Example 4: Stats
    print(f"Stats: {cache.get_stats()}")

