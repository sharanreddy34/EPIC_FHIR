"""
FHIRPath adapter for the fhirpath library.

This module provides an adapter for the fhirpath library, replacing fhirpathpy
while maintaining a compatible API for existing code.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter

# Define a mock FHIRPath class to avoid dependency errors
class MockFHIRPath:
    def __init__(self, resource=None):
        self._obj = resource
        
    def evaluate(self, resource, path):
        """
        Handle basic FHIRPath expressions for testing.
        This is an improved version that can handle simple where() filters and first() function.
        """
        if resource is None or path is None:
            return []
        
        logger.debug(f"MockFHIRPath evaluating: {path} on resource type: {type(resource).__name__}")
            
        # Special handling for commonly used complex paths that the mock can't truly parse
        if path == "name.where(use='official').given.first()":
            # Special handling for patient name
            if isinstance(resource, dict) and "name" in resource and isinstance(resource["name"], list):
                for name_entry in resource["name"]:
                    if isinstance(name_entry, dict) and name_entry.get("use") == "official":
                        if "given" in name_entry and isinstance(name_entry["given"], list) and name_entry["given"]:
                            return [name_entry["given"][0]]
            return []
            
        if path == "name.where(use='official').family":
            # Special handling for patient family name
            if isinstance(resource, dict) and "name" in resource and isinstance(resource["name"], list):
                for name_entry in resource["name"]:
                    if isinstance(name_entry, dict) and name_entry.get("use") == "official":
                        if "family" in name_entry:
                            return [name_entry["family"]]
            return []

        if path == "telecom.where(system='phone').value.first()":
            # Special handling for phone
            if isinstance(resource, dict) and "telecom" in resource and isinstance(resource["telecom"], list):
                for telecom in resource["telecom"]:
                    if isinstance(telecom, dict) and telecom.get("system") == "phone" and "value" in telecom:
                        return [telecom["value"]]
            return []
        
        # Basic field access for simple paths
        if '.' not in path and '(' not in path:
            if isinstance(resource, dict):
                return [resource.get(path)] if path in resource and resource[path] is not None else []
            return []
            
        # Handle simple paths with dot notation
        parts = path.split('.')
        value = resource
        
        try:
            for i, part in enumerate(parts):
                # Handle functions or complex expressions
                if '(' in part:
                    # Simple implementation of first() function
                    if part == "first()":
                        if isinstance(value, list) and value:
                            return [value[0]]
                        return []
                    
                    # Simplified where() function handling
                    if part.startswith("where(") and part.endswith(")"):
                        if not isinstance(value, list):
                            return []
                            
                        # Extract filter condition (very simplified)
                        filter_expr = part[6:-1]  # Remove where( and )
                        
                        # Handle basic equality filters, e.g., "use='official'"
                        if '=' in filter_expr and ('"' in filter_expr or "'" in filter_expr):
                            # Extract field and value
                            field, quoted_value = filter_expr.split('=', 1)
                            field = field.strip()
                            filter_value = quoted_value.strip().strip("'").strip('"')
                            
                            # Filter the list
                            filtered = []
                            for item in value:
                                if isinstance(item, dict) and field in item and item[field] == filter_value:
                                    filtered.append(item)
                            
                            value = filtered
                        continue
                        
                # Handle normal field access
                if isinstance(value, dict):
                    if part in value:
                        value = value[part]
                    else:
                        return []
                elif isinstance(value, list):
                    next_value = []
                    for item in value:
                        if isinstance(item, dict) and part in item:
                            if isinstance(item[part], list):
                                next_value.extend(item[part])
                            else:
                                next_value.append(item[part])
                    value = next_value
                    if not value:
                        return []
                else:
                    return []
                    
            # Return result in appropriate format
            if value is None:
                return []
            if not isinstance(value, list):
                return [value]
            return value
        except Exception as e:
            logger.error(f"Error in MockFHIRPath for path '{path}': {e}")
            return []

# Use environment variable to determine if we should force mock mode
FORCE_MOCK_MODE = os.environ.get("USE_MOCK_MODE") == "true"

# Set up logger
logger = logging.getLogger(__name__)

# Try importing real fhirpath library, use mock if not available or if mock mode is forced
if FORCE_MOCK_MODE:
    logger.info("Using MockFHIRPath due to USE_MOCK_MODE environment variable")
    FHIRPathEngine = MockFHIRPath
else:
    try:
        # First try the recommended fhirpathpy library
        try:
            import fhirpathpy
            
            # Create an engine class that wraps fhirpathpy correctly
            class FHIRPathPyEngine:
                def __init__(self):
                    pass
                    
                def evaluate(self, resource, path):
                    logger.debug(f"FHIRPathPyEngine evaluating: {path}")
                    # Convert pydantic model to dict if needed
                    resource_dict = resource
                    if hasattr(resource, "dict") and callable(resource.dict):
                        resource_dict = resource.dict()
                    elif hasattr(resource, "model_dump") and callable(resource.model_dump):
                        resource_dict = resource.model_dump()
                    
                    # Use fhirpathpy.evaluate with the correct API
                    try:
                        result = fhirpathpy.evaluate(resource_dict, path)
                        logger.debug(f"FHIRPathPy result for {path}: {result}")
                        return result if result is not None else []
                    except Exception as e:
                        logger.warning(f"FHIRPathPy evaluation error for path '{path}': {e}")
                        # Try the expression against the original resource if dict conversion failed
                        try:
                            return fhirpathpy.evaluate(resource, path) or []
                        except Exception as e2:
                            logger.error(f"FHIRPathPy fallback evaluation failed: {e2}")
                            return []
                    
            # Use the fhirpathpy engine
            FHIRPathEngine = FHIRPathPyEngine
            logger.info("Successfully loaded fhirpathpy for FHIRPath evaluation")
        except ImportError as e:
            logger.warning(f"Could not import fhirpathpy: {e}, trying alternative libraries...")
            # Try alternative FHIRPath implementations if available (future-proofing)
            raise ImportError("No compatible FHIRPath implementation found")
            
    except Exception as e:
        # Use mock if no real module is available
        logger.warning(f"Using MockFHIRPath due to import error: {e}")
        FHIRPathEngine = MockFHIRPath

class FHIRPathAdapter:
    """
    Adapter for the fhirpath library that provides a compatible API with fhirpathpy.
    This class wraps the new fhirpath library with the same interface as the previous
    implementation to minimize code changes during migration.
    """
    
    @staticmethod
    def evaluate(resource: Any, path: str) -> List[Any]:
        """
        Evaluate a FHIRPath expression against a FHIR resource.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            List of values matching the FHIRPath expression
        """
        if not resource or not path:
            return []
            
        logger.debug(f"FHIRPathAdapter evaluating: {path}")
        
        try:
            # Prepare a FHIR resource object for the fhirpath engine when possible.
            resource_to_use = resource

            if isinstance(resource, dict):
                resource_type = resource.get("resourceType")
                parsed_obj = None

                try:
                    if resource_type == "Patient":
                        parsed_obj = Patient.parse_obj(resource)
                    elif resource_type == "Observation":
                        parsed_obj = Observation.parse_obj(resource)
                    elif resource_type == "Condition":
                        parsed_obj = Condition.parse_obj(resource)
                    elif resource_type == "Encounter":
                        parsed_obj = Encounter.parse_obj(resource)
                except Exception as parse_error:
                    logger.debug(f"Could not parse resource as {resource_type}: {parse_error}")
                    parsed_obj = None

                # Prefer the parsed FHIR model object if parsing succeeded; otherwise use original dict
                resource_to_use = parsed_obj if parsed_obj is not None else resource

            # If the resource is a pydantic model use it directly
            elif hasattr(resource, "model_dump") or hasattr(resource, "dict"):
                resource_to_use = resource

            # Use fhirpath to evaluate the expression
            engine = FHIRPathEngine()
            result = engine.evaluate(resource_to_use, path)
            
            # Ensure consistent return format (fhirpathpy may return differently than fhirpath)
            if result is None:
                return []
            elif not isinstance(result, list):
                return [result]
                
            # Log result for debugging
            logger.debug(f"FHIRPath result for {path}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating FHIRPath '{path}': {e}")
            # Use the mock implementation as a fallback
            try:
                mock_engine = MockFHIRPath()
                mock_result = mock_engine.evaluate(resource, path)
                logger.info(f"Using mock implementation for path: {path}")
                return mock_result
            except Exception as mock_e:
                logger.error(f"Mock implementation also failed: {mock_e}")
                return []
    
    @classmethod
    def extract(cls, resource: Any, path: str) -> List[Any]:
        """
        Extract data from a FHIR resource using a FHIRPath expression.
        Compatible API with FHIRPathExtractor.extract.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            List of values matching the FHIRPath expression
        """
        return cls.evaluate(resource, path)
    
    @classmethod
    def extract_first(cls, resource: Any, path: str, default: Any = None) -> Any:
        """
        Extract the first matching value from a FHIR resource using a FHIRPath expression.
        Compatible API with FHIRPathExtractor.extract_first.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            default: Default value to return if no matches are found
            
        Returns:
            First value matching the FHIRPath expression, or default if none
        """
        results = cls.extract(resource, path)
        if results and len(results) > 0:
            return results[0]
        return default
    
    @classmethod
    def exists(cls, resource: Any, path: str) -> bool:
        """
        Check if a FHIRPath expression has any matches in a FHIR resource.
        Compatible API with FHIRPathExtractor.exists.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            path: FHIRPath expression to evaluate
            
        Returns:
            True if the expression has matches, False otherwise
        """
        results = cls.extract(resource, path)
        return bool(results)
    
    @classmethod
    def extract_with_paths(cls, resource: Any, paths: List[str], default: Any = None) -> Any:
        """
        Try multiple FHIRPath expressions in order until one returns a value.
        Compatible API with FHIRPathExtractor.extract_with_paths.
        
        Args:
            resource: FHIR resource (dictionary or FHIR resource model)
            paths: List of FHIRPath expressions to try
            default: Default value to return if no matches are found
            
        Returns:
            First value from the first path that has matches, or default if none
        """
        for path in paths:
            value = cls.extract_first(resource, path)
            if value is not None:
                return value
        return default 