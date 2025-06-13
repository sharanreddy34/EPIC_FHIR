import logging
import uuid
import os
from typing import Dict, Any, Optional

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False
    logging.warning("python-json-logger not available, falling back to standard logging")

# Create a unique run ID for this process
RUN_ID = os.environ.get("RUN_ID", str(uuid.uuid4())[:8])

def get_logger(
    name: str, 
    level: str = "INFO", 
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    **context
) -> logging.LoggerAdapter:
    """
    Get a configured logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Log level
        log_to_file: Whether to log to file in addition to console
        log_file: Path to log file (if None, uses name)
        **context: Additional context fields to include in logs
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicate logging
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set formatter based on availability
    if HAS_JSON_LOGGER:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        if log_file is None:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{name}.log")
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add context via LoggerAdapter
    standard_context = {
        "run_id": RUN_ID,
        "environment": os.environ.get("ENVIRONMENT", "development")
    }
    
    # Add custom context
    context_dict = {**standard_context, **context}
    
    # Create adapter with context
    logger_with_context = logging.LoggerAdapter(logger, context_dict)
    
    return logger_with_context

def mask_pii(text: str) -> str:
    """
    Mask potential PII in log messages.
    
    Args:
        text: Text that might contain PII
        
    Returns:
        Text with PII masked
    """
    import re
    
    # Simple patterns for potentially sensitive info
    patterns = [
        # SSN: XXX-XX-XXXX
        (r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX'),
        
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL@MASKED'),
        
        # Phone numbers (simple pattern)
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'PHONE-MASKED'),
        
        # Credit card numbers (simplified)
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'XXXX-XXXX-XXXX-XXXX'),
    ]
    
    masked_text = text
    for pattern, replacement in patterns:
        masked_text = re.sub(pattern, replacement, masked_text)
    
    return masked_text 