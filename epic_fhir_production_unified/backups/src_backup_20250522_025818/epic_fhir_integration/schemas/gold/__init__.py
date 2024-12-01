"""Gold layer schemas for FHIR data."""

from epic_fhir_integration.schemas.gold.patient_schema import PATIENT_SCHEMA
from epic_fhir_integration.schemas.gold.observation_schema import OBSERVATION_SCHEMA
from epic_fhir_integration.schemas.gold.encounter_schema import ENCOUNTER_SCHEMA

# Export schemas for easy access
patient_schema = PATIENT_SCHEMA
observation_schema = OBSERVATION_SCHEMA
encounter_schema = ENCOUNTER_SCHEMA

__all__ = [
    "patient_schema",
    "observation_schema",
    "encounter_schema",
    "PATIENT_SCHEMA",
    "OBSERVATION_SCHEMA",
    "ENCOUNTER_SCHEMA",
] 