"""
Dashboard module for FHIR data quality visualization.

This module provides components for creating interactive dashboards
for data quality metrics, validation results, and quality trends.
"""

from epic_fhir_integration.metrics.dashboard.quality_dashboard import QualityDashboardGenerator
from epic_fhir_integration.metrics.dashboard.validation_dashboard import ValidationDashboard

__all__ = ["QualityDashboardGenerator", "ValidationDashboard"] 