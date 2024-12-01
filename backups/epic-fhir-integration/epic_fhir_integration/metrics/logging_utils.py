"""
Utilities for enhanced logging configuration across the codebase.

This module provides utilities for configuring consistent logging across the codebase
with support for different formats, log levels, and output destinations.
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

# Custom debug levels for more granular control
DEBUG_BASIC = 10      # Basic debug info (standard DEBUG level)
DEBUG_DETAILED = 5    # More detailed debug info
DEBUG_TRACE = 3       # Trace-level debugging with full context

# Register custom log levels
logging.addLevelName(DEBUG_DETAILED, "DETAILED")
logging.addLevelName(DEBUG_TRACE, "TRACE")


# Add methods to Logger class for custom levels
def detailed(self, message, *args, **kwargs):
    """Log with DETAILED level."""
    if self.isEnabledFor(DEBUG_DETAILED):
        self._log(DEBUG_DETAILED, message, args, **kwargs)


def trace(self, message, *args, **kwargs):
    """Log with TRACE level."""
    if self.isEnabledFor(DEBUG_TRACE):
        self._log(DEBUG_TRACE, message, args, **kwargs)


# Add methods to Logger class
logging.Logger.detailed = detailed
logging.Logger.trace = trace


class ProgressTracker:
    """Track progress of operations for consistent logging."""
    
    def __init__(
        self, 
        logger: logging.Logger, 
        operation_name: str, 
        total_items: int, 
        log_interval: Optional[int] = None
    ):
        """Initialize progress tracker.
        
        Args:
            logger: Logger to use for logging progress
            operation_name: Name of the operation being tracked
            total_items: Total number of items to process
            log_interval: Number of items between progress logs, defaults to 10% of total
        """
        self.logger = logger
        self.operation_name = operation_name
        self.total_items = total_items
        self.start_time = time.time()
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.current_phase = "initializing"
        
        # Determine log interval if not specified
        if log_interval is None:
            # Log at most 10 times, but at least once
            self.log_interval = max(1, min(100, total_items // 10))
        else:
            self.log_interval = max(1, log_interval)
    
    def update(
        self, 
        items_processed: int = 1, 
        successful: int = 0, 
        failed: int = 0, 
        phase: Optional[str] = None,
        force_log: bool = False,
        **extra_context
    ) -> None:
        """Update progress and log if interval reached.
        
        Args:
            items_processed: Number of items processed in this update
            successful: Number of successfully processed items in this update
            failed: Number of failed items in this update
            phase: Current phase of the operation
            force_log: Force logging regardless of interval
            **extra_context: Additional context to include in log
        """
        self.processed_items += items_processed
        self.successful_items += successful
        self.failed_items += failed
        
        if phase:
            self.current_phase = phase
        
        # Log progress if interval reached or forced
        if force_log or (self.processed_items % self.log_interval == 0) or (self.processed_items >= self.total_items):
            self._log_progress(**extra_context)
    
    def _log_progress(self, **extra_context) -> None:
        """Log current progress."""
        elapsed_time = time.time() - self.start_time
        percent_complete = (self.processed_items / self.total_items) * 100 if self.total_items > 0 else 0
        
        # Create context for structured logging
        context = {
            "operation": self.operation_name,
            "phase": self.current_phase,
            "progress": f"{self.processed_items}/{self.total_items}",
            "percent_complete": f"{percent_complete:.1f}%",
            "successful": self.successful_items,
            "failed": self.failed_items,
            "elapsed_time": f"{elapsed_time:.2f}s",
        }
        
        # Add any extra context
        context.update(extra_context)
        
        # Format context for logging
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        
        # Log the progress
        self.logger.info(f"Progress - {self.operation_name}: {percent_complete:.1f}% complete ({self.processed_items}/{self.total_items}) [{context_str}]")
    
    def complete(self, **extra_context) -> Dict:
        """Mark operation as complete and log final status.
        
        Args:
            **extra_context: Additional context to include in log
            
        Returns:
            Dictionary with completion statistics
        """
        total_time = time.time() - self.start_time
        avg_time_per_item = total_time / self.processed_items if self.processed_items > 0 else 0
        success_rate = (self.successful_items / self.processed_items) * 100 if self.processed_items > 0 else 0
        
        # Create context for structured logging
        context = {
            "operation": self.operation_name,
            "total_processed": self.processed_items,
            "successful": self.successful_items,
            "failed": self.failed_items,
            "success_rate": f"{success_rate:.1f}%",
            "total_time": f"{total_time:.2f}s",
            "avg_time_per_item": f"{avg_time_per_item:.3f}s",
        }
        
        # Add any extra context
        context.update(extra_context)
        
        # Format context for logging
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        
        # Log the completion
        self.logger.info(f"Completed - {self.operation_name}: processed {self.processed_items} items in {total_time:.2f}s [{context_str}]")
        
        # Return statistics
        return {
            "operation": self.operation_name,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "success_rate": success_rate,
            "total_time": total_time,
            "avg_time_per_item": avg_time_per_item,
            **extra_context
        }


def configure_logging(
    log_level: int = logging.INFO,
    detailed_level: bool = False,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    module_levels: Optional[Dict[str, int]] = None
) -> logging.Logger:
    """Configure logging for the application.
    
    Args:
        log_level: Base log level for the root logger
        detailed_level: Whether to enable detailed logging
        log_file: Path to log file, if None logs to console only
        log_format: Custom log format string
        module_levels: Dict mapping module names to log levels
        
    Returns:
        Configured root logger
    """
    # Determine actual log level
    actual_level = DEBUG_DETAILED if detailed_level and log_level <= logging.DEBUG else log_level
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(actual_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Define log format
    if not log_format:
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    formatter = logging.Formatter(log_format)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(actual_level)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Create directory for log file if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(actual_level)
        root_logger.addHandler(file_handler)
    
    # Configure module-specific log levels
    if module_levels:
        for module_name, level in module_levels.items():
            logging.getLogger(module_name).setLevel(level)
    
    # Log configuration details
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with base level: {logging.getLevelName(log_level)}")
    if detailed_level and log_level <= logging.DEBUG:
        logger.info(f"Detailed logging enabled at level: {logging.getLevelName(actual_level)}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")
    if module_levels:
        logger.info(f"Module-specific log levels: {', '.join([f'{m}={logging.getLevelName(l)}' for m, l in module_levels.items()])}")
    
    return root_logger


def get_logger_with_context(name: str) -> logging.Logger:
    """Get a logger with context tracking capabilities.
    
    Args:
        name: Logger name
        
    Returns:
        Logger with context tracking
    """
    logger = logging.getLogger(name)
    
    # Add context tracking if not already done
    if not hasattr(logger, 'log_with_context'):
        def log_with_context(self, message: str, level: int = logging.INFO, **context):
            """Log a message with contextual information.
            
            Args:
                message: The message to log
                level: The logging level
                **context: Additional context to include in the log
            """
            if not self.isEnabledFor(level):
                return
                
            # Add timestamp to context
            context['timestamp'] = datetime.utcnow().isoformat()
            
            # Format the context
            if context:
                context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
                full_message = f"{message} [{context_str}]"
            else:
                full_message = message
                
            # Log at the appropriate level
            self.log(level, full_message)
        
        # Add method to logger instance
        logger.log_with_context = lambda *args, **kwargs: log_with_context(logger, *args, **kwargs)
    
    return logger


class TimingLogger:
    """A context manager for logging execution time of code blocks."""
    
    def __init__(self, logger: logging.Logger, operation_name: str, level: int = logging.DEBUG, **context):
        """Initialize timing logger.
        
        Args:
            logger: Logger to use for logging
            operation_name: Name of the operation being timed
            level: Log level to use
            **context: Additional context to include in log
        """
        self.logger = logger
        self.operation_name = operation_name
        self.level = level
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        
        # Only log entry if using DETAILED level or higher
        if self.logger.isEnabledFor(min(DEBUG_DETAILED, self.level)):
            context_str = ""
            if self.context:
                context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
                context_str = f" [{context_str}]"
            
            self.logger.log(self.level, f"Starting: {self.operation_name}{context_str}")
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log."""
        elapsed_time = time.time() - self.start_time
        
        # Update context with timing info
        context = {**self.context, "elapsed_time": f"{elapsed_time:.3f}s"}
        
        if exc_type is not None:
            # Log error with timing
            error_context = {
                **context,
                "error_type": exc_type.__name__,
                "error": str(exc_val)
            }
            
            context_str = " | ".join([f"{k}={v}" for k, v in error_context.items()])
            self.logger.error(f"Failed: {self.operation_name} [{context_str}]")
        else:
            # Log successful completion with timing
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.log(self.level, f"Completed: {self.operation_name} in {elapsed_time:.3f}s [{context_str}]")
        
        return False  # Don't suppress exceptions 