"""
FHIRPath adapter for the new fhirpath library.

This module provides an adapter for the new fhirpath library while maintaining  
backward compatibility with the existing fhirpathpy implementation.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import the new fhirpath library
import fhirpath
# Keep the old library for compatibility
import fhirpathpy

logger = logging.getLogger(__name__)

class FHIRPathAdapter:
    """
    Adapter for the new fhirpath library that maintains compatibility with the existing API.
    
    This adapter allows for a smooth transition from fhirpathpy to the improved fhirpath
    implementation while maintaining backward compatibility.
    """
    
    def __init__(self, use_legacy: bool = False):
        """
        Initialize the FHIRPath adapter.
        
        Args:
            use_legacy: If True, use the legacy fhirpathpy implementation
        """
        self.use_legacy = use_legacy
    
    def evaluate(self, resource: Any, path: str) -> List[Any]:
        """
        Evaluate a FHIRPath expression on a FHIR resource.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            List of values matching the FHIRPath expression
        """
        try:
            # Convert FHIR resource model to dictionary if needed
            if hasattr(resource, "model_dump"):
                resource_dict = resource.model_dump()
            elif hasattr(resource, "dict"):
                resource_dict = resource.dict()
            else:
                resource_dict = resource
            
            if self.use_legacy:
                return fhirpathpy.evaluate(resource_dict, path)
            else:
                # Use the new fhirpath library
                # The new library returns a FHIRPathResult object, so we convert to list
                result = fhirpath.evaluate(resource_dict, path)
                if hasattr(result, "to_list"):
                    return result.to_list()
                return list(result) if result else []
                
        except Exception as e:
            logger.error(f"Error evaluating FHIRPath '{path}': {e}")
            return []

    def extract_first(self, resource: Any, path: str, default: Any = None) -> Any:
        """
        Extract the first matching value from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            default: Default value to return if no matches are found
            
        Returns:
            First value matching the FHIRPath expression, or default if none
        """
        results = self.evaluate(resource, path)
        if results and len(results) > 0:
            return results[0]
        return default
    
    def exists(self, resource: Any, path: str) -> bool:
        """
        Check if a FHIRPath expression has any matches in a FHIR resource.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            True if the expression has matches, False otherwise
        """
        try:
            if self.use_legacy:
                # Use the legacy implementation
                return bool(fhirpathpy.evaluate(resource, path))
            else:
                # The new library has a dedicated exists method
                if hasattr(resource, "model_dump"):
                    resource_dict = resource.model_dump()
                elif hasattr(resource, "dict"):
                    resource_dict = resource.dict()
                else:
                    resource_dict = resource
                
                return fhirpath.exists(resource_dict, path)
        except Exception as e:
            logger.error(f"Error checking existence of FHIRPath '{path}': {e}")
            return False

    def extract_with_paths(self, resource: Any, paths: List[str], default: Any = None) -> Any:
        """
        Try multiple FHIRPath expressions in order until one returns a value.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            paths: List of FHIRPath expressions to try
            default: Default value to return if no matches are found
            
        Returns:
            First value from the first path that has matches, or default if none
        """
        for path in paths:
            value = self.extract_first(resource, path)
            if value is not None:
                return value
        return default


# Create a backward-compatible interface that mimics the FHIRPathExtractor class
class FHIRPathExtractor:
    """Backward-compatible FHIRPathExtractor using the new adapter."""
    
    @staticmethod
    def extract(resource: Any, path: str) -> List[Any]:
        """
        Extract data from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            List of values matching the FHIRPath expression
        """
        adapter = FHIRPathAdapter(use_legacy=False)
        return adapter.evaluate(resource, path)
    
    @staticmethod
    def extract_first(resource: Any, path: str, default: Any = None) -> Any:
        """
        Extract the first matching value from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            default: Default value to return if no matches are found
            
        Returns:
            First value matching the FHIRPath expression, or default if none
        """
        adapter = FHIRPathAdapter(use_legacy=False)
        return adapter.extract_first(resource, path, default)
    
    @staticmethod
    def exists(resource: Any, path: str) -> bool:
        """
        Check if a FHIRPath expression has any matches in a FHIR resource.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            True if the expression has matches, False otherwise
        """
        adapter = FHIRPathAdapter(use_legacy=False)
        return adapter.exists(resource, path)
    
    @classmethod
    def extract_with_paths(cls, resource: Any, paths: List[str], default: Any = None) -> Any:
        """
        Try multiple FHIRPath expressions in order until one returns a value.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            paths: List of FHIRPath expressions to try
            default: Default value to return if no matches are found
            
        Returns:
            First value from the first path that has matches, or default if none
        """
        adapter = FHIRPathAdapter(use_legacy=False)
        return adapter.extract_with_paths(resource, paths, default)


# Create __init__.py in analytics directory
def create_analytics_init():
    return """\"\"\"
Analytics package for FHIR data using Pathling.

This package provides analytics capabilities for FHIR data using the Pathling library.
\"\"\"

from .pathling_service import PathlingService

__all__ = ["PathlingService"]
""" 