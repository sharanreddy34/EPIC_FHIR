"""
Integration module for FHIR resource schemas and fhir.resources models.

This module provides a bridge between the dictionary-based schema system and
the fhir.resources model-based system, ensuring compatibility during the transition.
"""

from typing import Any, Dict, List, Optional, Type, Union, cast

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.encounter import Encounter
from fhir.resources.careplan import CarePlan
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.condition import Condition
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.procedure import Procedure
from fhir.resources.immunization import Immunization
from fhir.resources.documentreference import DocumentReference
from fhir.resources.relatedperson import RelatedPerson
from fhir.resources.resource import Resource
from pydantic import ValidationError

import logging

# Import the original schema definitions
from epic_fhir_integration.schemas.fhir import (
    RESOURCE_SCHEMAS,
    FALLBACK_PATHS,
    get_schema_for_resource as get_original_schema,
    get_fallback_paths as get_original_fallback_paths,
)

from epic_fhir_integration.schemas.fhir_resources import (
    RESOURCE_MODELS,
    parse_resource,
    validate_resource,
)

logger = logging.getLogger(__name__)

# Mapping from old schema dictionary keys to fhir.resources model paths
# This helps with transitioning from manually extracting fields to using model attributes
SCHEMA_TO_MODEL_PATHS = {
    "Patient": {
        "id": "id",
        "active": "active",
        "gender": "gender",
        "birthDate": "birthDate",
        "name.family": "name[0].family",
        "name.given": "name[0].given",
        "telecom.phone": "telecom[system=phone].value",
        "telecom.email": "telecom[system=email].value",
        "address.line": "address[0].line",
        "address.city": "address[0].city",
        "address.state": "address[0].state",
        "address.postalCode": "address[0].postalCode",
        "maritalStatus": "maritalStatus.coding[0].display",
    },
    "Observation": {
        "id": "id",
        "status": "status",
        "code": "code.coding[0].code",
        "code.text": "code.text",
        "code.display": "code.coding[0].display",
        "value": "valueQuantity.value",
        "valueQuantity.value": "valueQuantity.value",
        "valueQuantity.unit": "valueQuantity.unit",
        "valueString": "valueString",
        "valueDateTime": "valueDateTime",
        "effectiveDateTime": "effectiveDateTime",
        "category": "category[0].coding[0].code",
    },
    "Encounter": {
        "id": "id",
        "status": "status",
        "class": "class.code",
        "type": "type[0].coding[0].code",
        "period.start": "period.start",
        "period.end": "period.end",
    },
    # Additional mappings can be added as needed for other resource types
}

def get_schema_for_resource(resource_type: str) -> Dict[str, Any]:
    """
    Get the schema for a specific resource type.
    
    This function maintains backward compatibility with the original schema system
    while supporting the transition to fhir.resources models.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        Schema definition for the resource type
        
    Raises:
        ValueError: If no schema is defined for the resource type
    """
    # First check if we have a model for this resource type
    if resource_type not in RESOURCE_MODELS:
        # Fall back to original schema
        return get_original_schema(resource_type)
    
    # For now, still return the original schema
    # Future enhancement: generate a schema from the FHIR resource model
    return get_original_schema(resource_type)

def get_fallback_paths(resource_type: str, field_path: str) -> List[str]:
    """
    Get fallback paths for a field in a resource type.
    
    Maintains backward compatibility with the original fallback path system
    while supporting the transition to fhir.resources models.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        field_path: Path to the field (e.g., "gender", "name.family")
        
    Returns:
        List of fallback paths for the field
    """
    # Use the original fallback paths for now
    return get_original_fallback_paths(resource_type, field_path)

def extract_field_from_model(resource: Resource, field_path: str) -> Any:
    """
    Extract a field value from a FHIR resource model using the original field path notation.
    
    This function provides compatibility with the original field extraction logic,
    translating from the dictionary-style paths to fhir.resources attribute paths.
    
    Args:
        resource: FHIR resource model
        field_path: Original field path in dot notation (e.g., "name.family", "telecom.phone")
        
    Returns:
        The extracted field value or None if not found
    """
    # Get the resource type
    resource_type = resource.model_dump().get('resourceType')
    if not resource_type:
        return None
    
    # Check if we have a mapping for this field path
    if resource_type in SCHEMA_TO_MODEL_PATHS and field_path in SCHEMA_TO_MODEL_PATHS[resource_type]:
        # Convert to model path
        model_path = SCHEMA_TO_MODEL_PATHS[resource_type][field_path]
        
        # Split path by dots
        parts = model_path.split('.')
        
        # Start with the resource
        current = resource
        
        for part in parts:
            # Handle array indexing with filters (e.g., "telecom[system=phone]")
            filter_match = part.find('[') != -1 and part.find('=') != -1
            if filter_match:
                array_name = part[:part.find('[')]
                filter_expr = part[part.find('[')+1:part.find(']')]
                filter_field, filter_value = filter_expr.split('=')
                
                # Get the array
                if not hasattr(current, array_name) or getattr(current, array_name) is None:
                    return None
                
                array = getattr(current, array_name)
                
                # Find the matching item
                match = None
                for item in array:
                    if hasattr(item, filter_field) and getattr(item, filter_field) == filter_value:
                        match = item
                        break
                
                if match is None:
                    return None
                
                current = match
                continue
            
            # Handle array indexing (e.g., "name[0]")
            if part.find('[') != -1 and part.find(']') != -1:
                array_name = part[:part.find('[')]
                index = int(part[part.find('[')+1:part.find(']')])
                
                # Get the array
                if not hasattr(current, array_name) or getattr(current, array_name) is None:
                    return None
                
                array = getattr(current, array_name)
                
                # Check if index is valid
                if not isinstance(array, list) or index >= len(array):
                    return None
                
                current = array[index]
                continue
            
            # Regular attribute access
            if not hasattr(current, part) or getattr(current, part) is None:
                return None
            
            current = getattr(current, part)
        
        return current
    
    # If no mapping exists, try a direct attribute access
    parts = field_path.split('.')
    current = resource
    
    for part in parts:
        # Regular attribute access
        if not hasattr(current, part) or getattr(current, part) is None:
            return None
        
        current = getattr(current, part)
    
    return current

def resource_model_to_dict(resource: Resource, schema: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convert a FHIR resource model to a dictionary using the original schema fields.
    
    This function provides compatibility with code that expects the original
    dictionary structure rather than the fhir.resources model objects.
    
    Args:
        resource: FHIR resource model
        schema: Optional schema to determine which fields to include
        
    Returns:
        Dictionary representation of the resource using original schema fields
    """
    result = {}
    
    # Get resource type
    resource_type = resource.model_dump().get('resourceType')
    if not resource_type:
        return result
    
    # If no schema provided, get it
    if schema is None:
        try:
            schema = get_schema_for_resource(resource_type)
        except ValueError:
            # Just convert the whole model to a dict
            return resource.model_dump(exclude_none=True)
    
    # Extract fields based on schema
    for field, field_schema in schema.items():
        # Skip resourceType field
        if field == "resourceType":
            result["resourceType"] = resource_type
            continue
        
        # Try to extract the field value
        value = extract_field_from_model(resource, field)
        
        # Include non-None values
        if value is not None:
            result[field] = value
    
    return result

def create_model_from_dict(data: Dict[str, Any]) -> Optional[Resource]:
    """
    Create a FHIR resource model from a dictionary.
    
    This is a wrapper around parse_resource that provides detailed error handling
    for debugging purposes.
    
    Args:
        data: Dictionary representation of a FHIR resource
        
    Returns:
        FHIR resource model or None if conversion fails
    """
    try:
        return parse_resource(data)
    except ValidationError as e:
        logger.error(f"Validation error creating model from dict: {e}")
        return None
    except ValueError as e:
        logger.error(f"Value error creating model from dict: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating model from dict: {e}")
        return None 