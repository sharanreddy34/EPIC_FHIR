"""
FHIRPath Adapter Module.

This module provides a wrapper around the fhirpath library for extracting data 
from FHIR resources. It implements caching and error handling for better performance
and robustness.
"""

import logging
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

try:
    # Try to import the preferred fhirpath library
    import fhirpath
    USING_FHIRPATH = True
except ImportError:
    # Fall back to fhirpathpy if the main library is not available
    import fhirpathpy
    USING_FHIRPATH = False

logger = logging.getLogger(__name__)


class FHIRPathAdapter:
    """Adapter for FHIRPath libraries with caching and error handling.
    
    This class provides a consistent interface for FHIRPath operations,
    regardless of which underlying library is used. It also implements
    caching for better performance when the same path is evaluated multiple
    times on different resources.
    """
    
    def __init__(self, cache_enabled: bool = True, cache_size: int = 128):
        """Initialize the FHIRPath adapter.
        
        Args:
            cache_enabled: Whether to enable caching of FHIRPath expressions.
            cache_size: Maximum number of FHIRPath expressions to cache.
        """
        self.cache_enabled = cache_enabled
        self.cache_size = cache_size
        self.using_fhirpath = USING_FHIRPATH
        
        if self.using_fhirpath:
            logger.info("Using 'fhirpath' library for FHIRPath evaluation")
        else:
            logger.info("Using 'fhirpathpy' library for FHIRPath evaluation")
    
    def extract(self, resource: Any, path: str) -> List[Any]:
        """Extract data from a FHIR resource using a FHIRPath expression.
        
        Args:
            resource: FHIR resource (dict or object).
            path: FHIRPath expression.
            
        Returns:
            List of extracted values.
            
        Raises:
            ValueError: If the path is invalid or the resource is None.
        """
        if resource is None:
            raise ValueError("Resource cannot be None")
        
        if not path:
            raise ValueError("Path cannot be empty")
        
        start_time = time.time()
        
        try:
            if self.cache_enabled:
                result = self._cached_extract(resource, path)
            else:
                result = self._extract_impl(resource, path)
                
            duration = time.time() - start_time
            if duration > 0.1:  # Log slow evaluations
                logger.debug(f"FHIRPath evaluation of '{path}' took {duration:.3f}s")
                
            return result
        
        except Exception as e:
            logger.error(f"Error evaluating FHIRPath expression '{path}': {str(e)}")
            raise
    
    def extract_first(self, resource: Any, path: str, default: Any = None) -> Any:
        """Extract the first matching value or return default.
        
        Args:
            resource: FHIR resource (dict or object).
            path: FHIRPath expression.
            default: Value to return if no matches are found.
            
        Returns:
            First matching value or default if no matches are found.
        """
        try:
            results = self.extract(resource, path)
            return results[0] if results else default
        except Exception as e:
            logger.error(f"Error extracting first value with path '{path}': {str(e)}")
            return default
    
    def exists(self, resource: Any, path: str) -> bool:
        """Check if a FHIRPath expression has any matches.
        
        Args:
            resource: FHIR resource (dict or object).
            path: FHIRPath expression.
            
        Returns:
            True if the expression has matches, False otherwise.
        """
        try:
            results = self.extract(resource, path)
            return bool(results)
        except Exception as e:
            logger.error(f"Error checking existence with path '{path}': {str(e)}")
            return False
    
    @lru_cache(maxsize=128)
    def _cached_extract(self, resource_str: str, path: str) -> List[Any]:
        """Cached version of _extract_impl.
        
        Since lru_cache requires hashable arguments, we need to convert the
        resource to a string representation.
        
        Args:
            resource_str: String representation of FHIR resource.
            path: FHIRPath expression.
            
        Returns:
            List of extracted values.
        """
        # Convert back to dict if needed
        import json
        if isinstance(resource_str, str):
            resource = json.loads(resource_str)
        else:
            resource = resource_str
            
        return self._extract_impl(resource, path)
    
    def _extract_impl(self, resource: Any, path: str) -> List[Any]:
        """Implementation of FHIRPath extraction logic.
        
        Args:
            resource: FHIR resource (dict or object).
            path: FHIRPath expression.
            
        Returns:
            List of extracted values.
        """
        if self.using_fhirpath:
            # Use the fhirpath library
            result = fhirpath.evaluate(resource, path)
        else:
            # Use the fhirpathpy library
            result = fhirpathpy.evaluate(resource, path)
            
        return result if isinstance(result, list) else [result] 