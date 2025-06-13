"""Schema module for FHIR data transformations."""

from epic_fhir_integration.schemas.gold import (
    patient_schema,
    observation_schema,
    encounter_schema,
)

__all__ = [
    "patient_schema",
    "observation_schema",
    "encounter_schema",
] 