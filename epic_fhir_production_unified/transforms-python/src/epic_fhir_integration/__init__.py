"""
Epic FHIR Integration Package.

This package provides tools for working with FHIR data from Epic systems,
including data acquisition, transformation, validation, and analysis.
"""

import os
import sys
import logging

# Configure the root logger
from epic_fhir_integration.utils.logging import configure_logging
configure_logging()

# Package version
__version__ = "0.1.0"

# Configure logging utilities
from epic_fhir_integration.utils.logging import get_logger, log_with_context

# ----------------------------------------------------------------------
# Public API re-exports
# ----------------------------------------------------------------------
from epic_fhir_integration.infrastructure.api_clients.jwt_auth import (
    get_or_refresh_token,
    get_token_with_retry,
)
from epic_fhir_integration.infrastructure.api_clients.fhir_client import (
    create_fhir_client,
    FHIRClient,
)
from epic_fhir_integration.domain.bronze.resource_extractor import (
    extract_resource,
    extract_all_resources,
)
from epic_fhir_integration.domain.validation.ge_validator import (
    validate_with_great_expectations,
)

__all__ = [
    "__version__",
    # Auth & Client
    "get_or_refresh_token",
    "get_token_with_retry",
    "create_fhir_client",
    "FHIRClient",
    # Logging
    "get_logger",
    "log_with_context",
    "configure_logging",
    # Bronze Extraction
    "extract_resource",
    "extract_all_resources",
    # Validation
    "validate_with_great_expectations",
]

# Legacy lazy import mechanism removed after package re-org 