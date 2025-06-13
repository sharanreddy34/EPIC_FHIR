"""
Utilities for handling CodeableConcept fields in FHIR resources.

This module provides functions for extracting, validating, and normalizing
CodeableConcept fields, which are a common complex type in FHIR resources.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Common code systems used in FHIR resources
CODE_SYSTEMS = {
    "LOINC": "http://loinc.org",
    "SNOMED": "http://snomed.info/sct",
    "RxNorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "ICD-10": "http://hl7.org/fhir/sid/icd-10",
    "ICD-10-CM": "http://hl7.org/fhir/sid/icd-10-cm",
    "CPT": "http://www.ama-assn.org/go/cpt",
    "UCUM": "http://unitsofmeasure.org",
    "HL7 v3 Code System": "http://terminology.hl7.org/CodeSystem",
}

# Mapping of common display values to normalized values
COMMON_TERM_MAPPING = {
    # Gender terms
    "male": "male",
    "m": "male",
    "man": "male",
    "boy": "male",
    "female": "female",
    "f": "female",
    "woman": "female",
    "girl": "female",
    "other": "other",
    "unknown": "unknown",
    
    # Severity terms
    "mild": "mild",
    "light": "mild",
    "moderate": "moderate",
    "medium": "moderate",
    "severe": "severe",
    "high": "severe",
    "critical": "severe",
    
    # Status terms
    "active": "active",
    "completed": "completed",
    "finished": "completed",
    "inactive": "inactive",
    "in progress": "active",
    "in-progress": "active",
    "resolved": "completed",
    "suspended": "inactive",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "entered-in-error": "entered-in-error",
    "error": "entered-in-error",
}

def extract_display(codeable_concept: Dict[str, Any]) -> Optional[str]:
    """
    Extract the most user-friendly display value from a CodeableConcept.
    
    Args:
        codeable_concept: FHIR CodeableConcept structure
        
    Returns:
        Display value, or None if not found
    """
    if not isinstance(codeable_concept, dict):
        return None
        
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

def extract_coding_details(
    codeable_concept: Dict[str, Any],
    preferred_system: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract detailed information from a CodeableConcept.
    
    Args:
        codeable_concept: FHIR CodeableConcept structure
        preferred_system: Optional preferred code system to use
        
    Returns:
        Dictionary with code details or empty dict if not found
    """
    if not isinstance(codeable_concept, dict):
        return {}
        
    result = {
        "display": extract_display(codeable_concept),
        "code": None,
        "system": None,
        "system_name": None,
    }
    
    # No coding, return just the text if available
    coding = codeable_concept.get("coding", [])
    if not coding or not isinstance(coding, list) or len(coding) == 0:
        return result
        
    # If preferred system is specified, look for it
    if preferred_system:
        for code in coding:
            if code.get("system") == preferred_system:
                result["code"] = code.get("code")
                result["system"] = code.get("system")
                result["display"] = code.get("display") or result["display"]
                
                # Get system name from URL
                for name, url in CODE_SYSTEMS.items():
                    if url == preferred_system:
                        result["system_name"] = name
                        break
                        
                return result
    
    # Use the first coding entry
    first_code = coding[0]
    result["code"] = first_code.get("code")
    result["system"] = first_code.get("system")
    result["display"] = first_code.get("display") or result["display"]
    
    # Get system name from URL
    if result["system"]:
        for name, url in CODE_SYSTEMS.items():
            if url == result["system"]:
                result["system_name"] = name
                break
    
    return result

def normalize_value(value: str) -> str:
    """
    Normalize a value to a standardized form.
    
    Args:
        value: Value to normalize
        
    Returns:
        Normalized value
    """
    if not value or not isinstance(value, str):
        return value
        
    # Convert to lowercase for matching
    lower_value = value.lower().strip()
    
    # Check if it's in our mapping
    if lower_value in COMMON_TERM_MAPPING:
        return COMMON_TERM_MAPPING[lower_value]
        
    return value

def code_lookup(
    code: str,
    system: str,
    lookup_table: Dict[Tuple[str, str], str]
) -> Optional[str]:
    """
    Look up a display value for a code and system pair.
    
    Args:
        code: The code value
        system: The code system URL
        lookup_table: Dictionary mapping (system, code) pairs to display values
        
    Returns:
        Display value, or None if not found
    """
    key = (system, code)
    return lookup_table.get(key)

def extract_concepts_from_array(
    concepts: List[Dict[str, Any]],
    preferred_system: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extract detailed information from an array of CodeableConcepts.
    
    Args:
        concepts: List of FHIR CodeableConcept structures
        preferred_system: Optional preferred code system to use
        
    Returns:
        List of dictionaries with code details
    """
    if not concepts or not isinstance(concepts, list):
        return []
        
    results = []
    for concept in concepts:
        details = extract_coding_details(concept, preferred_system)
        if details.get("display") or details.get("code"):
            results.append(details)
            
    return results

def get_code_system_name(system_url: str) -> Optional[str]:
    """
    Get a human-readable name for a code system URL.
    
    Args:
        system_url: Code system URL
        
    Returns:
        Code system name, or None if not recognized
    """
    for name, url in CODE_SYSTEMS.items():
        if url == system_url:
            return name
            
    return None 