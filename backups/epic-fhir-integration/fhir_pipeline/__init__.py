"""
FHIR Pipeline package for Epic FHIR integration.

This package includes:
- FHIR data extraction from Epic API
- Bronze to Silver transformation
- Silver to Gold transformation
- Validation and quality checks
"""

__version__ = "0.1.0"

# Make key modules available at package level
import fhir_pipeline.transforms
import fhir_pipeline.validation
import fhir_pipeline.utils 