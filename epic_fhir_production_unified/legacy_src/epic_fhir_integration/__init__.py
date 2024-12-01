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
from epic_fhir_integration.datascience import *
from epic_fhir_integration.validation import * 