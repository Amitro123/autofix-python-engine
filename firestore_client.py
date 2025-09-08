#!/usr/bin/env python3
"""
Firestore REST API client for secure metrics collection.

This module provides a Firestore client using the REST API instead of the Admin SDK.
This approach allows safe distribution without exposing service account keys.

Why REST API instead of Admin SDK:
- Admin SDK requires private service account keys (firebase-key.json)
- REST API uses public Web API keys, safe for client distribution
- No sensitive credentials exposed to end users
- Maintains full Firestore functionality for metrics collection
"""

import json
import os
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class FirestoreClient:
    """
    Firestore client using REST API for secure metrics collection.
    
    Uses Web API Key instead of service account for safe distribution.
    """
    
    def __init__(self, project_id: str = None, api_key: str = None, app_id: str = None):
        """
        Initialize Firestore REST API client.
        
        Args:
            project_id: Firebase project ID
            api_key: Web API key (safe for client distribution)
        """
        self.project_id = project_id
        self.api_key = api_key
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for REST API requests"""
        return {
            "Content-Type": "application/json",
        }
    
    def _convert_to_firestore_value(self, value: Any) -> Dict[str, Any]:
        """
        Convert Python value to Firestore REST API format.
        
        Firestore REST API requires specific value type formatting:
        - strings: {"stringValue": "text"}
        - integers: {"integerValue": "123"}
        - timestamps: {"timestampValue": "2023-01-01T00:00:00Z"}
        - maps: {"mapValue": {"fields": {...}}}
        """
        if isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, int):
            return {"integerValue": str(value)}
        elif isinstance(value, float):
            return {"doubleValue": value}
        elif isinstance(value, bool):
            return {"booleanValue": value}
        elif isinstance(value, datetime):
            # Convert to ISO format for Firestore timestamp
            iso_string = value.isoformat()
            if not iso_string.endswith('Z') and '+' not in iso_string:
                iso_string += 'Z'
            return {"timestampValue": iso_string}
        elif isinstance(value, dict):
            # Convert nested dictionary to Firestore map
            fields = {}
            for k, v in value.items():
                fields[k] = self._convert_to_firestore_value(v)
            return {"mapValue": {"fields": fields}}
        elif isinstance(value, list):
            # Convert list to Firestore array
            array_values = [self._convert_to_firestore_value(item) for item in value]
            return {"arrayValue": {"values": array_values}}
        elif value is None:
            return {"nullValue": None}
        else:
            # Fallback to string representation
            return {"stringValue": str(value)}
    
    def add_document(self, collection_path: str, data: Dict[str, Any]) -> bool:
        """
        Add a document to Firestore collection.
        
        Args:
            collection_path: Path to collection (e.g., "artifacts/app-id/metrics")
            data: Document data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert data to Firestore format
            fields = {}
            for key, value in data.items():
                fields[key] = self._convert_to_firestore_value(value)
            
            document = {"fields": fields}
            
            # Make REST API request
            url = f"{self.base_url}/{collection_path}?key={self.api_key}"
            headers = self._get_headers() 
            
            response = requests.post(url, json=document, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.debug(f"Successfully saved document to {collection_path}")
                return True
            else:
                logger.error(f"Failed to save document: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error saving to Firestore: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving to Firestore: {e}")
            return False

class MetricsCollector:
    """
    Handles metrics collection with standardized schema.
    
    All metrics documents follow this consistent schema:
    - app_id (string): Application identifier
    - script_path (string): Path to the script being processed
    - status (string): Operation status (success, failure, canceled, etc.)
    - original_error (string): Type of error detected (TypeError, IndexError, etc.)
    - error_details (map): Additional error information and context
    - message (string): Human-readable description
    - timestamp (timestamp): UTC timestamp of the event
    - fix_attempts (integer): Number of fix attempts made
    - fix_duration (float): Time spent on fixing in seconds
    """
    
    def __init__(self, project_id: str = None, api_key: str = None, app_id: str = None):
        """
        Initialize metrics collector.
        
        For end users: No configuration needed - metrics are handled transparently.
        For developers: Can override with custom Firebase project for testing.
        
        Args:
            project_id: Firebase project ID (uses default if not provided)
            api_key: Web API key (uses default if not provided)  
            app_id: Application ID (uses default if not provided)
        """
        # Default credentials for production metrics collection
        # These are safe public credentials, not secrets
        self.project_id = project_id or os.getenv('FIREBASE_PROJECT_ID', 'autofix-enginedb')
        self.api_key = api_key or os.getenv('FIREBASE_WEB_API_KEY', 'AIzaSyExample-WebAPIKey-ForMetrics')
        self.app_id = app_id or os.getenv('APP_ID', 'autofix-default-app')
        
        # Initialize Firestore client
        # Note: In production, credentials would be properly configured
        self.client = None
        try:
            if self.project_id and self.api_key:
                self.client = FirestoreClient(self.project_id, self.api_key)
                logger.debug("Metrics collection initialized")
        except Exception as e:
            logger.debug(f"Metrics collection disabled: {e}")
            self.client = None
    
    def save_metrics(self, script_path: str, status: str, original_error: str = None, 
                    error_details: Dict[str, Any] = None, message: str = None,
                    fix_attempts: int = 0, fix_duration: float = 0.0, **kwargs) -> bool:
        """
        Save metrics to Firestore with standardized schema.
        
        Args:
            script_path: Path to the script being processed
            status: Operation status (success, failure, canceled, fix_succeeded, fix_failed)
            original_error: Type of error detected (TypeError, IndexError, etc.)
            error_details: Additional error information and context
            message: Human-readable description of the event
            fix_attempts: Number of fix attempts made
            fix_duration: Time spent on fixing in seconds
            **kwargs: Additional fields to include
            
        Returns:
            bool: True if metrics saved successfully, False otherwise
        """
        if not self.client:
            logger.debug("Metrics collection disabled")
            return False
        
        try:
            # Build standardized metrics document
            metrics = {
                "app_id": self.app_id,
                "script_path": script_path,
                "status": status,
                "timestamp": datetime.now(timezone.utc),
                "fix_attempts": fix_attempts,
                "fix_duration": fix_duration
            }
            
            # Add optional fields if provided
            if original_error:
                metrics["original_error"] = original_error
            
            if error_details:
                metrics["error_details"] = error_details
            else:
                metrics["error_details"] = {}
            
            if message:
                metrics["message"] = message
            else:
                # Generate default message based on status
                if status == "success":
                    metrics["message"] = "Script executed successfully"
                elif status == "fix_succeeded":
                    metrics["message"] = f"Successfully fixed {original_error or 'error'}"
                elif status == "fix_failed":
                    metrics["message"] = f"Failed to fix {original_error or 'error'}"
                elif status == "canceled":
                    metrics["message"] = f"User canceled {original_error or 'error'} fix"
                else:
                    metrics["message"] = f"Status: {status}"
            
            # Add any additional fields
            metrics.update(kwargs)
            
            # Save to Firestore: artifacts/{app_id}/metrics
            collection_path = f"artifacts/{self.app_id}/metrics"
            success = self.client.add_document(collection_path, metrics)
            
            if success:
                logger.debug(f"Metrics saved: {status} for {os.path.basename(script_path)}")
            else:
                logger.debug(f"Failed to save metrics for {os.path.basename(script_path)}")
            
            return success
            
        except Exception as e:
            logger.debug(f"Error saving metrics: {e}")
            return False

# Global metrics collector instance
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def save_metrics(script_path: str, status: str, **kwargs) -> bool:
    """
    Convenience function to save metrics using global collector.
    
    Args:
        script_path: Path to the script being processed
        status: Operation status
        **kwargs: Additional metrics fields
        
    Returns:
        bool: True if saved successfully
    """
    collector = get_metrics_collector()
    return collector.save_metrics(script_path, status, **kwargs)
