"""
Retry utilities for handling transient failures in network operations.

This module provides decorators and functions for retrying operations that may
fail transiently, such as API calls, with configurable backoff strategies.
"""

import functools
import logging
import random
import time
from typing import Any, Callable, List, Optional, Type, TypeVar, Union, cast

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)

# Generic return type for wrapped functions
T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    logger_name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Multiplier for backoff time after each retry
        jitter: Whether to add random jitter to backoff time
        exceptions: Exception type(s) to catch and retry on
        logger_name: Optional logger name to use
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger_name
            log = get_logger(logger_name or func.__module__)
            
            retry_count = 0
            current_backoff = initial_backoff
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        log.error(
                            f"Max retries ({max_retries}) exceeded",
                            function=func.__name__,
                            error=str(e)
                        )
                        raise
                    
                    # Calculate backoff time with optional jitter
                    sleep_time = min(current_backoff, max_backoff)
                    if jitter:
                        sleep_time = sleep_time * (0.5 + random.random())
                    
                    log.warning(
                        f"Retry {retry_count}/{max_retries} after error: {str(e)}",
                        function=func.__name__,
                        sleep_time=sleep_time,
                        error=str(e)
                    )
                    
                    time.sleep(sleep_time)
                    
                    # Increase backoff for next retry
                    current_backoff = min(current_backoff * backoff_factor, max_backoff)
                    
        return wrapper
    
    return decorator


def retry_on_exception(
    func: Callable[..., T],
    max_retries: int = 3,
    retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    backoff_strategy: str = "exponential",
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    log_level: int = logging.WARNING,
) -> T:
    """
    Retry a function call when specified exceptions occur.
    
    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        retry_exceptions: Exception type(s) to catch and retry on
        backoff_strategy: Backoff strategy ("constant", "linear", "exponential")
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for backoff time after each retry
        log_level: Logging level for retry messages
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception that occurred if all retries fail
    """
    if isinstance(retry_exceptions, list):
        exception_classes = tuple(retry_exceptions)
    else:
        exception_classes = (retry_exceptions,)
    
    attempt = 0
    last_exception = None
    
    while attempt <= max_retries:
        try:
            return func()
        except exception_classes as e:
            last_exception = e
            attempt += 1
            
            if attempt > max_retries:
                logger.error(
                    f"All {max_retries} retries failed",
                    function=getattr(func, "__name__", str(func)),
                    error=str(e)
                )
                raise
            
            # Calculate delay based on strategy
            if backoff_strategy == "constant":
                delay = initial_delay
            elif backoff_strategy == "linear":
                delay = min(initial_delay * attempt, max_delay)
            else:  # exponential
                delay = min(initial_delay * (backoff_factor ** (attempt - 1)), max_delay)
            
            # Add jitter (±10%)
            jitter = random.uniform(0.9, 1.1)
            delay *= jitter
            
            logger.log(
                log_level,
                f"Retry {attempt}/{max_retries} after error: {str(e)}",
                function=getattr(func, "__name__", str(func)),
                delay=delay,
                error=str(e)
            )
            
            time.sleep(delay)
    
    # This should never be reached due to the raise in the loop
    assert last_exception is not None
    raise last_exception


class RetrySession:
    """
    Context manager for executing code with retries.
    
    This class provides a context manager that allows for retrying
    code blocks with configurable retry policies.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
        backoff_strategy: str = "exponential",
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        log_level: int = logging.WARNING,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
    ):
        """
        Initialize a retry session.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_exceptions: Exception type(s) to catch and retry on
            backoff_strategy: Backoff strategy ("constant", "linear", "exponential")
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Multiplier for backoff time after each retry
            log_level: Logging level for retry messages
            on_retry: Optional callback function called on each retry
        """
        self.max_retries = max_retries
        self.retry_exceptions = retry_exceptions
        self.backoff_strategy = backoff_strategy
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.log_level = log_level
        self.on_retry = on_retry
        
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self) -> "RetrySession":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # No exception, successful execution
            return True
        
        # Check if the exception should be retried
        if isinstance(self.retry_exceptions, list):
            should_retry = any(isinstance(exc_val, ex) for ex in self.retry_exceptions)
        else:
            should_retry = isinstance(exc_val, self.retry_exceptions)
        
        if not should_retry:
            # Exception doesn't match retry_exceptions, don't handle it
            return False
        
        self.attempt += 1
        self.last_exception = exc_val
        
        if self.attempt > self.max_retries:
            logger.error(
                f"All {self.max_retries} retries failed",
                error=str(exc_val)
            )
            return False  # Don't suppress the exception
        
        # Calculate delay based on strategy
        if self.backoff_strategy == "constant":
            delay = self.initial_delay
        elif self.backoff_strategy == "linear":
            delay = min(self.initial_delay * self.attempt, self.max_delay)
        else:  # exponential
            delay = min(
                self.initial_delay * (self.backoff_factor ** (self.attempt - 1)),
                self.max_delay
            )
        
        # Add jitter (±10%)
        jitter = random.uniform(0.9, 1.1)
        delay *= jitter
        
        logger.log(
            self.log_level,
            f"Retry {self.attempt}/{self.max_retries} after error: {str(exc_val)}",
            delay=delay,
            error=str(exc_val)
        )
        
        # Call the retry callback if provided
        if self.on_retry:
            self.on_retry(exc_val, self.attempt)
        
        time.sleep(delay)
        
        # Return True to suppress the exception and retry the with block
        return True 