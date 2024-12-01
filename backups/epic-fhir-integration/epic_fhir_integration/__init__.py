"""
Epic FHIR Integration Package.

This package provides tools for working with FHIR data from Epic systems,
including data acquisition, transformation, validation, and analysis.
"""

import os
import sys
import logging

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Add the parent directory to sys.path to import the compatibility layer
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import and install the compatibility layer for deprecated imports
try:
    from compatibility_layer import install_compatibility_layer
    install_compatibility_layer()
    logging.getLogger(__name__).info("Compatibility layer for deprecated imports installed")
except ImportError:
    logging.getLogger(__name__).warning("Failed to import compatibility_layer module")

# Package version
__version__ = "1.0.0"

# Re-export high-level APIs
from epic_fhir_integration.auth.jwt_auth import get_or_refresh_token, get_token_with_retry
from epic_fhir_integration.config.loader import get_config
from epic_fhir_integration.extract.extractor import extract_resources
from epic_fhir_integration.io.fhir_client import create_fhir_client, FHIRClient
from epic_fhir_integration.security.secret_store import (
    load_secret, save_secret, delete_secret, list_secrets
)
from epic_fhir_integration.transform.bronze_to_silver import (
    transform_bronze_to_silver, transform_all_bronze_to_silver
)
from epic_fhir_integration.transform.silver_to_gold import (
    transform_silver_to_gold, transform_all_silver_to_gold, validate_schemas
)
from epic_fhir_integration.transform.gold import (
    PatientSummary, ObservationSummary, EncounterSummary
)
from epic_fhir_integration.schemas.gold import (
    patient_schema, observation_schema, encounter_schema
)

# Added from merged modules
from epic_fhir_integration.datascience import *
from epic_fhir_integration.validation import *
from epic_fhir_integration.profiles import * 