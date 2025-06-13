"""
Patient resource transformations using FHIR resource models.

This module provides functions for transforming Patient resources using
typed FHIR models from fhir.resources instead of dictionaries.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fhir.resources.patient import Patient
from fhir.resources.resource import Resource

from epic_fhir_integration.utils.fhir_resource_utils import extract_nested_attribute
from epic_fhir_integration.schemas.fhir_resource_schemas import (
    extract_field_from_model,
    resource_model_to_dict,
)

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

def extract_birth_date(patient: Patient) -> Optional[str]:
    """
    Extract birth date from patient resource with fallback options.
    
    Args:
        patient: Patient resource model
        
    Returns:
        Birth date string in ISO format (YYYY-MM-DD), or None if not found
    """
    # Try primary birthDate field
    birth_date = patient.birthDate
    
    # If not found, try extension
    if not birth_date and patient.extension:
        for ext in patient.extension:
            url = ext.url if hasattr(ext, 'url') else None
            if url and ("birthDate" in url or "birth-date" in url):
                birth_date = getattr(ext, "valueDate", None) or getattr(ext, "valueDateTime", None)
                if birth_date:
                    break
    
    # Clean up and validate format
    if birth_date:
        # Extract date part if it's a dateTime
        if "T" in birth_date:
            birth_date = birth_date.split("T")[0]
            
        return birth_date
    
    return None

def extract_gender(patient: Patient) -> Optional[str]:
    """
    Extract gender from patient resource with fallback options.
    
    Args:
        patient: Patient resource model
        
    Returns:
        Gender string (male, female, other, unknown), or None if not found
    """
    # With fhir.resources, gender is already validated during parsing
    return patient.gender

def extract_language(patient: Patient) -> Optional[str]:
    """
    Extract preferred language from patient resource.
    
    Args:
        patient: Patient resource model
        
    Returns:
        Language code or description, or None if not found
    """
    # Look for language in communication section
    if not patient.communication:
        return None
    
    # First check for preferred languages
    for comm in patient.communication:
        if comm.preferred:
            language = comm.language
            if language and language.coding and len(language.coding) > 0:
                coding = language.coding[0]
                return coding.code or coding.display
            elif language and language.text:
                return language.text
    
    # If no preferred language, take the first one
    if patient.communication and len(patient.communication) > 0:
        first_comm = patient.communication[0]
        language = first_comm.language
        if language and language.coding and len(language.coding) > 0:
            coding = language.coding[0]
            return coding.code or coding.display
        elif language and language.text:
            return language.text
    
    return None

def extract_patient_demographics(patient: Patient) -> Dict[str, Any]:
    """
    Extract comprehensive demographics from a patient resource.
    
    Args:
        patient: Patient resource model
        
    Returns:
        Dictionary of demographic information
    """
    # Extract patient ID
    patient_id = patient.id
    
    # Extract name components
    name = {}
    if patient.name and len(patient.name) > 0:
        official_name = None
        
        # First look for an official name
        for n in patient.name:
            if n.use == "official":
                official_name = n
                break
                
        # If no official name, use the first one
        if not official_name and patient.name:
            official_name = patient.name[0]
            
        if official_name:
            name["family"] = official_name.family or ""
            
            given_names = official_name.given or []
            if given_names:
                name["given"] = " ".join(given_names)
                
                if len(given_names) > 0:
                    name["first"] = given_names[0]
                if len(given_names) > 1:
                    name["middle"] = " ".join(given_names[1:])
            
            name["text"] = official_name.text or ""
            name["prefix"] = " ".join(official_name.prefix or [])
            name["suffix"] = " ".join(official_name.suffix or [])
    
    # Extract birth date and age
    birth_date = extract_birth_date(patient)
    age = calculate_age(birth_date) if birth_date else None
    
    # Extract gender
    gender = extract_gender(patient)
    
    # Extract language
    language = extract_language(patient)
    
    # Extract ethnicity and race from extensions
    ethnicity = None
    race = None
    
    if patient.extension:
        for ext in patient.extension:
            url = ext.url
            if "ethnicity" in url:
                ethnicity = getattr(ext, "valueString", None)
                if not ethnicity and hasattr(ext, "extension"):
                    for sub_ext in ext.extension:
                        if sub_ext.url == "text" and hasattr(sub_ext, "valueString"):
                            ethnicity = sub_ext.valueString
                            break
            elif "race" in url:
                race = getattr(ext, "valueString", None)
                if not race and hasattr(ext, "extension"):
                    for sub_ext in ext.extension:
                        if sub_ext.url == "text" and hasattr(sub_ext, "valueString"):
                            race = sub_ext.valueString
                            break
    
    # Extract address
    address = {}
    if patient.address and len(patient.address) > 0:
        home_address = None
        
        # First look for a home address
        for addr in patient.address:
            if addr.use == "home":
                home_address = addr
                break
                
        # If no home address, use the first one
        if not home_address and patient.address:
            home_address = patient.address[0]
            
        if home_address:
            address["line"] = home_address.text or ""
            
            line_parts = home_address.line or []
            if line_parts:
                address["street"] = "; ".join(line_parts)
                
            address["city"] = home_address.city or ""
            address["state"] = home_address.state or ""
            address["postalCode"] = home_address.postalCode or ""
            address["country"] = home_address.country or ""
    
    # Extract contact info
    contact_info = {}
    if patient.telecom:
        for contact in patient.telecom:
            system = contact.system
            value = contact.value
            use = contact.use
            
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
        "active": patient.active if hasattr(patient, "active") else True,
    }
    
    return demographics

def transform_patient_to_row(patient: Patient) -> Dict[str, Any]:
    """
    Transform a patient resource to a flattened row format for CSV generation.
    
    Args:
        patient: Patient resource model
        
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

def legacy_transform_patient(patient: Union[Patient, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transform a patient resource to a flattened row format, with support for both
    FHIR resource models and dictionaries (for backward compatibility).
    
    Args:
        patient: Patient resource model or dictionary
        
    Returns:
        Dictionary with flattened patient data
    """
    from epic_fhir_integration.schemas.fhir_resource_schemas import create_model_from_dict
    from epic_fhir_integration.transform.transform_utils import transform_patient_to_row as dict_transform_patient_to_row
    
    # Check if input is a dictionary
    if isinstance(patient, dict):
        # Try to convert to a Patient model
        patient_model = create_model_from_dict(patient)
        
        # If conversion fails, use the legacy dictionary-based transformation
        if patient_model is None:
            return dict_transform_patient_to_row(patient)
        
        # Otherwise, use the model-based transformation
        return transform_patient_to_row(patient_model)
    
    # Input is already a Patient model
    return transform_patient_to_row(patient) 