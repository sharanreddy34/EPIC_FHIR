"""
Structured logging configuration for Epic FHIR integration.

This module configures structured JSON logging for Foundry compatibility.
"""

import json
import logging
import sys
from datetime import datetime
import time


def configure_logging():
    """Configure structured JSON logging for Foundry compatibility."""
    
    # Set up the root logger
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(message)s",  # We'll format as JSON in the filter
    )
    
    # Add a JSON formatter
    class JsonFormatter(logging.Filter):
        def filter(self, record):
            # Extract standard attributes
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "module": record.module,
                "message": record.getMessage(),
            }
            
            # Add any extra attributes passed via the extra parameter
            for key, value in getattr(record, "extras", {}).items():
                log_data[key] = value
                
            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                }
            
            # Replace the message with the JSON string
            record.msg = json.dumps(log_data)
            record.args = ()
            
            return True
    
    # Apply the filter to the root logger
    logging.getLogger().addFilter(JsonFormatter())
    
    # Log startup message
    logging.info("Logging configured for Foundry integration")
    
    return logging.getLogger()


def get_logger(name):
    """Get a logger with the specified name, configured for JSON output."""
    return logging.getLogger(name)


def log_with_context(logger, level, message, **context):
    """Log with additional context as structured fields."""
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    logger.log(level, message, extra={"extras": context})


class LogMetrics:
    """Context manager for logging metrics around a code block."""
    
    def __init__(self, logger, operation_name):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # Success case
            self.logger.info(
                f"Completed {self.operation_name}",
                extra={"fields": {"duration_seconds": duration}}
            )
        else:
            # Error case
            self.logger.error(
                f"Failed {self.operation_name}: {exc_val}",
                extra={"fields": {"duration_seconds": duration, "error": str(exc_val)}}
            )
            
    def log_count(self, count, entity_type="records"):
        """Log a count metric."""
        self.logger.info(
            f"Processed {count} {entity_type}",
            extra={"fields": {f"{entity_type}_count": count}}
        ) 