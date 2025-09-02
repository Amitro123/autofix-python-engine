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
        
        logger.info("Performance Statistics:")
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


class PerformanceTracker:
    """Track performance metrics for different operations"""
    
    def __init__(self):
        self.operation_times = defaultdict(list)
        self.current_operations = {}
    
    def start_operation(self, operation_id: str, operation_name: str):
        """Start timing an operation"""
        self.current_operations[operation_id] = {
            'name': operation_name,
            'start_time': time.perf_counter()
        }
    
    def end_operation(self, operation_id: str) -> float:
        """End timing an operation and return duration"""
        if operation_id not in self.current_operations:
            return 0.0
        
        op_info = self.current_operations.pop(operation_id)
        duration = time.perf_counter() - op_info['start_time']
        self.operation_times[op_info['name']].append(duration)
        return duration
    
    def get_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for a specific operation"""
        times = self.operation_times.get(operation_name, [])
        if not times:
            return {}
        
        return {
            'count': len(times),
            'total': sum(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    def report_performance(self, logger: logging.Logger):
        """Report performance statistics"""
        if not self.operation_times:
            logger.info("No performance data recorded")
            return
        
        logger.info("Performance Report:")
        for operation, times in self.operation_times.items():
            stats = self.get_stats(operation)
            logger.info(f"  {operation}: {stats['count']} ops, "
                       f"avg={stats['average']:.3f}s, "
                       f"total={stats['total']:.3f}s")


class AutoFixMetrics:
    """Comprehensive metrics tracking for AutoFix operations"""
    
    def __init__(self):
        self.fix_stats = FixStats()
        self.performance = PerformanceTracker()
        self.session_start = datetime.now()
    
    def record_fix_attempt(self, outcome: str, operation: str = "fix", 
                          duration: float = 0.0, error_type: Optional[str] = None):
        """Record a fix attempt with outcome and timing"""
        self.fix_stats.record(outcome, operation, duration, error_type)
    
    def start_timing(self, operation_id: str, operation_name: str):
        """Start timing an operation"""
        self.performance.start_operation(operation_id, operation_name)
    
    def end_timing(self, operation_id: str) -> float:
        """End timing an operation"""
        return self.performance.end_operation(operation_id)
    
    def generate_session_report(self, logger: logging.Logger):
        """Generate comprehensive session report"""
        session_duration = datetime.now() - self.session_start
        
        logger.info("=" * 50)
        logger.info("AutoFix Session Report")
        logger.info(f"Session Duration: {session_duration}")
        logger.info("=" * 50)
        
        self.fix_stats.detailed_report(logger)
        
        error_summary = self.fix_stats.get_error_summary()
        if error_summary:
            logger.info("Error Types Encountered:")
            for error_type, count in error_summary.items():
                logger.info(f"  {error_type}: {count}")
        
        self.performance.report_performance(logger)
        logger.info("=" * 50)


# Global metrics instance for easy access
_global_metrics = AutoFixMetrics()


def get_metrics() -> AutoFixMetrics:
    """Get the global metrics instance"""
    return _global_metrics


def record_success(operation: str = "fix", duration: float = 0.0):
    """Quick function to record a successful operation"""
    _global_metrics.record_fix_attempt("success", operation, duration)


def record_failure(operation: str = "fix", duration: float = 0.0, error_type: str = None):
    """Quick function to record a failed operation"""
    _global_metrics.record_fix_attempt("failure", operation, duration, error_type)


def record_partial(operation: str = "fix", duration: float = 0.0):
    """Quick function to record a partially successful operation"""
    _global_metrics.record_fix_attempt("partial", operation, duration)
