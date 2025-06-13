"""
Retry Utilities for EPIC FHIR Integration

This module provides utilities for retrying operations that may fail due to
transient errors, such as network timeouts or API rate limits.
"""

import time
import random
import logging
import functools
from typing import Callable, Type, Union, List, Optional, Any, Dict, Tuple

logger = logging.getLogger(__name__)

# Default retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_JITTER = 0.1


def exponential_backoff(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    jitter: float = DEFAULT_JITTER
) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Factor to increase delay by
        jitter: Random jitter factor (0-1)
        
    Returns:
        Delay in seconds
    """
    # Calculate delay with exponential backoff
    delay = min(max_delay, base_delay * (backoff_factor ** attempt))
    
    # Add random jitter
    if jitter > 0:
        delay = delay * (1 + random.uniform(-jitter, jitter))
        
    return delay


def retry_on_exceptions(
    max_retries: int = DEFAULT_MAX_RETRIES,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    backoff_func: Callable[[int], float] = exponential_backoff,
    should_retry_func: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
):
    """
    Decorator for retrying a function when specific exceptions occur.
    
    Args:
        max_retries: Maximum number of retry attempts
        exceptions: Exception type(s) to catch and retry on
        backoff_func: Function to calculate backoff delay
        should_retry_func: Function to determine if retry should be attempted
        on_retry: Function called before each retry
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Attempt to call the function
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if attempt >= max_retries:
                        # Max retries reached, re-raise
                        logger.warning(f"Max retries ({max_retries}) reached, giving up")
                        raise
                        
                    if should_retry_func and not should_retry_func(e):
                        # Don't retry based on exception
                        logger.info(f"Not retrying based on exception: {e}")
                        raise
                        
                    # Calculate delay
                    delay = backoff_func(attempt)
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e, delay)
                        except Exception as callback_e:
                            logger.warning(f"Error in on_retry callback: {callback_e}")
                    
                    # Log the retry
                    logger.warning(
                        f"Retry {attempt+1}/{max_retries} after error: {e}. "
                        f"Waiting {delay:.2f} seconds before next attempt."
                    )
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This point should not be reached, but if it is, re-raise the last exception
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def retry_with_timeout(
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: float = 60.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    backoff_func: Callable[[int], float] = exponential_backoff
):
    """
    Decorator for retrying a function with a total timeout.
    
    Args:
        max_retries: Maximum number of retry attempts
        timeout: Maximum total time to spend retrying in seconds
        exceptions: Exception type(s) to catch and retry on
        backoff_func: Function to calculate backoff delay
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Attempt to call the function
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if attempt >= max_retries:
                        # Max retries reached, re-raise
                        logger.warning(f"Max retries ({max_retries}) reached, giving up")
                        raise
                        
                    # Calculate delay
                    delay = backoff_func(attempt)
                    
                    # Check if we would exceed timeout
                    elapsed = time.time() - start_time
                    if elapsed + delay > timeout:
                        logger.warning(f"Timeout of {timeout}s would be exceeded, giving up after {attempt+1} attempts")
                        raise
                    
                    # Log the retry
                    logger.warning(
                        f"Retry {attempt+1}/{max_retries} after error: {e}. "
                        f"Waiting {delay:.2f} seconds before next attempt. "
                        f"Elapsed time: {elapsed:.2f}s, timeout: {timeout:.2f}s"
                    )
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This point should not be reached, but if it is, re-raise the last exception
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def is_transient_error(exception: Exception) -> bool:
    """
    Check if an exception represents a transient error that should be retried.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the exception is a transient error, False otherwise
    """
    import requests
    
    # Check request exceptions that are typically transient
    if isinstance(exception, requests.exceptions.RequestException):
        # Network errors
        if isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError
        )):
            return True
            
        # Check status code for server errors
        if isinstance(exception, requests.exceptions.HTTPError):
            status_code = exception.response.status_code if exception.response else 0
            # 429 Too Many Requests, or 5xx Server Error
            return status_code == 429 or (500 <= status_code < 600)
    
    # Check for common database errors
    if exception.__class__.__name__ in [
        'OperationalError',    # Database operational errors
        'InterfaceError',      # Database interface errors
        'InternalError',       # Database internal errors
        'LockTimeoutError'     # Lock timeouts
    ]:
        return True
        
    # Spark errors that might be transient
    if 'SparkException' in exception.__class__.__name__:
        error_msg = str(exception).lower()
        return any(term in error_msg for term in [
            'timeout',
            'connection reset',
            'connection refused',
            'temporarily unavailable',
            'resource temporarily unavailable',
            'executor lost',
            'task failed'
        ])
    
    # Generic transient error indicators
    error_msg = str(exception).lower()
    return any(term in error_msg for term in [
        'timeout',
        'temporary',
        'temporarily',
        'retriable',
        'retry',
        'retryable',
        'rate limit',
        'throttl',
        'back-off',
        'backoff',
        'overload',
        'busy',
        'unavailable',
        'connection reset',
        'connection refused',
        'network'
    ])


def retry_api_call(
    func: Callable,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs
) -> Any:
    """
    Retry an API call with exponential backoff for transient errors.
    
    This is a convenience function for common API call scenarios.
    
    Args:
        func: Function to call
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function call
    """
    import requests
    
    # Define retry callback
    def on_retry_callback(attempt, exception, delay):
        logger.warning(
            f"API call failed (attempt {attempt}/{max_retries}): {exception}. "
            f"Retrying in {delay:.2f} seconds..."
        )
    
    # Create decorated function
    @retry_on_exceptions(
        max_retries=max_retries,
        exceptions=(requests.exceptions.RequestException, IOError, ConnectionError),
        should_retry_func=is_transient_error,
        on_retry=on_retry_callback
    )
    def _call_with_retry():
        return func(*args, **kwargs)
    
    # Call the decorated function
    return _call_with_retry() 