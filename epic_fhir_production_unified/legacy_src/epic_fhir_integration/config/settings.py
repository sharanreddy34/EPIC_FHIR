"""
Configuration settings for the Epic FHIR integration.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = os.environ.get('EPIC_FHIR_DATA_DIR', BASE_DIR / 'data')
TEMP_DIR = os.environ.get('EPIC_FHIR_TEMP_DIR', BASE_DIR / 'temp')
LOGS_DIR = os.environ.get('EPIC_FHIR_LOGS_DIR', BASE_DIR / 'logs')

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Epic API settings
EPIC_FHIR_BASE_URL = os.environ.get(
    'EPIC_FHIR_BASE_URL', 
    'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4'
)

# Pathling settings
PATHLING_DOCKER_IMAGE = 'aehrc/pathling:6.3.0'
PATHLING_BASE_URL = os.environ.get('PATHLING_BASE_URL', 'http://localhost:8080/fhir')
PATHLING_MEMORY = os.environ.get('PATHLING_MEMORY', '4g')

# DataScience settings
DEFAULT_DATASET_FORMAT = 'pandas'
MAX_DATAFRAME_DISPLAY_ROWS = 100

# Validation settings
DEFAULT_FHIR_VERSION = 'R4'
DEFAULT_PROFILE_PATH = BASE_DIR / 'epic_fhir_integration' / 'profiles' / 'epic'
VALIDATION_LEVEL = 'standard'  # Can be 'minimum', 'standard', or 'strict'

# Security settings
JWT_ISSUER = os.environ.get('JWT_ISSUER', 'epic_fhir_integration')
CLIENT_ID = os.environ.get('EPIC_CLIENT_ID', '02317de4-f128-4607-989b-07892f678580')

# Token settings
TOKEN_CACHE_ENABLED = True
TOKEN_CACHE_FILE = 'epic_token.json'
TOKEN_REFRESH_MARGIN_SECONDS = 300  # 5 minutes 