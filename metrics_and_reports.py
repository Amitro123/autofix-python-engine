#!/usr/bin/env python3
"""
Metrics and statistics tracking for AutoFix operations.

This module provides classes and utilities for tracking fix outcomes,
performance metrics, and generating reports using secure Firestore REST API.

Why REST API instead of Admin SDK:
- Admin SDK requires private service account keys (firebase-key.json)
- REST API uses public Web API keys, safe for client distribution
- No sensitive credentials exposed to end users
- Maintains full Firestore functionality for metrics collection
"""

import logging
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager

# Import secure Firestore client
from firestore_client import get_metrics_collector, save_metrics

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
    """Record of a single fix attempt with enhanced metrics"""
    timestamp: datetime
    operation: str
    outcome: str  # "success", "failure", "partial", "fix_succeeded", "fix_failed", "canceled"
    duration: float
    error_type: Optional[str] = None
    details: Optional[str] = None
    script_path: Optional[str] = None
    line_number: Optional[int] = None
    fix_applied: bool = False


class FixStats:
    """Track fix outcomes and generate statistics with Firestore integration"""
    
    def __init__(self, enable_firestore: bool = True):
        self.counter = Counter()
        self.attempts: List[FixAttempt] = []
        self.durations = defaultdict(list)
        self.enable_firestore = enable_firestore

        if enable_firestore:
            try:
                from .firestore_client import get_metrics_collector  # Import עדכני
                self.metrics_collector = get_metrics_collector()
            except ImportError:
                self.metrics_collector = None
                self.enable_firestore = False
        else:
            self.metrics_collector = None
    
    def record(self, outcome: str, operation: str = "fix", duration: float = 0.0, 
                 error_type: Optional[str] = None, details: Optional[str] = None,
                 script_path: Optional[str] = None, line_number: Optional[int] = None,
                 fix_applied: bool = False, **kwargs):
        """Record a fix attempt outcome with enhanced metrics and Firestore integration"""
        self.counter[outcome] += 1
        
        attempt = FixAttempt(
            timestamp=datetime.now(timezone.utc),
            operation=operation,
            outcome=outcome,
            duration=duration,
            error_type=error_type,
            details=details,
            script_path=script_path,
            line_number=line_number,
            fix_applied=fix_applied
        )
        self.attempts.append(attempt)
        
        if duration > 0:
            self.durations[operation].append(duration)
        
        # Save to Firestore if enabled and script_path provided
        if self.enable_firestore and script_path and self.metrics_collector:
            error_details = {
                "operation": operation,
                "duration": duration,
                "fix_applied": fix_applied
            }
            if line_number:
                error_details["line_number"] = line_number
            if details:
                error_details["details"] = details[:200]  # Limit size
            
            self.metrics_collector.save_metrics(
                script_path=script_path,
                status=outcome,
                original_error=error_type,
                error_details=error_details,
                message=f"{operation} {outcome}",
                fix_attempts=1 if outcome in ["fix_succeeded", "fix_failed"] else 0,
                fix_duration=duration,
                **kwargs
            )
    
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
    
    def save_summary_metrics(self, script_path: str):
        """Save summary metrics to Firestore"""
        if not self.enable_firestore or not self.metrics_collector:
            return
        
        total_attempts = sum(self.counter.values())
        if total_attempts == 0:
            return
        
        success_count = self.counter.get("success", 0) + self.counter.get("fix_succeeded", 0)
        failure_count = self.counter.get("failure", 0) + self.counter.get("fix_failed", 0)
        success_rate = (success_count / total_attempts) * 100 if total_attempts > 0 else 0
        
        avg_duration = 0.0
        if self.durations:
            all_durations = []
            for durations_list in self.durations.values():
                all_durations.extend(durations_list)
            avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0.0
        
        summary_details = {
            "total_attempts": total_attempts,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate_percent": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 3),
            "error_types": dict(self.get_error_summary())
        }
        
        self.metrics_collector.save_metrics(
            script_path=script_path,
            status="session_summary",
            error_details=summary_details,
            message=f"Session summary: {total_attempts} attempts, {success_rate:.1f}% success rate",
            fix_attempts=total_attempts,
            fix_duration=avg_duration
        )


# Convenience functions for easy metrics recording
def record_fix_attempt(script_path: str, outcome: str, error_type: str = None, 
                      duration: float = 0.0, line_number: int = None, **kwargs):
    """Convenience function to record a fix attempt with Firestore integration"""
    return save_metrics(
        script_path=script_path,
        status=outcome,
        original_error=error_type,
        error_details=kwargs,
        fix_duration=duration,
        fix_attempts=1 if outcome in ["fix_succeeded", "fix_failed"] else 0
    )

def record_session_start(script_path: str):
    """Record the start of an AutoFix session"""
    return save_metrics(
        script_path=script_path,
        status="session_start",
        message="AutoFix session started"
    )

def record_session_end(script_path: str, total_fixes: int = 0, success: bool = False):
    """Record the end of an AutoFix session"""
    return save_metrics(
        script_path=script_path,
        status="session_end",
        error_details={"total_fixes_attempted": total_fixes, "session_successful": success},
        message=f"AutoFix session ended - {'Success' if success else 'Failed'}",
        fix_attempts=total_fixes
    )


class ReportFormatter:
    """Handles formatting and display of AutoFix reports and analysis results"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def display_analysis_results(self, results: dict):
        """Display formatted analysis results"""
        print("\n" + "=" * 60)
        print("🔍 ANALYSIS RESULTS")
        print("=" * 60)
        
        if results.get('errors_found'):
            print(f"\n📋 Found {len(results['errors_found'])} potential issue(s):")
            
            for i, error in enumerate(results['errors_found'], 1):
                print(f"\n{i}. {error['type']}: {error['message']}")
                if error.get('suggested_fixes'):
                    print("   💡 Suggested fixes:")
                    for fix in error['suggested_fixes']:
                        print(f"      • {fix}")
                if error.get('file_path'):
                    print(f"   📁 File: {error['file_path']}")
                if error.get('line_number'):
                    print(f"   📍 Line: {error['line_number']}")
        else:
            print("\n✅ No issues detected - script should run without problems!")
        
        print("\n" + "=" * 60)
        print("💡 Run without --dry-run to apply fixes automatically")
        print("=" * 60)
    
    def print_banner(self, quiet_mode: bool = False):
        """Print AutoFix banner"""
        if not quiet_mode:
            self.logger.info("AutoFix v1.0.0 - Python Error Fixer")
            self.logger.info("=" * 40)
    
    def print_summary(self, script_path: str, success: bool):
        """Print execution summary"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"\n{'=' * 50}")
        self.logger.info(f"AutoFix Summary: {status}")
        self.logger.info(f"Script: {script_path}")
        self.logger.info(f"{'=' * 50}")


