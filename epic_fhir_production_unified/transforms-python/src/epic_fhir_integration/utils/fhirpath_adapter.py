"""
FHIRPath adapter for querying FHIR resources.

This module provides a wrapper around the fhirpathpy library to provide a more
Pythonic interface for querying FHIR resources using FHIRPath expressions.
"""

from typing import Any, Dict, List, Optional, Union, cast
import logging
import re

# Import fhirpathpy with error handling
try:
    import fhirpathpy
except ImportError:
    # Raise a more informative error message
    raise ImportError(
        "fhirpathpy package is required for FHIRPath queries. "
        "Install it with 'pip install fhirpathpy'."
    )

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


class FHIRPathAdapter:
    """
    Adapter class for executing FHIRPath queries on FHIR resources.
    
    This class wraps the fhirpathpy library to provide a simplified interface
    and handle errors gracefully.
    """
    
    def __init__(self, resource: Optional[Dict[str, Any]] = None):
        """
        Initialize the FHIRPath adapter.
        
        Args:
            resource: Optional FHIR resource to query
        """
        self.resource = resource
    
    def set_resource(self, resource: Dict[str, Any]) -> None:
        """
        Set the FHIR resource to query.
        
        Args:
            resource: FHIR resource dictionary
        """
        self.resource = resource
    
    def evaluate(
        self, 
        fhirpath_expr: str, 
        resource: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Evaluate a FHIRPath expression against a FHIR resource.
        
        Args:
            fhirpath_expr: FHIRPath expression string
            resource: Optional resource to query (uses self.resource if None)
            
        Returns:
            List of results from the FHIRPath query
            
        Raises:
            ValueError: If no resource is available to query
        """
        target_resource = resource if resource is not None else self.resource
        
        if target_resource is None:
            raise ValueError("No FHIR resource provided for FHIRPath evaluation")
        
        try:
            result = fhirpathpy.evaluate(target_resource, fhirpath_expr)
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.warning(
                f"FHIRPath evaluation error: {e}",
                expression=fhirpath_expr
            )
            return []
    
    def extract_first(
        self, 
        fhirpath_expr: str, 
        resource: Optional[Dict[str, Any]] = None,
        default: Any = None
    ) -> Any:
        """
        Extract the first result from a FHIRPath expression.
        
        Args:
            fhirpath_expr: FHIRPath expression string
            resource: Optional resource to query (uses self.resource if None)
            default: Default value to return if no results
            
        Returns:
            First result from the FHIRPath query, or default if none
        """
        results = self.evaluate(fhirpath_expr, resource)
        
        if not results:
            return default
        
        return results[0]
    
    def extract_scalar(
        self, 
        fhirpath_expr: str, 
        resource: Optional[Dict[str, Any]] = None,
        default: Any = None
    ) -> Any:
        """
        Extract a scalar value from a FHIRPath expression.
        
        This method is similar to extract_first but tries to handle
        common result types (lists, dicts with single values) to return
        a clean scalar value.
        
        Args:
            fhirpath_expr: FHIRPath expression string
            resource: Optional resource to query (uses self.resource if None)
            default: Default value to return if no results
            
        Returns:
            Scalar value from the FHIRPath query, or default if none
        """
        value = self.extract_first(fhirpath_expr, resource, default)
        
        # Handle empty results
        if value is None:
            return default
        
        # Handle list with single item
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        
        # Handle dict with single value (common in FHIR)
        if isinstance(value, dict) and len(value) == 1:
            value = next(iter(value.values()))
        
        return value
    
    def exists(
        self, 
        fhirpath_expr: str, 
        resource: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a FHIRPath expression returns any results.
        
        Args:
            fhirpath_expr: FHIRPath expression string
            resource: Optional resource to query (uses self.resource if None)
            
        Returns:
            True if the expression returns any results, False otherwise
        """
        results = self.evaluate(fhirpath_expr, resource)
        return bool(results)
    
    def count(
        self, 
        fhirpath_expr: str, 
        resource: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count the number of results from a FHIRPath expression.
        
        Args:
            fhirpath_expr: FHIRPath expression string
            resource: Optional resource to query (uses self.resource if None)
            
        Returns:
            Number of results from the FHIRPath query
        """
        results = self.evaluate(fhirpath_expr, resource)
        return len(results)
    
    @staticmethod
    def simplify_path(path: str) -> str:
        """
        Convert a dotted path to a FHIRPath expression.
        
        Args:
            path: Dotted path string (e.g., "patient.name[0].given[0]")
            
        Returns:
            FHIRPath expression string
        """
        # Replace array indices with FHIRPath syntax
        # Example: name[0].given[0] -> name.first().given.first()
        simplified = re.sub(r"\[0\]", ".first()", path)
        simplified = re.sub(r"\[(\d+)\]", lambda m: f"[{int(m.group(1))-1}]", simplified)
        
        return simplified


# Global instance for convenience
fhirpath = FHIRPathAdapter() 