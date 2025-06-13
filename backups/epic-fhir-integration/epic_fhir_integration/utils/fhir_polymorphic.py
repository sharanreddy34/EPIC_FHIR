"""
Utilities for handling polymorphic fields in FHIR resources using fhir.resources models.

This module provides functions for extracting, validating, and transforming
polymorphic fields (such as value[x]) in FHIR resource objects from the fhir.resources library.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from fhir.resources.resource import Resource
from fhir.resources.quantity import Quantity
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.range import Range
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.procedure import Procedure

# Common polymorphic fields in FHIR resources
COMMON_POLYMORPHIC_FIELDS = {
    "Observation": ["value", "effective"],
    "Condition": ["onset", "abatement"],
    "Procedure": ["performed"],
    "MedicationRequest": ["reported", "medication"],
    "DiagnosticReport": ["effective"],
    "AllergyIntolerance": ["onset"],
}

# Mapping of type suffix to simpler type name
TYPE_SUFFIX_MAP = {
    "Quantity": "quantity",
    "DateTime": "dateTime",
    "Period": "period",
    "String": "string",
    "Boolean": "boolean",
    "CodeableConcept": "codeableConcept",
    "Range": "range",
    "Ratio": "ratio",
    "SampledData": "sampledData",
    "Time": "time",
    "Reference": "reference",
    "Integer": "integer",
    "Age": "age",
    "Attachment": "attachment",
    "Identifier": "identifier",
    "Timing": "timing",
}

def identify_polymorphic_fields(resource: Resource) -> List[str]:
    """
    Identify all polymorphic fields present in a FHIR resource.
    
    Args:
        resource: FHIR resource object
        
    Returns:
        List of base names for polymorphic fields found in the resource
    """
    # Get resource type 
    resource_type = resource.resource_type
    
    if resource_type not in COMMON_POLYMORPHIC_FIELDS:
        return []
        
    # Get common polymorphic fields for this resource type
    potential_fields = COMMON_POLYMORPHIC_FIELDS[resource_type]
    
    # Convert resource to dictionary to check for field patterns
    resource_dict = resource.model_dump()
    
    # Find which ones are actually present
    found_fields = []
    for field_base in potential_fields:
        pattern = re.compile(f"^{field_base}([A-Z][a-zA-Z]+)$")
        for key in resource_dict.keys():
            if pattern.match(key):
                found_fields.append(field_base)
                break
                
    return found_fields

def extract_polymorphic_field(resource: Resource, field_base: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Extract a value from a polymorphic FHIR field.
    
    Args:
        resource: FHIR resource object
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        
    Returns:
        Tuple of (value, type_suffix) where type_suffix is the type indicator (e.g., "Quantity")
    """
    # Convert resource to dictionary to check for field patterns
    resource_dict = resource.model_dump()
    
    pattern = re.compile(f"^{field_base}([A-Z][a-zA-Z]+)$")
    
    # Find all matching fields
    matches = []
    for key in resource_dict.keys():
        match = pattern.match(key)
        if match:
            type_suffix = match.group(1)
            matches.append((key, type_suffix))
    
    # Return the first match found, if any
    if matches:
        key, type_suffix = matches[0]
        return getattr(resource, key), type_suffix
    
    return None, None

def get_normalized_type(type_suffix: str) -> str:
    """
    Get a normalized type name from a type suffix.
    
    Args:
        type_suffix: Type suffix from a polymorphic field (e.g., "Quantity")
        
    Returns:
        Normalized type name (e.g., "quantity")
    """
    return TYPE_SUFFIX_MAP.get(type_suffix, type_suffix.lower())

def extract_value_from_polymorphic(resource: Resource, field_base: str) -> Dict[str, Any]:
    """
    Extract a structured value from a polymorphic field.
    
    Args:
        resource: FHIR resource object
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        
    Returns:
        Dictionary with structured value information or empty dict if not found
    """
    value, type_suffix = extract_polymorphic_field(resource, field_base)
    
    if value is None or type_suffix is None:
        return {}
        
    result = {
        "type": get_normalized_type(type_suffix),
        "value": None,
        "raw": value,
    }
    
    # Extract the actual value based on the type
    if type_suffix == "Quantity" and isinstance(value, Quantity):
        result["value"] = value.value
        result["unit"] = value.unit or value.code
        result["system"] = value.system
        result["display"] = f"{result['value']} {result['unit'] or ''}"
        
    elif type_suffix == "CodeableConcept" and isinstance(value, CodeableConcept):
        if value.coding and len(value.coding) > 0:
            code = value.coding[0]
            result["code"] = code.code
            result["system"] = code.system
            result["display"] = code.display or value.text or ""
        else:
            result["display"] = value.text or ""
        result["value"] = result["display"]
        
    elif type_suffix == "String":
        result["value"] = value
        result["display"] = value
        
    elif type_suffix == "Boolean":
        result["value"] = value
        result["display"] = "Yes" if value else "No"
        
    elif type_suffix == "DateTime":
        result["value"] = value
        result["display"] = value
        
    elif type_suffix == "Period" and isinstance(value, Period):
        result["start"] = value.start
        result["end"] = value.end
        result["value"] = result["start"]
        result["display"] = f"{result['start']} to {result['end']}" if result["end"] else result["start"]
        
    elif type_suffix == "Reference" and isinstance(value, Reference):
        result["reference"] = value.reference
        result["display"] = value.display or result["reference"] or ""
        result["value"] = result["reference"]
        
    return result

def get_preferred_extraction_type(field_base: str, resource_type: str) -> List[str]:
    """
    Get the preferred extraction types for a polymorphic field.
    
    Args:
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        resource_type: FHIR resource type
        
    Returns:
        List of type suffixes in preference order
    """
    # Define preferred extraction types for common fields
    if field_base == "value" and resource_type == "Observation":
        return ["Quantity", "String", "CodeableConcept", "Boolean", "DateTime"]
        
    elif field_base == "effective" and resource_type in ["Observation", "DiagnosticReport"]:
        return ["DateTime", "Period"]
        
    elif field_base == "onset" and resource_type == "Condition":
        return ["DateTime", "Period", "Age", "Range", "String"]
        
    elif field_base == "performed" and resource_type == "Procedure":
        return ["DateTime", "Period", "String", "Age", "Range"]
        
    elif field_base == "medication" and resource_type == "MedicationRequest":
        return ["CodeableConcept", "Reference"]
        
    # Default to common types in a reasonable order
    return ["String", "CodeableConcept", "Quantity", "DateTime", "Period", "Boolean", "Reference"]

def extract_best_polymorphic_value(resource: Resource, field_base: str) -> Any:
    """
    Extract the best value from a polymorphic field based on resource type.
    
    This function tries to extract the most useful representation of a polymorphic
    field's value based on context and resource type.
    
    Args:
        resource: FHIR resource object
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        
    Returns:
        Extracted value in the most appropriate form, or None if not found
    """
    # Get the structured value information
    value_info = extract_value_from_polymorphic(resource, field_base)
    if not value_info:
        return None
        
    # For most use cases, return the display or value
    return value_info.get("display") or value_info.get("value") 