"""
Dashboard module for FHIR data quality and validation metrics.
"""

from epic_fhir_integration.metrics.dashboard.quality_dashboard import QualityDashboard
from epic_fhir_integration.metrics.dashboard.validation_dashboard import ValidationDashboard

__all__ = ['QualityDashboard', 'ValidationDashboard'] 