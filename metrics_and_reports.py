#!/usr/bin/env python3
"""
Metrics and statistics tracking for AutoFix operations.

This module provides classes and utilities for tracking fix outcomes,
performance metrics, and generating reports.
"""

import logging
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

from tests import test_pip_conflicts

# Setup logger for this module
logger = logging.getLogger(__name__)

@contextmanager
def log_duration(logger: logging.Logger, operation: str):
    """
    Context manager to log the duration of an operation.
    
    Args:
        logger: Logger instance to use for output
        operation: Description of the operation being timed
        
    Usage:
        with log_duration(logger, "Fixing imports"):
            run_fix()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        logger.info(f"{operation} completed in {duration:.3f}s")


@dataclass
class FixAttempt:
    """Record of a single fix attempt"""
    timestamp: datetime
    operation: str
    outcome: str  # "success", "failure", "partial"
    duration: float
    error_type: Optional[str] = None
    details: Optional[str] = None


class FixStats:
    """Track fix outcomes and generate statistics"""
    
    def __init__(self):
        self.counter = Counter()
        self.attempts: List[FixAttempt] = []
        self.durations = defaultdict(list)
    
    def record(self, outcome: str, operation: str = "fix", duration: float = 0.0, 
                 error_type: Optional[str] = None, details: Optional[str] = None):
        """Record a fix attempt outcome"""
        self.counter[outcome] += 1
        
        attempt = FixAttempt(
            timestamp=datetime.now(),
            operation=operation,
            outcome=outcome,
            duration=duration,
            error_type=error_type,
            details=details
        )
        self.attempts.append(attempt)
        
        if duration > 0:
            self.durations[operation].append(duration)
    
    def report(self, logger: logging.Logger):
        """Generate and log basic statistics report"""
        total = sum(self.counter.values())
        if total == 0:
            logger.info("No fix attempts recorded")
            return
        
        success = self.counter.get("success", 0)
        failure = self.counter.get("failure", 0)
        partial = self.counter.get("partial", 0)
        
        success_rate = (success / total) * 100 if total > 0 else 0
        
        logger.info(f"Fix Statistics: {total} total attempts")
        logger.info(f"  Success: {success} ({success_rate:.1f}%)")
        logger.info(f"  Failure: {failure}")
        if partial > 0:
            logger.info(f"  Partial: {partial}")
    
    def detailed_report(self, logger: logging.Logger):
        """Generate detailed statistics report"""
        self.report(logger)  # Basic report first
        
        if not self.durations:
            return
        
        logger.info("\nPerformance Statistics:")
        for operation, times in self.durations.items():
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                logger.info(f"  {operation}: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error types encountered"""
        error_counts = Counter()
        for attempt in self.attempts:
            if attempt.outcome == "failure" and attempt.error_type:
                error_counts[attempt.error_type] += 1
        return dict(error_counts)
    
    def reset(self):
        """Reset all statistics"""
        self.counter.clear()
        self.attempts.clear()
        self.durations.clear()


