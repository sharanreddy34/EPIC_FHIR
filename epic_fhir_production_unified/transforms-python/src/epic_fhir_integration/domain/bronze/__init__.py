"""
Bronze layer modules for Epic FHIR integration.

This package contains transforms for ingesting raw FHIR resources from the Epic API.
"""

from epic_fhir_integration.bronze.extractor import (
    extract_resources,
    extract_patient_resources,
    extract_observation_resources,
    extract_encounter_resources
)

__all__ = [
    "extract_resources",
    "extract_patient_resources",
    "extract_observation_resources",
    "extract_encounter_resources"
] 