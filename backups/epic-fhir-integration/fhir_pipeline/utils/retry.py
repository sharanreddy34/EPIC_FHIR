"""
Retry functionality for handling transient errors.
"""

import time
import functools
import logging

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Error that should trigger a retry."""
    pass


def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    Retry decorator with exponential backoff.
    
    Args:
        retries: Maximum number of retries
        backoff_in_seconds: Initial backoff time in seconds
        
    Returns:
        Decorated function that will retry on RetryableError
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Initial values
            attempt = 0
            delay = backoff_in_seconds
            
            # Try until success or max retries
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except RetryableError as e:
                    # Increment attempt counter
                    attempt += 1
                    
                    # If this was the last attempt, re-raise the exception
                    if attempt == retries:
                        raise
                    
                    # Log the retry
                    logger.warning(
                        "Retryable error: %s. Retrying in %s seconds... (Attempt %s/%s)",
                        str(e), delay, attempt, retries
                    )
                    
                    # Wait before next attempt
                    time.sleep(delay)
                    
                    # Exponential backoff
                    delay *= 2
            
            # This shouldn't be reached, but just in case
            return func(*args, **kwargs)
            
        return wrapper
    return decorator 