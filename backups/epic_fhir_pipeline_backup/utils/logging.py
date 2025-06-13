"""
Centralized logging configuration for FHIR pipeline.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    module_name: str = "fhir_pipeline",
) -> logging.Logger:
    """
    Configure logging for the FHIR pipeline.
    
    Args:
        level: Logging level
        log_file: Optional file to log to
        module_name: Logger name
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if requested
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(
    module_name: str,
    debug: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Get a configured logger for a module.
    
    Args:
        module_name: Name for the logger
        debug: Whether to enable debug logging
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    level = logging.DEBUG if debug else logging.INFO
    log_file_path = Path(log_file) if log_file else None
    return configure_logging(level, log_file_path, module_name) 