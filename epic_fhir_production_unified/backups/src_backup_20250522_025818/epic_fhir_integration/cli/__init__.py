"""Command-line interface package for Epic FHIR integration."""

# Import all CLI command groups
from epic_fhir_integration.cli.analytics import analytics
from epic_fhir_integration.cli.auth_token import auth
from epic_fhir_integration.cli.extract import extract
from epic_fhir_integration.cli.transform_bronze import transform_bronze
from epic_fhir_integration.cli.transform_gold import transform_gold
from epic_fhir_integration.cli.run_pipeline import pipeline
from epic_fhir_integration.cli.validate_run import validate
from epic_fhir_integration.cli.dashboard_commands import dashboard_group

# Define all available command groups
__all__ = [
    'analytics',
    'auth',
    'extract',
    'transform_bronze',
    'transform_gold',
    'pipeline',
    'validate',
    'dashboard_group'
] 