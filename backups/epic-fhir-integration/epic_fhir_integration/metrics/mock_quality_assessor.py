"""
Mock Quality Assessor for FHIR resources.

This module provides a simplified mock implementation to replace
the real Great Expectations-based validator with a version that 
always returns success values without requiring the dependency.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MockGreatExpectationsValidator:
    """A mock implementation of the Great Expectations validator."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the mock validator, accepting any arguments but not using them."""
        logger.info("Using MockGreatExpectationsValidator")
    
    def validate_resource(self, resource, *args, **kwargs):
        """Mock validation that always succeeds."""
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "unknown")
        
        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "is_valid": True,
            "validation_type": "MOCK",
            "issues": []
        }
    
    def validate_resources(self, resources, *args, **kwargs):
        """Mock batch validation that always succeeds."""
        results = []
        
        for resource in resources:
            result = self.validate_resource(resource)
            results.append(result)
        
        return {
            "timestamp": "2025-05-21T00:00:00Z",
            "pipeline_stage": kwargs.get("pipeline_stage", "unknown"),
            "validation_type": "MOCK",
            "resources_total": len(resources),
            "resources_valid": len(resources),
            "validation_rate": 1.0,
            "total_issues": 0,
            "issues_per_resource": 0,
            "results": results
        }


def assess_resources(resources: Dict[str, List[Dict[str, Any]]], tier: str = "bronze") -> Dict[str, Any]:
    """A mock implementation of the quality assessor.
    
    Args:
        resources: Dictionary of FHIR resources by type
        tier: Data quality tier
        
    Returns:
        Dictionary with mock quality metrics
    """
    # Count resources
    resource_counts = {resource_type: len(resources_list) for resource_type, resources_list in resources.items()}
    total_resources = sum(resource_counts.values())
    
    # Create mock quality metrics
    return {
        "tier": tier,
        "resource_counts": resource_counts,
        "total_resources": total_resources,
        "quality_scores": {
            "completeness": 0.95,
            "conformance": 1.0,
            "consistency": 0.98,
            "timeliness": 0.99
        },
        "overall_quality": 0.98,
        "resource_types": list(resources.keys()),
        "mock_mode": True
    } 