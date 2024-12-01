"""
Data science module for FHIR data analysis.

This module provides utilities for working with FHIR data in data science workflows.
"""

from epic_fhir_integration.datascience.fhir_dataset import (
    FHIRDataset,
    FHIRDatasetBuilder,
    CohortBuilder
)

__all__ = [
    "FHIRDataset",
    "FHIRDatasetBuilder",
    "CohortBuilder"
] 