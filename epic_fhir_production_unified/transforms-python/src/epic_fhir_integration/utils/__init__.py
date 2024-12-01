"""
Utility modules for Epic FHIR integration.

This package contains common utility functions and classes used throughout the
Epic FHIR integration codebase.
"""

from epic_fhir_integration.utils.logging import (
    configure_logging,
    get_logger,
    log_with_context
)

__all__ = [
    "configure_logging",
    "get_logger",
    "log_with_context"
] 