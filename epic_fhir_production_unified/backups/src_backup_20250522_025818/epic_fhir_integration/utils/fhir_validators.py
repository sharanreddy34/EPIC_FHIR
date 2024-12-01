"""
FHIR resource validators for fhir.resources objects.

This module provides validation utilities that work directly with 
fhir.resources model objects rather than dictionaries.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union, Type

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.resource import Resource
from fhir.resources.patient import Patient

logger = logging.getLogger(__name__)

def validate_codeable_concept(
    codeable_concept: CodeableConcept,
    allowed_systems: Optional[List[str]] = None,
    allowed_codes: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a FHIR CodeableConcept structure using fhir.resources model.
    
    Args:
        codeable_concept: The CodeableConcept object to validate
        allowed_systems: Optional list of allowed code systems
        allowed_codes: Optional list of allowed codes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(codeable_concept, CodeableConcept):
        return False, f"Expected CodeableConcept but got {type(codeable_concept).__name__}"
    
    # Check for coding array or text
    has_coding = codeable_concept.coding and len(codeable_concept.coding) > 0
    has_text = codeable_concept.text is not None and codeable_concept.text != ""
    
    if not has_coding and not has_text:
        return False, "CodeableConcept must have either coding or text"
    
    # Validate coding array if present
    if has_coding:
        # Validate each coding entry
        for i, code in enumerate(codeable_concept.coding):
            # Each coding should have system and code
            if not code.system:
                return False, f"Coding[{i}] missing system"
                
            if not code.code:
                return False, f"Coding[{i}] missing code"
                
            # Validate against allowed systems if specified
            if allowed_systems and code.system not in allowed_systems:
                return False, f"Coding[{i}] system '{code.system}' not in allowed systems: {allowed_systems}"
                
            # Validate against allowed codes if specified
            if allowed_codes and code.code not in allowed_codes:
                return False, f"Coding[{i}] code '{code.code}' not in allowed codes: {allowed_codes}"
    
    return True, None

def validate_polymorphic_field(
    resource: Resource,
    field_base: str,
    allowed_types: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a polymorphic FHIR field in a fhir.resources model.
    
    Args:
        resource: FHIR resource object
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        allowed_types: Optional list of allowed type suffixes (e.g., ["Quantity", "String"])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get all attributes of the resource
    resource_dict = resource.model_dump()
    
    # Pattern to match polymorphic fields 
    pattern = re.compile(f"^{field_base}([A-Z][a-zA-Z]+)$")
    
    # Find all matching fields
    matches = []
    for key in resource_dict.keys():
        match = pattern.match(key)
        if match:
            type_suffix = match.group(1)
            matches.append((key, type_suffix))
    
    # If no match found, field is missing
    if not matches:
        return False, f"No {field_base}[x] field found"
    
    # Get the first match
    field_name, type_suffix = matches[0]
    
    # Check if the type is allowed
    if allowed_types and type_suffix not in allowed_types:
        return False, f"{field_base}{type_suffix} type not in allowed types: {allowed_types}"
    
    # Get the field value using getattr
    value = getattr(resource, field_name)
    
    # Field exists and type is allowed, so it's valid
    # Note: Detailed type validation is handled by Pydantic in fhir.resources
    return True, None

def validate_fhir_reference(
    reference: Reference,
    allowed_resource_types: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a FHIR Reference structure using fhir.resources model.
    
    Args:
        reference: The Reference object to validate
        allowed_resource_types: Optional list of allowed resource types
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(reference, Reference):
        return False, f"Expected Reference but got {type(reference).__name__}"
    
    # Check if reference field is present
    if not reference.reference:
        return False, "Reference must have a reference field"
    
    # Check resource type if allowed_resource_types specified
    if allowed_resource_types:
        # Extract the resource type from the reference value
        # Format could be "ResourceType/id" or just "id"
        resource_type = None
        if "/" in reference.reference:
            resource_type = reference.reference.split("/")[0]
            
        if resource_type and resource_type not in allowed_resource_types:
            return False, f"Reference resource type '{resource_type}' not in allowed types: {allowed_resource_types}"
    
    return True, None

def extract_field_value_from_resource(resource: Resource, field_path: str) -> Any:
    """
    Extract a field value from a FHIR resource using a dot-notation path.
    
    Args:
        resource: FHIR resource object
        field_path: Path to the field (e.g., "name.0.family" or "code.coding.0.code")
        
    Returns:
        Field value or None if not found
    """
    # If resource is None, return None
    if resource is None:
        return None
        
    # Split path by dots
    parts = field_path.split('.')
    
    # Start with the whole resource
    current = resource
    
    for part in parts:
        # Handle array indexing
        array_match = re.match(r'(.+)\[(\d+)\]$', part)
        if array_match:
            # Array index notation like "name[0]"
            array_name = array_match.group(1)
            array_index = int(array_match.group(2))
            
            # Get the array attribute
            array_attr = getattr(current, array_name, None)
            if array_attr is None or not isinstance(array_attr, list):
                return None
                
            if array_index >= len(array_attr):
                return None
                
            current = array_attr[array_index]
            continue
        
        # Regular attribute access
        try:
            current = getattr(current, part, None)
            if current is None:
                return None
        except (AttributeError, TypeError):
            return None
    
    return current 