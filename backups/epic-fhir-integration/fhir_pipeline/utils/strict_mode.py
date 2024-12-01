"""
Strict Mode Utilities for FHIR Pipeline

This module provides utilities for enforcing strict mode in the FHIR pipeline,
which prevents the use of mock data and ensures all data comes from real Epic FHIR API.
"""

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Global variable to track strict mode
_STRICT_MODE_ENABLED = False

def get_strict_mode():
    """Get the current strict mode setting."""
    # Check environment variable first
    env_strict = os.environ.get("FHIR_STRICT_MODE", "").lower()
    if env_strict in ("true", "1", "yes"):
        return True
    
    # Then check global variable (set by enable_strict_mode)
    return _STRICT_MODE_ENABLED

def enable_strict_mode(enable=True):
    """Enable or disable strict mode globally."""
    global _STRICT_MODE_ENABLED
    _STRICT_MODE_ENABLED = enable
    logger.info(f"Strict mode {'enabled' if enable else 'disabled'}")
    
    # Also set environment variable for child processes
    if enable:
        os.environ["FHIR_STRICT_MODE"] = "true"
    else:
        os.environ.pop("FHIR_STRICT_MODE", None)
    
    return _STRICT_MODE_ENABLED

def strict_mode_check(mock_attempted=None):
    """
    Check if strict mode is enabled and raise an error if mock data is attempted.
    
    Args:
        mock_attempted: Description of the mock data that was attempted
        
    Raises:
        RuntimeError: If strict mode is enabled and mock data is attempted
    """
    if get_strict_mode() and mock_attempted:
        error_message = f"STRICT MODE VIOLATION: Attempted to use mock data ({mock_attempted})."
        logger.error(error_message)
        raise RuntimeError(error_message)

def no_mocks(mock_type=None):
    """
    Decorator to enforce strict mode in functions.
    
    Args:
        mock_type: Description of the mock data this function might use
    
    Returns:
        Decorated function that checks strict mode
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # If mock_mode is explicitly passed as an argument, check it
            if 'mock_mode' in kwargs and kwargs['mock_mode']:
                mock_description = mock_type or f"mock_mode in {func.__name__}"
                strict_mode_check(mock_description)
            
            # Otherwise, just run the function
            return func(*args, **kwargs)
        return wrapper
    return decorator 