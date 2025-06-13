"""
Serialization helpers for FHIR results.

This module provides utilities to ensure FHIR results can be properly serialized
to JSON, handling special data types like dates and decimals.
"""

import json
import datetime
from typing import Any, Dict, List, Optional, Union


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime, date, and other special types.
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert special types to JSON serializable values.
        
        Args:
            obj: The object to convert
            
        Returns:
            A JSON serializable representation of the object
        """
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif hasattr(obj, '__str__'):
            return str(obj)
        return super().default(obj)


def serialize_results(results: Any) -> str:
    """
    Serialize results to JSON, handling special types.
    
    Args:
        results: The results to serialize
        
    Returns:
        JSON string representation of the results
    """
    return json.dumps(results, cls=JSONEncoder)


def deserialize_results(json_str: str) -> Any:
    """
    Deserialize results from JSON.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        Deserialized object
    """
    return json.loads(json_str)


def ensure_serializable(obj: Any) -> Any:
    """
    Ensure an object is JSON serializable.
    
    Args:
        obj: The object to make serializable
        
    Returns:
        A serializable representation of the object
    """
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: ensure_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_serializable(item) for item in obj]
    elif hasattr(obj, 'dict') and callable(obj.dict):
        return ensure_serializable(obj.dict())
    elif hasattr(obj, 'model_dump') and callable(obj.model_dump):
        return ensure_serializable(obj.model_dump())
    elif hasattr(obj, '__dict__'):
        return ensure_serializable(obj.__dict__)
    return obj 