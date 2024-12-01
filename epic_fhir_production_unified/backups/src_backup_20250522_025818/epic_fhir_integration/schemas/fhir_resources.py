"""
FHIR resource models using the fhir.resources library.

This module provides integration with the fhir.resources library to replace
custom dictionary-based schemas with standard FHIR models and leverage 
their built-in validation.
"""

from typing import Any, Dict, List, Optional, Type, Union

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

logger = logging.getLogger(__name__)

# Map resource types to corresponding fhir.resources classes
RESOURCE_MODELS = {
    "Patient": Patient,
    "Observation": Observation,
    "Encounter": Encounter,
    "CarePlan": CarePlan, 
    "MedicationRequest": MedicationRequest,
    "Condition": Condition,
    "DiagnosticReport": DiagnosticReport,
    "AllergyIntolerance": AllergyIntolerance,
    "Procedure": Procedure,
    "Immunization": Immunization,
    "DocumentReference": DocumentReference,
    "RelatedPerson": RelatedPerson,
}

def get_resource_model(resource_type: str) -> Type[Resource]:
    """
    Get the appropriate fhir.resources model class for a given resource type.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        The corresponding fhir.resources model class
        
    Raises:
        ValueError: If no model exists for the given resource type
    """
    if resource_type not in RESOURCE_MODELS:
        raise ValueError(f"No model defined for resource type: {resource_type}")
    return RESOURCE_MODELS[resource_type]

def parse_resource(data: Dict[str, Any]) -> Resource:
    """
    Parse a FHIR resource dictionary into the appropriate fhir.resources model.
    
    Args:
        data: FHIR resource as a dictionary
        
    Returns:
        Parsed FHIR resource model
        
    Raises:
        ValueError: If the resource type is missing or unknown
        ValidationError: If the resource data fails validation
    """
    resource_type = data.get("resourceType")
    if not resource_type:
        raise ValueError("Resource missing required 'resourceType' field")
    
    model_class = get_resource_model(resource_type)
    # Using model_validate (Pydantic V2) instead of parse_obj (Pydantic V1)
    return model_class.model_validate(data)

def validate_resource(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate a FHIR resource dictionary using fhir.resources models.
    
    Args:
        data: FHIR resource as a dictionary
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check for resourceType
    resource_type = data.get("resourceType")
    if not resource_type:
        return [{"field": "resourceType", "message": "Resource type is missing"}]
    
    # Check if we have a model for this resource type
    if resource_type not in RESOURCE_MODELS:
        return [{"field": "resourceType", "message": f"No model defined for resource type: {resource_type}"}]
    
    # Try to parse the resource
    try:
        parse_resource(data)
        return []  # No errors
    except ValidationError as e:
        # Convert Pydantic validation errors to our format
        for error in e.errors():
            # Get the field path from the error location
            field_path = ".".join(str(loc) for loc in error["loc"])
            
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error.get("type"),
                "value": str(error.get("input"))[:100]  # Truncate long values
            })
    except Exception as e:
        # Catch other exceptions and add them to errors
        errors.append({
            "field": "unknown",
            "message": str(e),
            "type": "exception",
            "value": str(data)[:100]  # Truncate long values
        })
    
    return errors 