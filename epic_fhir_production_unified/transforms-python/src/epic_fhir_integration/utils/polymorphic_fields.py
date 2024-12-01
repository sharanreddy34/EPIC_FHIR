"""
Utilities for handling polymorphic fields in FHIR resources.

This module provides functions for working with FHIR extensions and fields
that can have multiple value types.
"""

from typing import Any, Dict, List, Optional, Union, TypeVar, cast


def extract_extension(
    resource: Dict[str, Any],
    url: str
) -> List[Dict[str, Any]]:
    """
    Extract extensions with a specific URL from a FHIR resource.
    
    Args:
        resource: FHIR resource dictionary
        url: Extension URL to search for
        
    Returns:
        List of matching extension objects
    """
    if not resource or not isinstance(resource, dict):
        return []
    
    extensions = resource.get("extension", [])
    if not extensions:
        return []
    
    return [ext for ext in extensions if ext.get("url") == url]


def extract_extension_value(
    resource: Dict[str, Any],
    url: str,
    default: Any = None
) -> Any:
    """
    Extract the value from the first matching extension in a FHIR resource.
    
    Args:
        resource: FHIR resource dictionary
        url: Extension URL to search for
        default: Default value if extension not found
        
    Returns:
        Value from the extension, or default if not found
    """
    extensions = extract_extension(resource, url)
    if not extensions:
        return default
    
    # Get the first matching extension
    extension = extensions[0]
    
    # Handle value[x] fields - find the first value field
    for key in extension:
        if key.startswith("value") and key != "url":
            return extension[key]
    
    return default


def extract_all_extension_values(
    resource: Dict[str, Any],
    url: str
) -> List[Any]:
    """
    Extract values from all matching extensions in a FHIR resource.
    
    Args:
        resource: FHIR resource dictionary
        url: Extension URL to search for
        
    Returns:
        List of values from matching extensions
    """
    extensions = extract_extension(resource, url)
    if not extensions:
        return []
    
    values = []
    for extension in extensions:
        # Find the value field in each extension
        for key in extension:
            if key.startswith("value") and key != "url":
                values.append(extension[key])
                break
    
    return values


def get_polymorphic_value(
    resource: Dict[str, Any],
    field_base: str,
    default: Any = None
) -> Any:
    """
    Get the value of a polymorphic field from a FHIR resource.
    
    FHIR uses a convention where a field can have multiple types, indicated
    by field_base[Type] naming. This function finds the actual field name
    and returns its value.
    
    Args:
        resource: FHIR resource dictionary
        field_base: Base name of the polymorphic field (e.g., "value" for "valueString")
        default: Default value if no matching field found
        
    Returns:
        Value of the polymorphic field, or default if not found
    """
    if not resource or not isinstance(resource, dict):
        return default
    
    # Look for field names that start with the base name
    for key in resource:
        if key.startswith(field_base) and key != field_base:
            return resource[key]
    
    return default


def create_extension(
    url: str,
    value: Any,
    value_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a FHIR extension object.
    
    Args:
        url: Extension URL
        value: Value for the extension
        value_type: Optional type override (e.g., "String", "Integer")
            If not provided, the type will be inferred from the value
        
    Returns:
        FHIR extension object as a dictionary
    """
    extension = {"url": url}
    
    if value is None:
        return extension
    
    # Determine value type if not specified
    if value_type is None:
        if isinstance(value, bool):
            value_type = "Boolean"
        elif isinstance(value, int):
            value_type = "Integer"
        elif isinstance(value, float):
            value_type = "Decimal"
        elif isinstance(value, str):
            value_type = "String"
        elif isinstance(value, dict):
            value_type = "CodeableConcept" if "coding" in value else "Reference"
        else:
            value_type = "String"
    
    # Set the value using the appropriate field name
    extension[f"value{value_type}"] = value
    
    return extension


def extract_nested_extension(
    resource: Dict[str, Any],
    parent_url: str,
    child_url: str,
    default: Any = None
) -> Any:
    """
    Extract a value from a nested extension.
    
    Args:
        resource: FHIR resource dictionary
        parent_url: URL of the parent extension
        child_url: URL of the child extension
        default: Default value if extension not found
        
    Returns:
        Value from the nested extension, or default if not found
    """
    extensions = extract_extension(resource, parent_url)
    if not extensions:
        return default
    
    parent_ext = extensions[0]
    if "extension" not in parent_ext:
        return default
    
    # Search for child extension in parent's extension array
    child_exts = [
        ext for ext in parent_ext["extension"] 
        if ext.get("url") == child_url
    ]
    
    if not child_exts:
        return default
    
    child_ext = child_exts[0]
    
    # Find the value field in the child extension
    for key in child_ext:
        if key.startswith("value") and key != "url":
            return child_ext[key]
    
    return default 