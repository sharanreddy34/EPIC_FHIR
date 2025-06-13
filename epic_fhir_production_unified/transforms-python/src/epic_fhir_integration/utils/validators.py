"""
Utility functions for validating and extracting data from FHIR resources.

This module provides helpers for safely extracting fields from nested FHIR structures
and validating their values.
"""

from typing import Any, Dict, List, Optional, Union, TypeVar, cast
import datetime
import re

# Type variable for generic functions
T = TypeVar("T")


def extract_field_value(
    data: Dict[str, Any], 
    path: str, 
    default: Optional[T] = None
) -> Union[Any, T]:
    """
    Safely extract a field value from a nested dictionary using a dot-notation path.
    
    Args:
        data: Dictionary to extract from
        path: Dot-notation path to field (e.g., "patient.name[0].given[0]")
        default: Default value to return if field not found
        
    Returns:
        Field value if found, default otherwise
    """
    if data is None:
        return default
    
    # Handle empty path
    if not path:
        return default
    
    parts = path.split(".")
    current = data
    
    for part in parts:
        # Handle array access (e.g., "name[0]")
        array_match = re.match(r"([^\[]+)\[(\d+)\]", part)
        
        if array_match:
            field_name = array_match.group(1)
            index = int(array_match.group(2))
            
            if not isinstance(current, dict) or field_name not in current:
                return default
            
            array_value = current[field_name]
            if not isinstance(array_value, list) or index >= len(array_value):
                return default
            
            current = array_value[index]
        else:
            # Regular field access
            if not isinstance(current, dict) or part not in current:
                return default
            
            current = current[part]
    
    return current


def is_valid_datetime(value: Any) -> bool:
    """
    Check if a value is a valid date/time string in FHIR format.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is a valid FHIR date/time string, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    # FHIR date formats: YYYY, YYYY-MM, YYYY-MM-DD
    # FHIR datetime formats: YYYY-MM-DDThh:mm:ss+zz:zz
    fhir_date_pattern = r"^\d{4}(-\d{2}(-\d{2})?)?$"
    fhir_datetime_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
    
    return bool(re.match(fhir_date_pattern, value) or re.match(fhir_datetime_pattern, value))


def parse_fhir_datetime(
    value: Optional[str],
    default: Optional[datetime.datetime] = None
) -> Optional[datetime.datetime]:
    """
    Parse a FHIR date/time string into a datetime object.
    
    Args:
        value: FHIR date/time string to parse
        default: Default value to return if parsing fails
        
    Returns:
        Datetime object if parsing succeeds, default otherwise
    """
    if not value:
        return default
    
    try:
        # Handle dates without time component (YYYY-MM-DD)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return datetime.datetime.strptime(value, "%Y-%m-%d")
        
        # Handle partial dates (YYYY-MM)
        if re.match(r"^\d{4}-\d{2}$", value):
            return datetime.datetime.strptime(value + "-01", "%Y-%m-%d")
        
        # Handle year only (YYYY)
        if re.match(r"^\d{4}$", value):
            return datetime.datetime.strptime(value + "-01-01", "%Y-%m-%d")
        
        # Handle datetime with timezone
        if "T" in value:
            # Remove fractional seconds for simpler parsing
            value = re.sub(r"(\.\d+)", "", value)
            
            # Check for Z (UTC) timezone
            if value.endswith("Z"):
                dt = datetime.datetime.strptime(value[:-1], "%Y-%m-%dT%H:%M:%S")
                return dt.replace(tzinfo=datetime.timezone.utc)
            
            # Check for +/- timezone offset
            tz_match = re.search(r"([+-])(\d{2}):(\d{2})$", value)
            if tz_match:
                # Remove timezone for initial parsing
                base_dt_str = value[:-6]
                dt = datetime.datetime.strptime(base_dt_str, "%Y-%m-%dT%H:%M:%S")
                
                # Parse and apply timezone
                sign = tz_match.group(1)
                hours = int(tz_match.group(2))
                minutes = int(tz_match.group(3))
                
                offset_seconds = hours * 3600 + minutes * 60
                if sign == "-":
                    offset_seconds = -offset_seconds
                
                return dt.replace(tzinfo=datetime.timezone(datetime.timedelta(seconds=offset_seconds)))
            
            # No timezone specified, parse as-is
            return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        
        # Fallback - try generic parsing
        return datetime.datetime.fromisoformat(value)
    
    except (ValueError, TypeError):
        return default


def extract_resource_id(resource: Dict[str, Any]) -> Optional[str]:
    """
    Extract the ID from a FHIR resource.
    
    Args:
        resource: FHIR resource dictionary
        
    Returns:
        Resource ID if present, None otherwise
    """
    if not resource or not isinstance(resource, dict):
        return None
    
    # Try direct ID field
    if "id" in resource:
        return str(resource["id"])
    
    # Try resourceType and id combined
    resource_type = resource.get("resourceType")
    if resource_type and "id" in resource:
        return f"{resource_type}/{resource['id']}"
    
    # If resource contains 'resource' sub-object (e.g., Bundle entry)
    if "resource" in resource and isinstance(resource["resource"], dict):
        sub_resource = resource["resource"]
        if "id" in sub_resource:
            return str(sub_resource["id"])
    
    return None


def is_valid_fhir_resource_type(resource_type: str) -> bool:
    """
    Check if a string is a valid FHIR resource type.
    
    Args:
        resource_type: Resource type to check
        
    Returns:
        True if valid FHIR resource type, False otherwise
    """
    # List of common FHIR resource types
    valid_types = {
        "Patient", "Practitioner", "Organization", "Encounter", "Observation",
        "Condition", "Procedure", "MedicationRequest", "AllergyIntolerance",
        "DiagnosticReport", "DocumentReference", "Immunization", "CarePlan",
        "Goal", "Device", "Location", "Bundle", "OperationOutcome", "Parameters",
        "ValueSet", "CodeSystem", "Questionnaire", "QuestionnaireResponse", "Task"
    }
    
    return resource_type in valid_types 