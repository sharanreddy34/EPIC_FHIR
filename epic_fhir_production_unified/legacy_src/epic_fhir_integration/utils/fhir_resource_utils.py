"""
Utilities for working with FHIR resources models.

This module provides helper functions for working with the fhir.resources library,
extracting data from FHIR resource models, and supporting the transition from
dictionary-based schemas to typed FHIR models.
"""

import logging
from typing import Any, Dict, List, Optional, Type, Union, cast, get_type_hints

from fhir.resources.resource import Resource
from pydantic import ValidationError

from epic_fhir_integration.schemas.fhir_resources import RESOURCE_MODELS, get_resource_model, parse_resource

logger = logging.getLogger(__name__)

def extract_nested_attribute(resource: Resource, attribute_path: str) -> Any:
    """
    Extract a nested attribute from a FHIR resource model using dot notation.
    
    This provides similar functionality to the extract_field_value function but works
    with fhir.resources model objects rather than dictionaries.
    
    Args:
        resource: FHIR resource model
        attribute_path: Path to the attribute using dot notation (e.g., "name.0.family")
        
    Returns:
        The extracted attribute value or None if not found
    """
    # Split path by dots
    parts = attribute_path.split('.')
    
    # Start with the resource
    current: Any = resource
    
    for part in parts:
        # Handle array indexing (e.g., "name.0.family")
        if part.isdigit():
            index = int(part)
            # Ensure current is a list and index is valid
            if isinstance(current, list) and 0 <= index < len(current):
                current = current[index]
            else:
                return None
        else:
            # Regular attribute access
            if not hasattr(current, part):
                return None
            current = getattr(current, part)
            
            # Handle None
            if current is None:
                return None
    
    return current

def resource_to_dict(resource: Resource) -> Dict[str, Any]:
    """
    Convert a FHIR resource model to a dictionary.
    
    Args:
        resource: FHIR resource model
        
    Returns:
        Dictionary representation of the resource
    """
    # Using model_dump (Pydantic V2) instead of dict (Pydantic V1)
    return resource.model_dump(exclude_none=True)

def resource_to_json(resource: Resource, indent: int = None) -> str:
    """
    Convert a FHIR resource model to a JSON string.
    
    Args:
        resource: FHIR resource model
        indent: Optional indentation level for pretty-printing
        
    Returns:
        JSON string representation of the resource
    """
    # Using model_dump_json (Pydantic V2)
    return resource.model_dump_json(indent=indent, exclude_none=True)

def dict_to_resource(data: Dict[str, Any]) -> Optional[Resource]:
    """
    Convert a dictionary to a FHIR resource model, handling validation errors.
    
    Args:
        data: Dictionary representation of the resource
        
    Returns:
        FHIR resource model or None if conversion fails
    """
    try:
        return parse_resource(data)
    except (ValueError, ValidationError) as e:
        logger.error(f"Failed to convert dictionary to FHIR resource: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error converting dictionary to FHIR resource: {e}")
        return None

def get_extension_by_url(resource: Resource, url: str) -> Optional[Dict[str, Any]]:
    """
    Get a FHIR extension from a resource by its URL.
    
    Args:
        resource: FHIR resource model
        url: Extension URL to find
        
    Returns:
        The extension as a dictionary or None if not found
    """
    # Check if the resource has extensions
    if not hasattr(resource, "extension") or not resource.extension:
        return None
        
    # Find the extension with matching URL
    for ext in resource.extension:
        if ext.url == url:
            return resource_to_dict(ext)
            
    return None

def get_coding_from_codeable_concept(cc: Any, system: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Extract a coding from a CodeableConcept based on the system.
    
    Args:
        cc: CodeableConcept from a FHIR resource
        system: Optional coding system to filter by
        
    Returns:
        The first matching coding as a dictionary or None if not found
    """
    if cc is None or not hasattr(cc, "coding") or not cc.coding:
        return None
        
    # If no system specified, return first coding
    if system is None and cc.coding:
        return resource_to_dict(cc.coding[0])
        
    # Find coding with matching system
    for coding in cc.coding:
        if coding.system == system:
            return resource_to_dict(coding)
            
    return None

def extract_identifier(resource: Resource, system: Optional[str] = None) -> Optional[str]:
    """
    Extract an identifier value from a FHIR resource.
    
    Args:
        resource: FHIR resource model
        system: Optional identifier system to filter by
        
    Returns:
        The identifier value or None if not found
    """
    if not hasattr(resource, "identifier") or not resource.identifier:
        return None
        
    # If no system specified, return first identifier value
    if system is None and resource.identifier:
        return resource.identifier[0].value
        
    # Find identifier with matching system
    for identifier in resource.identifier:
        if identifier.system == system:
            return identifier.value
            
    return None

def is_resource_model(obj: Any) -> bool:
    """
    Check if an object is a FHIR resource model.
    
    Args:
        obj: Object to check
        
    Returns:
        True if the object is a FHIR resource model, False otherwise
    """
    # Check types and inheritance
    return isinstance(obj, Resource)

def ensure_resource_model(obj: Union[Resource, Dict[str, Any]], resource_type: Optional[str] = None) -> Optional[Resource]:
    """
    Ensure an object is a FHIR resource model, converting it if necessary.
    
    Args:
        obj: Object to check/convert (either a Resource or dict)
        resource_type: Optional resource type override
        
    Returns:
        FHIR resource model or None if conversion fails
    """
    # If already a resource model, return it
    if is_resource_model(obj):
        return cast(Resource, obj)
        
    # If it's a dictionary, try to convert it
    if isinstance(obj, dict):
        # Override resource type if specified
        if resource_type:
            obj = obj.copy()
            obj["resourceType"] = resource_type
            
        return dict_to_resource(obj)
        
    return None 