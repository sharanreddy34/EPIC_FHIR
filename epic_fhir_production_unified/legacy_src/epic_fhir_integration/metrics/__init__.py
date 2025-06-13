"""
EPIC FHIR Integration Metrics Package

This package provides utilities for collecting, aggregating, and analyzing 
metrics throughout the FHIR processing pipeline.
"""

from epic_fhir_integration.metrics.collector import (
    record_metric,
    flush_metrics,
    get_collector_instance
)

__all__ = [
    'record_metric', 
    'flush_metrics',
    'get_collector_instance'
] 