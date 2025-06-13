"""
Input/Output module for FHIR operations.

This module provides clients and utilities for working with FHIR servers.
"""

from epic_fhir_integration.io.fhir_client import (
    FHIRClient,
    create_fhir_client
)

__all__ = [
    "FHIRClient",
    "create_fhir_client"
] 