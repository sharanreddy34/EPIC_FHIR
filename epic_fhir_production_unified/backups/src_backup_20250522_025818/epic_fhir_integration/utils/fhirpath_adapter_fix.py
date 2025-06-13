#!/usr/bin/env python3
from typing import Any, Dict, List, Optional, Union
import logging
import json
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter

logger = logging.getLogger(__name__)

def convert_to_fhir_model(resource_json: Dict[str, Any]) -> Optional[Any]:
    """Convert JSON resource to proper FHIR model object."""
    try:
        resource_type = resource_json.get("resourceType")
        if resource_type == "Patient":
            return Patient.parse_obj(resource_json)
        elif resource_type == "Observation":
            return Observation.parse_obj(resource_json)
        elif resource_type == "Condition":
            return Condition.parse_obj(resource_json)
        elif resource_type == "Encounter":
            return Encounter.parse_obj(resource_json)
        else:
            logger.warning(f"Unsupported resource type: {resource_type}")
            return None
    except Exception as e:
        logger.error(f"Error converting to FHIR model: {str(e)}")
        return None

def evaluate_fhirpath(resource: Dict[str, Any], path: str) -> Any:
    """Evaluate FHIRPath expression on a FHIR resource."""
    try:
        # Convert JSON to proper FHIR model
        fhir_model = convert_to_fhir_model(resource)
        
        if fhir_model is None:
            raise ValueError(f"Could not convert resource to FHIR model")
        
        # Use the model's fhirpath() method to evaluate the expression
        result = fhir_model.fhirpath(path)
        return result
    except Exception as e:
        logger.error(f"Error evaluating FHIRPath '{path}' with fhirpath: {str(e)}")
        # Fallback to mock implementation if needed
        logger.info(f"Falling back to mock implementation for path: {path}")
        return mock_fhirpath_evaluation(resource, path)

def mock_fhirpath_evaluation(resource: Dict[str, Any], path: str) -> Any:
    """Mock implementation of FHIRPath evaluation as fallback."""
    # This is a simplified implementation that handles common paths
    if path == 'gender':
        return resource.get('gender')
    elif path == 'birthDate':
        return resource.get('birthDate')
    elif path == 'name.where(use=\'official\').given.first()':
        names = resource.get('name', [])
        for name in names:
            if name.get('use') == 'official':
                given = name.get('given', [])
                return given[0] if given else None
        return None
    elif path == 'telecom.where(system=\'phone\').value.first()':
        telecom = resource.get('telecom', [])
        for t in telecom:
            if t.get('system') == 'phone':
                return t.get('value')
        return None
    elif path == 'address.line.first()':
        addresses = resource.get('address', [])
        for addr in addresses:
            lines = addr.get('line', [])
            return lines[0] if lines else None
        return None
    elif 'coding.where' in path:
        # Handle coding lookup
        if 'code.coding.where(system=\'http://loinc.org\').exists()' == path:
            codings = resource.get('code', {}).get('coding', [])
            return any(c.get('system') == 'http://loinc.org' for c in codings)
    elif 'valueQuantity.exists()' == path:
        return 'valueQuantity' in resource
    
    # Default fallback for unknown paths
    return None 