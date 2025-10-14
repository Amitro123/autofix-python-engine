"""
Memory Service for RAG with Quality Tracking
Stores and retrieves code fixes using ChromaDB + Firebase metrics
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
from pathlib import Path
from datetime import datetime

class MemoryService: #add logs
    """Self-improving memory service with quality tracking"""
    
    def __init__(
        self, 
        persist_directory: str = "./chroma_db",
        firebase_client=None
    ):
        """
        Initialize memory service with ChromaDB and Firebase
        
        Args:
            persist_directory: Directory for ChromaDB persistence
            firebase_client: Firebase client for quality tracking
        """
        # Create directory if needed
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="autofix_memory",
            metadata={"description": "Self-improving code fix memory with quality tracking"}
        )
        
        # Firebase for quality tracking
        self.firebase = firebase_client
    
    def _generate_id(self, code: str, error_type: str) -> str:
        """Generate unique ID for code-error pair"""
        content = f"{code}:{error_type}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def store_fix(
        self,
        original_code: str,
        error_type: str,
        fixed_code: str,
        method: str = "gemini",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store a code fix in memory
        
        Args:
            original_code: Broken code
            error_type: Type of error
            fixed_code: Fixed code
            method: Method used (gemini, rules, stackoverflow, etc.)
            metadata: Additional metadata
            
        Returns:
            Fix ID
        """
        fix_id = self._generate_id(original_code, error_type)
        
        # Prepare metadata
        fix_metadata = {
            "error_type": error_type,
            "method": method,
            "fixed_code": fixed_code,
            "stored_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        try:
            # Store in ChromaDB
            self.collection.add(
                documents=[original_code],
                metadatas=[fix_metadata],
                ids=[fix_id]
            )
            
            # Initialize quality tracking in Firebase
            if self.firebase:
                self.firebase.initialize_example_metrics(fix_id, {
                    'times_retrieved': 0,
                    'times_successful': 0,
                    'times_failed': 0,
                    'success_rate': 0.0,
                    'first_stored': datetime.now()
                })
            
            return fix_id
            
        except Exception as e:
            print(f"Error storing fix: {e}")
            return None
    
    def store_fix_with_validation(
        self,
        original_code: str,
        error_type: str,
        fixed_code: str,
        validation_result: Dict,
        method: str = "validated"
    ) -> Optional[str]:
        """
        Store fix only if validation passed
        
        Args:
            original_code: Broken code
            error_type: Error type
            fixed_code: Fixed code
            validation_result: Validation results from execution
            method: Method used
            
        Returns:
            Fix ID if stored, None if validation failed
        """
        # Only store if successful
        if not validation_result.get('success'):
            return None
        
        metadata = {
            'validated': True,
            'validation_time': validation_result.get('execution_time'),
            'tests_passed': validation_result.get('tests_passed', True)
        }
        
        return self.store_fix(
            original_code=original_code,
            error_type=error_type,
            fixed_code=fixed_code,
            method=method,
            metadata=metadata
        )
    
    def search_similar(
        self,
        code: str,
        error_type: str,
        k: int = 3
    ) -> List[Dict]:
        """
        Search for similar fixes (basic version)
        
        Args:
            code: Code to find similar fixes for
            error_type: Error type filter
            k: Number of results
            
        Returns:
            List of similar fixes
        """
        try:
            results = self.collection.query(
                query_texts=[code],
                n_results=k,
                where={"error_type": error_type}
            )
            
            if not results or not results['documents'][0]:
                return []
            
            similar_fixes = []
            for i, doc in enumerate(results['documents'][0]):
                fix = {
                    'id': results['ids'][0][i],
                    'original_code': doc,
                    'fixed_code': results['metadatas'][0][i]['fixed_code'],
                    'error_type': results['metadatas'][0][i]['error_type'],
                    'method': results['metadatas'][0][i]['method'],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                similar_fixes.append(fix)
            
            return similar_fixes
            
        except Exception as e:
            print(f"Error searching similar fixes: {e}")
            return []
    
    def search_similar_with_quality(
        self,
        code: str,
        error_type: str,
        k: int = 3,
        min_success_rate: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar fixes filtered by quality
        
        Args:
            code: Code to search
            error_type: Error type
            k: Number of results
            min_success_rate: Minimum success rate threshold
            
        Returns:
            Quality-filtered similar fixes
        """
        # Get more candidates than needed
        candidates = self.search_similar(code, error_type, k=k*3)
        
        if not self.firebase:
            return candidates[:k]
        
        # Enrich with quality metrics
        quality_results = []
        for candidate in candidates:
            metrics = self.firebase.get_example_metrics(candidate['id'])
            
            if not metrics or metrics.get('times_retrieved', 0) < 3:
                # New examples get benefit of doubt
                candidate['success_rate'] = 0.8  # Default high
                quality_results.append(candidate)
            else:
                # Calculate success rate
                times_retrieved = metrics['times_retrieved']
                times_successful = metrics['times_successful']
                success_rate = times_successful / times_retrieved if times_retrieved > 0 else 0.0
                
                if success_rate >= min_success_rate:
                    candidate['success_rate'] = success_rate
                    candidate['times_used'] = times_retrieved
                    quality_results.append(candidate)
        
        # Sort by success rate and return top k
        quality_results.sort(key=lambda x: x.get('success_rate', 0), reverse=True)
        return quality_results[:k]
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        stats = {
            'total_examples': self.collection.count(),
            'collection_name': self.collection.name
        }
        
        if self.firebase:
            stats['avg_success_rate'] = self.firebase.get_avg_success_rate()
            stats['total_retrievals'] = self.firebase.get_total_retrievals()
        
        return stats
    
    def cleanup_low_quality_examples(
        self,
        min_success_rate: float = 0.5,
        min_usage: int = 10
    ) -> int:
        """
        Remove low-quality examples
        
        Args:
            min_success_rate: Minimum success rate to keep
            min_usage: Minimum usage count before evaluation
            
        Returns:
            Number of examples removed
        """
        if not self.firebase:
            return 0
        
        all_items = self.collection.get()
        removed_count = 0
        
        for i, fix_id in enumerate(all_items['ids']):
            metrics = self.firebase.get_example_metrics(fix_id)
            
            if not metrics:
                continue
            
            times_retrieved = metrics.get('times_retrieved', 0)
            
            if times_retrieved >= min_usage:
                times_successful = metrics.get('times_successful', 0)
                success_rate = times_successful / times_retrieved
                
                if success_rate < min_success_rate:
                    self.collection.delete(ids=[fix_id])
                    self.firebase.delete_example_metrics(fix_id)
                    removed_count += 1
                    print(f"Removed low-quality example {fix_id} (success rate: {success_rate:.2f})")
        
        return removed_count
