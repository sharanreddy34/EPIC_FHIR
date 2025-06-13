"""
Data transformation utilities for FHIR resources.

This module provides functions for transforming FHIR resources 
to structured formats and implementing schema-based mapping.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from epic_fhir_integration.schemas.fhir import get_schema_for_resource, get_fallback_paths
from epic_fhir_integration.utils.validators import extract_field_value, extract_with_fallback
from epic_fhir_integration.utils.fhir_utils import extract_extensions

logger = logging.getLogger(__name__)

def calculate_age(birth_date: str) -> Optional[int]:
    """
    Calculate age from birth date.
    
    Args:
        birth_date: Birth date string in ISO format (YYYY-MM-DD)
        
    Returns:
        Age in years, or None if birth date is invalid
    """
    if not birth_date:
        return None
        
    try:
        # Parse the birth date
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
        
        # Get current date
        today = datetime.now()
        
        # Calculate age
        age = today.year - birth_date_obj.year
        
        # Adjust age if birthday hasn't occurred yet this year
        if (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day):
            age -= 1
            
        return age
    except ValueError as e:
        logger.warning(f"Error calculating age from birth date '{birth_date}': {e}")
        return None

def extract_birth_date(patient: Dict[str, Any]) -> Optional[str]:
    """
    Extract birth date from patient resource with fallback options.
    
    Args:
        patient: Patient resource dictionary
        
    Returns:
        Birth date string in ISO format (YYYY-MM-DD), or None if not found
    """
    # Try primary birthDate field
    birth_date = patient.get("birthDate")
    
    # If not found, try extension
    if not birth_date:
        extensions = patient.get("extension", [])
        for ext in extensions:
            url = ext.get("url", "")
            if "birthDate" in url or "birth-date" in url:
                birth_date = ext.get("valueDate") or ext.get("valueDateTime")
                if birth_date:
                    break
    
    # Clean up and validate format
    if birth_date:
        # Extract date part if it's a dateTime
        if "T" in birth_date:
            birth_date = birth_date.split("T")[0]
            
        # Validate format (YYYY-MM-DD)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
            return birth_date
    
    return None

def extract_gender(patient: Dict[str, Any]) -> Optional[str]:
    """
    Extract gender from patient resource with fallback options.
    
    Args:
        patient: Patient resource dictionary
        
    Returns:
        Gender string (male, female, other, unknown), or None if not found
    """
    # Try primary gender field
    gender = patient.get("gender")
    
    # If not found or invalid, try extension
    if not gender or gender not in ["male", "female", "other", "unknown"]:
        extensions = patient.get("extension", [])
        for ext in extensions:
            url = ext.get("url", "")
            if "gender" in url:
                gender = ext.get("valueCode") or ext.get("valueString")
                if gender:
                    break
                    
        # Still not found, check if it might be in a non-standard field
        if not gender:
            # Sometimes misplaced in communication section
            communication = patient.get("communication", [])
            if communication and isinstance(communication, list) and len(communication) > 0:
                first_comm = communication[0]
                if isinstance(first_comm, dict):
                    lang = first_comm.get("language", {})
                    if isinstance(lang, dict):
                        # This is a common error where gender and language are mixed up
                        text = lang.get("text")
                        if text in ["male", "female", "other", "unknown"]:
                            gender = text
    
    # Normalize gender values
    if gender:
        gender = gender.lower()
        if gender in ["m", "male"]:
            return "male"
        elif gender in ["f", "female"]:
            return "female"
        elif gender in ["o", "other"]:
            return "other"
        else:
            return "unknown"
    
    return None

def extract_language(patient: Dict[str, Any]) -> Optional[str]:
    """
    Extract preferred language from patient resource.
    
    Args:
        patient: Patient resource dictionary
        
    Returns:
        Language code or description, or None if not found
    """
    # Look for language in communication section
    communication = patient.get("communication", [])
    
    if communication and isinstance(communication, list):
        # First check for preferred languages
        for comm in communication:
            if isinstance(comm, dict) and comm.get("preferred") is True:
                language = comm.get("language", {})
                if isinstance(language, dict):
                    # Try different paths to find the language value
                    if "coding" in language and language["coding"]:
                        coding = language["coding"][0]
                        return coding.get("code") or coding.get("display")
                    elif "text" in language:
                        return language["text"]
        
        # If no preferred language, take the first one
        if communication:
            first_comm = communication[0]
            if isinstance(first_comm, dict):
                language = first_comm.get("language", {})
                if isinstance(language, dict):
                    if "coding" in language and language["coding"]:
                        coding = language["coding"][0]
                        return coding.get("code") or coding.get("display")
                    elif "text" in language:
                        return language["text"]
    
    return None

def extract_patient_demographics(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comprehensive demographics from a patient resource.
    
    Args:
        patient: Patient resource dictionary
        
    Returns:
        Dictionary of demographic information
    """
    # Extract patient ID
    patient_id = patient.get("id")
    
    # Extract name components
    name = {}
    name_list = patient.get("name", [])
    if name_list and isinstance(name_list, list):
        official_name = None
        
        # First look for an official name
        for n in name_list:
            if n.get("use") == "official":
                official_name = n
                break
                
        # If no official name, use the first one
        if not official_name and name_list:
            official_name = name_list[0]
            
        if official_name:
            name["family"] = official_name.get("family", "")
            
            given_names = official_name.get("given", [])
            if given_names and isinstance(given_names, list):
                name["given"] = " ".join(given_names)
                
                if len(given_names) > 0:
                    name["first"] = given_names[0]
                if len(given_names) > 1:
                    name["middle"] = " ".join(given_names[1:])
            
            name["text"] = official_name.get("text", "")
            name["prefix"] = " ".join(official_name.get("prefix", []))
            name["suffix"] = " ".join(official_name.get("suffix", []))
    
    # Extract birth date and age
    birth_date = extract_birth_date(patient)
    age = calculate_age(birth_date) if birth_date else None
    
    # Extract gender with fallback
    gender = extract_gender(patient)
    
    # Extract language
    language = extract_language(patient)
    
    # Extract extensions for additional demographics
    extensions = extract_extensions(patient, flatten=True)
    
    # Extract ethnicity and race from extensions
    ethnicity = None
    race = None
    
    if "ethnicity" in extensions:
        ethnicity = extensions["ethnicity"]
    if "race" in extensions:
        race = extensions["race"]
    
    # Extract address
    address = {}
    address_list = patient.get("address", [])
    if address_list and isinstance(address_list, list):
        home_address = None
        
        # First look for a home address
        for addr in address_list:
            if addr.get("use") == "home":
                home_address = addr
                break
                
        # If no home address, use the first one
        if not home_address and address_list:
            home_address = address_list[0]
            
        if home_address:
            address["line"] = home_address.get("text", "")
            
            line_parts = home_address.get("line", [])
            if line_parts and isinstance(line_parts, list):
                address["street"] = "; ".join(line_parts)
                
            address["city"] = home_address.get("city", "")
            address["state"] = home_address.get("state", "")
            address["postalCode"] = home_address.get("postalCode", "")
            address["country"] = home_address.get("country", "")
    
    # Extract contact info
    contact_info = {}
    telecom = patient.get("telecom", [])
    if telecom and isinstance(telecom, list):
        for contact in telecom:
            system = contact.get("system")
            value = contact.get("value")
            use = contact.get("use")
            
            if not system or not value:
                continue
                
            key = f"{system}_{use}" if use else system
            contact_info[key] = value
    
    # Build the complete demographics dictionary
    demographics = {
        "patient_id": patient_id,
        "name": name,
        "birth_date": birth_date,
        "age": age,
        "gender": gender,
        "language": language,
        "ethnicity": ethnicity,
        "race": race,
        "address": address,
        "contact_info": contact_info,
        "active": patient.get("active", True),
    }
    
    return demographics

def transform_patient_to_row(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a patient resource to a flattened row format for CSV generation.
    
    Args:
        patient: Patient resource dictionary
        
    Returns:
        Dictionary with flattened patient data
    """
    # Extract demographics
    demographics = extract_patient_demographics(patient)
    
    # Flatten nested structures
    row = {
        "patient_id": demographics["patient_id"],
        "active": "yes" if demographics["active"] else "no",
        "birth_date": demographics["birth_date"] or "",
        "age": str(demographics["age"]) if demographics["age"] is not None else "",
        "gender": demographics["gender"] or "",
        "language": demographics["language"] or "",
        "ethnicity": demographics["ethnicity"] or "",
        "race": demographics["race"] or "",
    }
    
    # Add name components
    name = demographics["name"]
    row["name_family"] = name.get("family", "")
    row["name_given"] = name.get("given", "")
    row["name_first"] = name.get("first", "")
    row["name_middle"] = name.get("middle", "")
    row["name_prefix"] = name.get("prefix", "")
    row["name_suffix"] = name.get("suffix", "")
    
    # Add address components
    address = demographics["address"]
    row["address_line"] = address.get("line", "")
    row["address_street"] = address.get("street", "")
    row["address_city"] = address.get("city", "")
    row["address_state"] = address.get("state", "")
    row["address_postal_code"] = address.get("postalCode", "")
    row["address_country"] = address.get("country", "")
    
    # Add contact info
    contact_info = demographics["contact_info"]
    row["phone_home"] = contact_info.get("phone_home", "")
    row["phone_mobile"] = contact_info.get("phone_mobile", "")
    row["phone"] = contact_info.get("phone", "")
    row["email"] = contact_info.get("email", "")
    
    # Add data quality metadata
    row["has_birth_date"] = "yes" if demographics["birth_date"] else "no"
    row["has_gender"] = "yes" if demographics["gender"] else "no"
    row["has_address"] = "yes" if any(address.values()) else "no"
    row["has_contact"] = "yes" if any(contact_info.values()) else "no"
    
    return row

def extract_code_display(codeable_concept: Dict[str, Any]) -> Optional[str]:
    """
    Extract display text from a codeable concept.
    
    Args:
        codeable_concept: FHIR CodeableConcept structure
        
    Returns:
        Display text, or None if not found
    """
    # First try the text field for user-friendly description
    text = codeable_concept.get("text")
    if text:
        return text
        
    # If no text, try to get from coding
    coding = codeable_concept.get("coding", [])
    if coding and isinstance(coding, list) and len(coding) > 0:
        first_code = coding[0]
        
        # Prefer display over code
        display = first_code.get("display")
        if display:
            return display
            
        # Fall back to code if no display
        code = first_code.get("code")
        if code:
            return code
    
    return None

def extract_observation_value(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract value from an observation with type detection.
    
    Args:
        observation: FHIR Observation resource
        
    Returns:
        Dictionary with value and metadata
    """
    result = {
        "value": None,
        "unit": None,
        "type": None,
        "text": None
    }
    
    # Check for quantity value
    if "valueQuantity" in observation:
        quantity = observation["valueQuantity"]
        result["value"] = quantity.get("value")
        result["unit"] = quantity.get("unit") or quantity.get("code")
        result["type"] = "quantity"
        
        # Create text representation
        if result["value"] is not None:
            result["text"] = f"{result['value']} {result['unit'] or ''}"
    
    # Check for string value
    elif "valueString" in observation:
        result["value"] = observation["valueString"]
        result["type"] = "string"
        result["text"] = result["value"]
    
    # Check for boolean value
    elif "valueBoolean" in observation:
        result["value"] = observation["valueBoolean"]
        result["type"] = "boolean"
        result["text"] = "Yes" if result["value"] else "No"
    
    # Check for dateTime value
    elif "valueDateTime" in observation:
        result["value"] = observation["valueDateTime"]
        result["type"] = "dateTime"
        result["text"] = result["value"]
    
    # Check for codeable concept
    elif "valueCodeableConcept" in observation:
        concept = observation["valueCodeableConcept"]
        result["value"] = extract_code_display(concept)
        result["type"] = "codeable_concept"
        result["text"] = result["value"]
        
        # Add code system information if available
        coding = concept.get("coding", [])
        if coding and len(coding) > 0:
            first_code = coding[0]
            result["system"] = first_code.get("system")
            result["code"] = first_code.get("code")
    
    # Check for interpretation
    if "interpretation" in observation and observation["interpretation"]:
        interpretation = observation["interpretation"]
        if isinstance(interpretation, list) and len(interpretation) > 0:
            interpretation_text = extract_code_display(interpretation[0])
            if interpretation_text:
                result["interpretation"] = interpretation_text
    
    return result

def extract_observation_data(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comprehensive data from an observation resource.
    
    Args:
        observation: FHIR Observation resource
        
    Returns:
        Dictionary with observation data
    """
    # Extract observation ID
    observation_id = observation.get("id")
    
    # Extract observation code (what was measured)
    code = observation.get("code", {})
    code_text = extract_code_display(code)
    
    # Extract coding information
    code_system = None
    code_value = None
    coding = code.get("coding", [])
    if coding and len(coding) > 0:
        first_code = coding[0]
        code_system = first_code.get("system")
        code_value = first_code.get("code")
    
    # Extract observation value
    value_data = extract_observation_value(observation)
    
    # Extract dates
    effective_date = None
    if "effectiveDateTime" in observation:
        effective_date = observation["effectiveDateTime"]
    elif "effectivePeriod" in observation:
        period = observation["effectivePeriod"]
        effective_date = period.get("start")
    
    issued_date = observation.get("issued")
    
    # Extract status
    status = observation.get("status")
    
    # Extract category
    category_list = observation.get("category", [])
    categories = []
    
    if category_list and isinstance(category_list, list):
        for category in category_list:
            category_text = extract_code_display(category)
            if category_text:
                categories.append(category_text)
    
    # Extract reference ranges
    reference_ranges = []
    range_list = observation.get("referenceRange", [])
    
    if range_list and isinstance(range_list, list):
        for ref_range in range_list:
            range_data = {
                "text": ref_range.get("text", ""),
                "low": None,
                "high": None,
            }
            
            if "low" in ref_range:
                low = ref_range["low"]
                range_data["low"] = {
                    "value": low.get("value"),
                    "unit": low.get("unit") or low.get("code", "")
                }
                
            if "high" in ref_range:
                high = ref_range["high"]
                range_data["high"] = {
                    "value": high.get("value"),
                    "unit": high.get("unit") or high.get("code", "")
                }
            
            # Only add if there's actual range information
            if range_data["text"] or range_data["low"] or range_data["high"]:
                reference_ranges.append(range_data)
    
    # Extract patient reference
    subject = observation.get("subject", {})
    patient_reference = subject.get("reference", "")
    patient_id = None
    
    if patient_reference:
        # Extract patient ID from reference (Patient/123 -> 123)
        parts = patient_reference.split("/")
        if len(parts) == 2 and parts[0] == "Patient":
            patient_id = parts[1]
    
    # Extract extensions
    extensions = extract_extensions(observation, flatten=True)
    
    # Build the complete observation data dictionary
    observation_data = {
        "observation_id": observation_id,
        "patient_id": patient_id,
        "code": {
            "text": code_text,
            "system": code_system,
            "code": code_value
        },
        "value": value_data,
        "effective_date": effective_date,
        "issued_date": issued_date,
        "status": status,
        "categories": categories,
        "reference_ranges": reference_ranges,
        "extensions": extensions
    }
    
    return observation_data

def transform_observation_to_row(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform an observation resource to a flattened row format for CSV generation.
    
    Args:
        observation: FHIR Observation resource
        
    Returns:
        Dictionary with flattened observation data
    """
    # Extract observation data
    observation_data = extract_observation_data(observation)
    
    # Flatten nested structures
    row = {
        "observation_id": observation_data["observation_id"],
        "patient_id": observation_data["patient_id"] or "",
        "code": observation_data["code"]["text"] or "",
        "code_system": observation_data["code"]["system"] or "",
        "code_value": observation_data["code"]["code"] or "",
        "status": observation_data["status"] or "",
        "effective_date": observation_data["effective_date"] or "",
        "issued_date": observation_data["issued_date"] or "",
    }
    
    # Add value information
    value_data = observation_data["value"]
    row["value"] = str(value_data["value"]) if value_data["value"] is not None else ""
    row["value_unit"] = value_data["unit"] or ""
    row["value_type"] = value_data["type"] or ""
    row["display_text"] = value_data["text"] or ""
    
    # Add interpretation if available
    if "interpretation" in value_data:
        row["interpretation"] = value_data["interpretation"]
    
    # Add category information
    categories = observation_data["categories"]
    row["category"] = "; ".join(categories) if categories else ""
    
    # Add reference range information
    ranges = observation_data["reference_ranges"]
    if ranges:
        first_range = ranges[0]
        
        if first_range.get("text"):
            row["reference_range"] = first_range["text"]
        else:
            # Build range string from low/high values
            range_parts = []
            
            if first_range.get("low"):
                low_value = first_range["low"]["value"]
                low_unit = first_range["low"]["unit"]
                range_parts.append(f">= {low_value} {low_unit}")
                
            if first_range.get("high"):
                high_value = first_range["high"]["value"]
                high_unit = first_range["high"]["unit"]
                range_parts.append(f"<= {high_value} {high_unit}")
                
            row["reference_range"] = ", ".join(range_parts)
    
    return row 