"""
Data validation utilities for FHIR resources.

This module provides functions for validating FHIR resources against schemas,
checking for data consistency, and generating validation reports.
"""

import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from epic_fhir_integration.schemas.fhir import (RESOURCE_SCHEMAS, VALIDATION_RULES,
                                               get_fallback_paths, get_schema_for_resource)

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """
    Exception raised for FHIR resource validation errors.
    
    Attributes:
        resource_type -- FHIR resource type being validated
        field -- field that failed validation
        message -- explanation of the error
    """
    
    def __init__(self, resource_type: str, field: str, message: str):
        self.resource_type = resource_type
        self.field = field
        self.message = message
        super().__init__(f"{resource_type}.{field}: {message}")

def extract_field_value(resource: Dict[str, Any], field_path: str) -> Any:
    """
    Extract a field value from a FHIR resource using a dot-notation path.
    
    Args:
        resource: FHIR resource dictionary
        field_path: Path to the field (e.g., "name.0.family" or "code.coding.0.code")
        
    Returns:
        Field value or None if not found
    """
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
            
            if array_name not in current or not isinstance(current[array_name], list):
                return None
                
            if array_index >= len(current[array_name]):
                return None
                
            current = current[array_name][array_index]
            continue
            
        # Handle array filter notation
        filter_match = re.match(r'(.+)\[(.+)=(.+)\]$', part)
        if filter_match:
            # Filter notation like "name[use=official]"
            array_name = filter_match.group(1)
            filter_field = filter_match.group(2)
            filter_value = filter_match.group(3)
            
            # Remove quotes from filter value if present
            if filter_value.startswith('"') and filter_value.endswith('"'):
                filter_value = filter_value[1:-1]
            if filter_value.startswith("'") and filter_value.endswith("'"):
                filter_value = filter_value[1:-1]
                
            if array_name not in current or not isinstance(current[array_name], list):
                return None
                
            # Find the first item in the array that matches the filter
            for item in current[array_name]:
                if isinstance(item, dict) and filter_field in item and item[filter_field] == filter_value:
                    current = item
                    break
            else:
                # No matching item found
                return None
                
            continue
            
        # Regular field access
        if part not in current:
            return None
            
        current = current[part]
    
    return current

def validate_field_value(value: Any, field_schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a field value against its schema.
    
    Args:
        value: The value to validate
        field_schema: Schema for the field
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if field_schema.get("required", False) and value is None:
        return False, "Required field is missing"
        
    # If value is None and field is not required, it's valid
    if value is None:
        return True, None
        
    # Check type
    field_type = field_schema.get("type")
    if field_type:
        if field_type == "string" and not isinstance(value, str):
            return False, f"Expected string but got {type(value).__name__}"
        elif field_type == "integer" and not isinstance(value, int):
            # Try to convert to int if it's a string
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            else:
                return False, f"Expected integer but got {type(value).__name__}"
        elif field_type == "decimal" and not isinstance(value, (int, float)):
            # Try to convert to float if it's a string
            if isinstance(value, str) and re.match(r'^-?\d+(\.\d+)?$', value):
                value = float(value)
            else:
                return False, f"Expected decimal but got {type(value).__name__}"
        elif field_type == "boolean" and not isinstance(value, bool):
            # Handle string representations of booleans
            if isinstance(value, str):
                if value.lower() in ("true", "yes", "1"):
                    value = True
                elif value.lower() in ("false", "no", "0"):
                    value = False
                else:
                    return False, f"Expected boolean but got string '{value}'"
            else:
                return False, f"Expected boolean but got {type(value).__name__}"
        elif field_type == "object" and not isinstance(value, dict):
            return False, f"Expected object but got {type(value).__name__}"
        elif field_type == "array" and not isinstance(value, list):
            return False, f"Expected array but got {type(value).__name__}"
    
    # Check validation rules
    validation_type = field_schema.get("validation")
    if validation_type and validation_type in VALIDATION_RULES:
        rules = VALIDATION_RULES[validation_type]
        
        # Check regex pattern
        if "regex" in rules and isinstance(value, str):
            pattern = rules["regex"]
            if not re.match(pattern, value):
                return False, f"Value '{value}' does not match pattern '{pattern}'"
                
        # Check allowed values
        if "allowed_values" in rules:
            allowed = rules["allowed_values"]
            if value not in allowed:
                return False, f"Value '{value}' is not one of the allowed values: {allowed}"
                
        # Check min/max for dates
        if validation_type == "date" and isinstance(value, str):
            min_date = rules.get("min_value")
            max_date = rules.get("max_value")
            
            if min_date and value < min_date:
                return False, f"Date '{value}' is before minimum date '{min_date}'"
                
            if max_date and value > max_date:
                return False, f"Date '{value}' is after maximum date '{max_date}'"
    
    # If we got here, the field is valid
    return True, None

def validate_resource(resource: Dict[str, Any], resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Validate a FHIR resource against its schema.
    
    Args:
        resource: FHIR resource dictionary
        resource_type: Optional resource type override (if not provided, extracted from resource)
        
    Returns:
        List of validation errors, empty if valid
    """
    # Determine resource type
    if not resource_type:
        resource_type = resource.get("resourceType")
        
    if not resource_type:
        return [{"field": "resourceType", "message": "Resource type is missing"}]
        
    # Get schema for this resource type
    try:
        schema = get_schema_for_resource(resource_type)
    except ValueError:
        return [{"field": "resourceType", "message": f"No schema defined for resource type: {resource_type}"}]
    
    errors = []
    
    # Validate required fields
    for field_name, field_schema in schema.items():
        if field_schema.get("required", False):
            value = extract_field_value(resource, field_name)
            if value is None:
                errors.append({
                    "field": field_name,
                    "message": "Required field is missing"
                })
    
    # Validate all fields that are present
    for field_name, field_schema in schema.items():
        value = extract_field_value(resource, field_name)
        
        if value is not None:
            is_valid, error_message = validate_field_value(value, field_schema)
            if not is_valid:
                errors.append({
                    "field": field_name,
                    "message": error_message,
                    "value": str(value)[:100]  # Truncate long values
                })
    
    return errors

def extract_with_fallback(resource: Dict[str, Any], resource_type: str, field_path: str) -> Any:
    """
    Extract a field value using fallback paths if the primary path fails.
    
    Args:
        resource: FHIR resource dictionary
        resource_type: FHIR resource type
        field_path: Primary path to the field
        
    Returns:
        Field value or None if not found in any path
    """
    # Get fallback paths for this field
    paths = get_fallback_paths(resource_type, field_path)
    
    # Try each path in order
    for path in paths:
        value = extract_field_value(resource, path)
        if value is not None:
            return value
            
    return None

def validate_date_format(date_str: str) -> bool:
    """
    Validate a date string against common formats.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    # List of formats to try
    formats = [
        "%Y-%m-%d",                # ISO 8601 date
        "%Y-%m-%dT%H:%M:%S",       # ISO 8601 datetime
        "%Y-%m-%dT%H:%M:%S.%f",    # ISO 8601 datetime with microseconds
        "%Y-%m-%dT%H:%M:%SZ",      # ISO 8601 UTC datetime
        "%Y-%m-%dT%H:%M:%S.%fZ",   # ISO 8601 UTC datetime with microseconds
        "%Y-%m-%dT%H:%M:%S%z",     # ISO 8601 datetime with timezone
    ]
    
    for fmt in formats:
        try:
            datetime.datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue
            
    return False

def validate_consistency(resources: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Validate consistency across related FHIR resources.
    
    Args:
        resources: Dictionary of resource lists by type
        
    Returns:
        List of consistency errors
    """
    errors = []
    
    # Get the patient resource
    patients = resources.get("Patient", [])
    if not patients:
        errors.append({
            "resource_type": "Patient",
            "message": "No patient resource found"
        })
        return errors
        
    patient = patients[0]
    patient_id = patient.get("id")
    
    # Validate patient references in other resources
    for resource_type, resource_list in resources.items():
        if resource_type == "Patient":
            continue
            
        for resource in resource_list:
            # Check for subject reference to the patient
            subject = resource.get("subject", {})
            if not subject:
                errors.append({
                    "resource_type": resource_type,
                    "resource_id": resource.get("id"),
                    "message": "Missing subject reference to patient"
                })
                continue
                
            reference = subject.get("reference", "")
            if not reference.endswith(f"/{patient_id}") and not reference.endswith(patient_id):
                errors.append({
                    "resource_type": resource_type,
                    "resource_id": resource.get("id"),
                    "message": f"Subject reference '{reference}' does not match patient ID '{patient_id}'"
                })
    
    # Validate date consistency for observations
    observations = resources.get("Observation", [])
    for obs in observations:
        # Extract date from observation
        obs_date = extract_with_fallback(obs, "Observation", "date")
        
        # Validate the date format if present
        if obs_date and isinstance(obs_date, str) and not validate_date_format(obs_date):
            errors.append({
                "resource_type": "Observation",
                "resource_id": obs.get("id"),
                "message": f"Invalid date format: '{obs_date}'"
            })
    
    return errors

def generate_validation_report(
    resources: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Generate a comprehensive validation report for a set of FHIR resources.
    
    Args:
        resources: Dictionary of resource lists by type
        
    Returns:
        Validation report dictionary
    """
    report = {
        "total_resources": sum(len(resource_list) for resource_list in resources.values()),
        "resource_counts": {resource_type: len(resource_list) for resource_type, resource_list in resources.items()},
        "validation_errors": [],
        "consistency_errors": [],
        "completeness": {},
    }
    
    # Validate individual resources
    for resource_type, resource_list in resources.items():
        for resource in resource_list:
            errors = validate_resource(resource, resource_type)
            for error in errors:
                report["validation_errors"].append({
                    "resource_type": resource_type,
                    "resource_id": resource.get("id"),
                    "field": error["field"],
                    "message": error["message"],
                    "value": error.get("value")
                })
    
    # Validate consistency across resources
    report["consistency_errors"] = validate_consistency(resources)
    
    # Calculate completeness metrics
    for resource_type, resource_list in resources.items():
        if resource_type not in RESOURCE_SCHEMAS:
            continue
            
        schema = RESOURCE_SCHEMAS[resource_type]
        required_fields = [field for field, field_schema in schema.items() if field_schema.get("required", False)]
        
        # Track field presence for this resource type
        field_presence = {field: 0 for field in schema.keys()}
        
        for resource in resource_list:
            for field in schema.keys():
                if extract_field_value(resource, field) is not None:
                    field_presence[field] += 1
        
        # Calculate completeness percentages
        if resource_list:
            report["completeness"][resource_type] = {
                "total_resources": len(resource_list),
                "overall_completeness": sum(field_presence.values()) / (len(schema) * len(resource_list)) * 100,
                "required_fields_completeness": sum(field_presence[field] for field in required_fields) / (len(required_fields) * len(resource_list)) * 100 if required_fields else 100,
                "field_completeness": {field: (count / len(resource_list) * 100) for field, count in field_presence.items()}
            }
    
    return report

def suggest_corrections(
    validation_errors: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Generate suggested corrections for validation errors.
    
    Args:
        validation_errors: List of validation errors
        
    Returns:
        Dictionary of suggested corrections by resource ID
    """
    suggestions = {}
    
    for error in validation_errors:
        resource_id = error.get("resource_id")
        if not resource_id:
            continue
            
        # Initialize suggestions for this resource if needed
        if resource_id not in suggestions:
            suggestions[resource_id] = {
                "resource_type": error.get("resource_type"),
                "corrections": []
            }
            
        # Generate suggestion based on error type
        field = error.get("field")
        message = error.get("message", "")
        value = error.get("value")
        
        if "Required field is missing" in message:
            suggestions[resource_id]["corrections"].append({
                "field": field,
                "suggestion": "Add a valid value for this required field",
                "current_value": None,
                "suggested_value": None
            })
        elif "is not one of the allowed values" in message:
            # Extract allowed values from message
            allowed_values_match = re.search(r'allowed values: \[(.*?)\]', message)
            if allowed_values_match:
                allowed_values = allowed_values_match.group(1).split(", ")
                suggested_value = allowed_values[0] if allowed_values else None
                
                suggestions[resource_id]["corrections"].append({
                    "field": field,
                    "suggestion": f"Change to one of the allowed values: {allowed_values}",
                    "current_value": value,
                    "suggested_value": suggested_value
                })
        elif "does not match pattern" in message:
            # For date fields
            if "date" in field.lower() and value:
                # Try to correct date format
                suggestions[resource_id]["corrections"].append({
                    "field": field,
                    "suggestion": "Fix date format to YYYY-MM-DD",
                    "current_value": value,
                    "suggested_value": None
                })
        elif "Expected" in message and "but got" in message:
            # Type mismatch error
            expected_type_match = re.search(r'Expected (\w+)', message)
            if expected_type_match:
                expected_type = expected_type_match.group(1)
                
                suggestions[resource_id]["corrections"].append({
                    "field": field,
                    "suggestion": f"Convert value to {expected_type} type",
                    "current_value": value,
                    "suggested_value": None
                })
    
    return suggestions

def validate_codeable_concept(
    codeable_concept: Dict[str, Any],
    allowed_systems: Optional[List[str]] = None,
    allowed_codes: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a FHIR CodeableConcept structure.
    
    Args:
        codeable_concept: The CodeableConcept to validate
        allowed_systems: Optional list of allowed code systems
        allowed_codes: Optional list of allowed codes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(codeable_concept, dict):
        return False, f"Expected object but got {type(codeable_concept).__name__}"
    
    # Check for coding array or text
    if "coding" not in codeable_concept and "text" not in codeable_concept:
        return False, "CodeableConcept must have either coding or text"
    
    # Validate coding array if present
    if "coding" in codeable_concept:
        coding = codeable_concept["coding"]
        
        if not isinstance(coding, list):
            return False, "Coding must be an array"
            
        if not coding:
            # Empty coding array is valid only if text is present
            if "text" not in codeable_concept or not codeable_concept["text"]:
                return False, "Empty coding array requires text to be present"
        else:
            # Validate each coding entry
            for i, code in enumerate(coding):
                if not isinstance(code, dict):
                    return False, f"Coding[{i}] must be an object"
                    
                # Each coding should have system and code
                if "system" not in code:
                    return False, f"Coding[{i}] missing system"
                    
                if "code" not in code:
                    return False, f"Coding[{i}] missing code"
                    
                # Validate against allowed systems if specified
                if allowed_systems and code.get("system") not in allowed_systems:
                    return False, f"Coding[{i}] system '{code.get('system')}' not in allowed systems: {allowed_systems}"
                    
                # Validate against allowed codes if specified
                if allowed_codes and code.get("code") not in allowed_codes:
                    return False, f"Coding[{i}] code '{code.get('code')}' not in allowed codes: {allowed_codes}"
    
    return True, None

def extract_polymorphic_field_value(
    resource: Dict[str, Any],
    field_base: str
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Extract a value from a polymorphic FHIR field (fields ending with [x]).
    
    FHIR polymorphic fields can have multiple types represented by different properties.
    For example, value[x] could be valueQuantity, valueString, valueDateTime, etc.
    
    Args:
        resource: FHIR resource dictionary
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        
    Returns:
        Tuple of (value, type_suffix) where type_suffix is the type indicator (e.g., "Quantity")
    """
    # Create regex pattern to match all variations of the field
    pattern = re.compile(f"^{field_base}([A-Z][a-zA-Z]+)$")
    
    # Find all matching fields in the resource
    matches = []
    for key in resource.keys():
        match = pattern.match(key)
        if match:
            type_suffix = match.group(1)
            matches.append((key, type_suffix))
    
    # Return the first match found, if any
    if matches:
        key, type_suffix = matches[0]
        return resource[key], type_suffix
    
    return None, None

def validate_polymorphic_field(
    resource: Dict[str, Any],
    field_base: str,
    allowed_types: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a polymorphic FHIR field (fields ending with [x]).
    
    Args:
        resource: FHIR resource dictionary
        field_base: Base name of the polymorphic field (e.g., "value" for value[x])
        allowed_types: Optional list of allowed type suffixes (e.g., ["Quantity", "String"])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Extract the polymorphic field value and type
    value, type_suffix = extract_polymorphic_field_value(resource, field_base)
    
    # If no match found, field is missing
    if value is None:
        return False, f"No {field_base}[x] field found"
    
    # Check if the type is allowed
    if allowed_types and type_suffix not in allowed_types:
        return False, f"{field_base}{type_suffix} type not in allowed types: {allowed_types}"
    
    # Validate the specific type
    if type_suffix == "Quantity":
        # Validate Quantity structure
        if not isinstance(value, dict):
            return False, f"{field_base}Quantity must be an object"
            
        if "value" not in value:
            return False, f"{field_base}Quantity missing value"
            
        if "unit" not in value and "code" not in value:
            return False, f"{field_base}Quantity missing unit or code"
            
    elif type_suffix == "CodeableConcept":
        # Use the CodeableConcept validator
        return validate_codeable_concept(value)
        
    elif type_suffix == "String":
        if not isinstance(value, str):
            return False, f"{field_base}String must be a string"
            
    elif type_suffix == "Boolean":
        if not isinstance(value, bool):
            return False, f"{field_base}Boolean must be a boolean"
            
    elif type_suffix == "DateTime":
        if not isinstance(value, str):
            return False, f"{field_base}DateTime must be a string"
            
        # Validate datetime format
        if not validate_date_format(value):
            return False, f"{field_base}DateTime '{value}' has invalid format"
    
    return True, None

def validate_fhir_reference(
    reference: Dict[str, Any],
    allowed_resource_types: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a FHIR Reference structure.
    
    Args:
        reference: The Reference object to validate
        allowed_resource_types: Optional list of allowed resource types
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(reference, dict):
        return False, f"Expected object but got {type(reference).__name__}"
    
    # Check if reference field is present
    if "reference" not in reference:
        return False, "Reference must have a reference field"
    
    reference_value = reference["reference"]
    if not isinstance(reference_value, str):
        return False, f"Reference value must be a string, got {type(reference_value).__name__}"
    
    # Check resource type if allowed_resource_types specified
    if allowed_resource_types:
        # Extract the resource type from the reference value
        # Format could be "ResourceType/id" or just "id"
        resource_type = None
        if "/" in reference_value:
            resource_type = reference_value.split("/")[0]
            
        if resource_type and resource_type not in allowed_resource_types:
            return False, f"Reference resource type '{resource_type}' not in allowed types: {allowed_resource_types}"
    
    return True, None 