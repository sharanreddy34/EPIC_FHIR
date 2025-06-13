"""
FHIR data automatic correction utilities.

This module provides utilities for automatically correcting common errors in FHIR resources,
including date format corrections, code system URL fixes, and reference format corrections.
"""

import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import dateutil.parser
from fhir.resources.resource import Resource

logger = logging.getLogger(__name__)

# Common incorrect code system mappings
CODE_SYSTEM_CORRECTIONS = {
    # Common incorrect URLs
    "http://snomed.info/sct": "http://snomed.info/sct",  # Correct, included for completeness
    "http://www.snomed.org/sct": "http://snomed.info/sct",
    "snomed": "http://snomed.info/sct",
    "snomed-ct": "http://snomed.info/sct",
    "snomedct": "http://snomed.info/sct",
    "http://loinc.org": "http://loinc.org",  # Correct, included for completeness
    "loinc": "http://loinc.org",
    "LOINC": "http://loinc.org",
    "http://hl7.org/fhir/sid/icd-10": "http://hl7.org/fhir/sid/icd-10",  # Correct
    "icd10": "http://hl7.org/fhir/sid/icd-10",
    "ICD-10": "http://hl7.org/fhir/sid/icd-10",
    "http://hl7.org/fhir/sid/icd-9-cm": "http://hl7.org/fhir/sid/icd-9-cm",  # Correct
    "icd9": "http://hl7.org/fhir/sid/icd-9-cm",
    "ICD-9": "http://hl7.org/fhir/sid/icd-9-cm",
    "http://www.nlm.nih.gov/research/umls/rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",  # Correct
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "RxNorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "http://hl7.org/fhir/sid/cvx": "http://hl7.org/fhir/sid/cvx",  # Correct
    "cvx": "http://hl7.org/fhir/sid/cvx",
    "CVX": "http://hl7.org/fhir/sid/cvx",
    "http://unitsofmeasure.org": "http://unitsofmeasure.org",  # Correct
    "ucum": "http://unitsofmeasure.org",
    "UCUM": "http://unitsofmeasure.org",
}

# Common date format patterns
DATE_PATTERNS = [
    # MM/DD/YYYY
    (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", r"\3-\1-\2"),
    # DD/MM/YYYY
    (r"^(\d{1,2})-(\d{1,2})-(\d{4})$", r"\3-\2-\1"),
    # YYYY/MM/DD
    (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", r"\1-\2-\3"),
    # YYYYMMDD
    (r"^(\d{4})(\d{2})(\d{2})$", r"\1-\2-\3"),
    # Remove time component if it's 00:00:00
    (r"^(\d{4}-\d{2}-\d{2})T00:00:00(\.\d+)?(Z|[+-]\d{2}:\d{2})?$", r"\1"),
]

# Reference format patterns
REFERENCE_PATTERNS = [
    # Missing resource type before ID (assumes Patient if not specified)
    (r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$", 
     r"Patient/\1"),
    # ID without leading resource type and slash
    (r"^([A-Za-z]+)([0-9]+)$", r"\1/\2"),
]


def correct_resource(resource: Union[Dict[str, Any], Resource]) -> Tuple[Union[Dict[str, Any], Resource], List[str]]:
    """
    Apply automatic corrections to a FHIR resource.
    
    Args:
        resource: FHIR resource as dictionary or Resource object
        
    Returns:
        Tuple of (corrected_resource, list_of_corrections_made)
    """
    # Convert Resource objects to dictionary for processing
    is_resource_object = isinstance(resource, Resource)
    if is_resource_object:
        if hasattr(resource, "model_dump"):
            resource_dict = resource.model_dump()
        else:
            resource_dict = resource.dict()
    else:
        resource_dict = resource
    
    # Apply corrections
    corrections = []
    corrected_dict = resource_dict.copy()
    
    # Process the resource recursively
    _process_dict(corrected_dict, "", corrections)
    
    # Convert back to Resource object if the input was a Resource
    if is_resource_object:
        try:
            resource_type = corrected_dict.get("resourceType")
            if not resource_type:
                return resource, []
                
            # Import the appropriate resource class
            module_name = resource_type.lower()
            try:
                module = __import__(f"fhir.resources.{module_name}", fromlist=[resource_type])
                resource_class = getattr(module, resource_type)
                
                # Parse the corrected dictionary
                if hasattr(resource_class, "model_validate"):
                    corrected_resource = resource_class.model_validate(corrected_dict)
                else:
                    corrected_resource = resource_class.parse_obj(corrected_dict)
                    
                return corrected_resource, corrections
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not convert corrected resource back to {resource_type} object: {e}")
                return resource, []
        except Exception as e:
            logger.warning(f"Error converting corrected resource back to Resource object: {e}")
            return resource, []
    else:
        return corrected_dict, corrections


def _process_dict(data: Dict[str, Any], path: str, corrections: List[str]) -> None:
    """
    Process a dictionary recursively to apply corrections.
    
    Args:
        data: Dictionary to process
        path: Current path in the resource
        corrections: List to append corrections to
    """
    if not isinstance(data, dict):
        return
    
    for key, value in list(data.items()):  # Use list() to avoid dict changed during iteration
        current_path = f"{path}.{key}" if path else key
        
        # Process nested dictionaries
        if isinstance(value, dict):
            _process_dict(value, current_path, corrections)
            
            # Special handling for Coding elements
            if "system" in value and "code" in value:
                if _correct_coding(value, current_path, corrections):
                    data[key] = value
            
        # Process arrays
        elif isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{current_path}[{i}]"
                if isinstance(item, dict):
                    _process_dict(item, item_path, corrections)
                    
                    # Special handling for Coding elements
                    if "system" in item and "code" in item:
                        if _correct_coding(item, item_path, corrections):
                            value[i] = item
                            
        # Process dates
        elif isinstance(value, str) and ("date" in key.lower() or key.lower() in ["issued", "authored", "recorded"]):
            corrected_date = _correct_date(value)
            if corrected_date != value:
                data[key] = corrected_date
                corrections.append(f"Corrected date format at {current_path}: {value} -> {corrected_date}")
        
        # Process references
        elif isinstance(value, str) and ("reference" == key.lower()):
            corrected_reference = _correct_reference(value)
            if corrected_reference != value:
                data[key] = corrected_reference
                corrections.append(f"Corrected reference format at {current_path}: {value} -> {corrected_reference}")


def _correct_coding(coding: Dict[str, Any], path: str, corrections: List[str]) -> bool:
    """
    Correct a Coding element.
    
    Args:
        coding: Coding dictionary
        path: Path to the coding element
        corrections: List to append corrections to
        
    Returns:
        True if corrections were made, False otherwise
    """
    corrected = False
    
    # Correct code system
    system = coding.get("system")
    if system and system in CODE_SYSTEM_CORRECTIONS:
        corrected_system = CODE_SYSTEM_CORRECTIONS[system]
        if corrected_system != system:
            coding["system"] = corrected_system
            corrections.append(f"Corrected code system at {path}: {system} -> {corrected_system}")
            corrected = True
    
    return corrected


def _correct_date(date_str: str) -> str:
    """
    Correct a date string to ISO format.
    
    Args:
        date_str: Date string to correct
        
    Returns:
        Corrected date string in ISO format
    """
    # First try with regex patterns
    for pattern, replacement in DATE_PATTERNS:
        if re.match(pattern, date_str):
            try:
                corrected = re.sub(pattern, replacement, date_str)
                # Validate the corrected date
                datetime.datetime.fromisoformat(corrected.replace("Z", "+00:00"))
                return corrected
            except ValueError:
                pass
    
    # Try with dateutil parser as a fallback
    try:
        parsed_date = dateutil.parser.parse(date_str)
        # Check if it's just a date or has time component
        if parsed_date.hour == 0 and parsed_date.minute == 0 and parsed_date.second == 0 and parsed_date.microsecond == 0:
            return parsed_date.date().isoformat()
        else:
            return parsed_date.isoformat()
    except (ValueError, dateutil.parser.ParserError):
        # Return the original string if we can't correct it
        return date_str


def _correct_reference(reference: str) -> str:
    """
    Correct a FHIR reference string.
    
    Args:
        reference: Reference string to correct
        
    Returns:
        Corrected reference string
    """
    # Skip URLs and already valid references
    if "://" in reference or "/" in reference:
        return reference
    
    # Try to correct the reference format
    for pattern, replacement in REFERENCE_PATTERNS:
        if re.match(pattern, reference):
            corrected = re.sub(pattern, replacement, reference)
            return corrected
    
    return reference


def suggest_value_corrections(
    resource_type: str, 
    field_path: str, 
    current_value: Any, 
    error_message: str
) -> List[Dict[str, Any]]:
    """
    Suggest corrections for a value based on error message and field.
    
    Args:
        resource_type: Type of FHIR resource
        field_path: Path to the field in the resource
        current_value: Current value of the field
        error_message: Error message from validation
        
    Returns:
        List of suggested corrections as dictionaries with 'value' and 'explanation'
    """
    suggestions = []
    
    # Suggestions for date fields
    if "date" in field_path.lower() or field_path.split(".")[-1].lower() in ["issued", "authored", "recorded"]:
        if isinstance(current_value, str):
            corrected_date = _correct_date(current_value)
            if corrected_date != current_value:
                suggestions.append({
                    "value": corrected_date,
                    "explanation": f"ISO 8601 format: {corrected_date}"
                })
    
    # Suggestions for code system URLs
    if "system" in field_path.lower() and isinstance(current_value, str):
        # Check if the current value might be a code system with incorrect URL
        for wrong_system, corrected_system in CODE_SYSTEM_CORRECTIONS.items():
            if current_value.lower() == wrong_system.lower() or current_value in wrong_system:
                suggestions.append({
                    "value": corrected_system,
                    "explanation": f"Correct system URL: {corrected_system}"
                })
                break
    
    # Suggestions for status fields
    if field_path.endswith(".status") and isinstance(current_value, str):
        # Common status values for different resources
        status_values = {
            "Patient": ["active", "inactive", "unknown"],
            "Observation": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"],
            "Encounter": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"],
            "MedicationRequest": ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"],
            "Condition": ["active", "recurrence", "relapse", "inactive", "remission", "resolved", "unknown"],
        }
        
        # Get the resource type from the field path
        path_parts = field_path.split(".")
        if path_parts[0] in status_values:
            resource_type = path_parts[0]
        
        if resource_type in status_values:
            for status in status_values[resource_type]:
                if status.lower() in current_value.lower() or current_value.lower() in status:
                    suggestions.append({
                        "value": status,
                        "explanation": f"Valid status for {resource_type}: {status}"
                    })
    
    # Suggestions for reference fields
    if field_path.endswith(".reference") and isinstance(current_value, str):
        corrected_reference = _correct_reference(current_value)
        if corrected_reference != current_value:
            suggestions.append({
                "value": corrected_reference,
                "explanation": f"Properly formatted reference: {corrected_reference}"
            })
    
    return suggestions 