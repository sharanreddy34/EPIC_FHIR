"""
Utilities for working with FHIR CodeableConcept data types.

This module provides helper functions for extracting and manipulating 
CodeableConcept elements from FHIR resources.
"""
from typing import Any, Dict, List, Optional, Union


def get_code(
    codeable_concept: Dict[str, Any], 
    system: Optional[str] = None
) -> Optional[str]:
    """
    Extract a code from a CodeableConcept, optionally filtering by system.
    
    Args:
        codeable_concept: A FHIR CodeableConcept object
        system: Optional coding system URI to filter by
        
    Returns:
        The code string if found, None otherwise
    """
    if not codeable_concept or "coding" not in codeable_concept:
        return None
    
    codings = codeable_concept.get("coding", [])
    
    # If system specified, find matching coding
    if system:
        for coding in codings:
            if coding.get("system") == system and "code" in coding:
                return coding["code"]
        return None
    
    # Otherwise return first available code
    for coding in codings:
        if "code" in coding:
            return coding["code"]
    
    return None


def get_display(
    codeable_concept: Dict[str, Any], 
    system: Optional[str] = None
) -> Optional[str]:
    """
    Extract a display text from a CodeableConcept, optionally filtering by system.
    
    Args:
        codeable_concept: A FHIR CodeableConcept object
        system: Optional coding system URI to filter by
        
    Returns:
        The display string if found, None otherwise
    """
    if not codeable_concept:
        return None
    
    # First try to get display from specific coding
    if "coding" in codeable_concept:
        codings = codeable_concept["coding"]
        
        # If system specified, find matching coding
        if system:
            for coding in codings:
                if coding.get("system") == system and "display" in coding:
                    return coding["display"]
        
        # Otherwise use first coding with display
        for coding in codings:
            if "display" in coding:
                return coding["display"]
    
    # Fall back to text
    return codeable_concept.get("text")


def create_codeable_concept(
    code: str, 
    system: str, 
    display: Optional[str] = None, 
    text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a FHIR CodeableConcept object.
    
    Args:
        code: The code value
        system: The coding system URI
        display: Optional display text for the coding
        text: Optional text for the CodeableConcept
        
    Returns:
        A FHIR CodeableConcept object as a dictionary
    """
    result = {"coding": [{"system": system, "code": code}]}
    
    if display:
        result["coding"][0]["display"] = display
    
    if text:
        result["text"] = text
    elif display:
        # Use display as text if text not provided
        result["text"] = display
    
    return result


def find_matching_concepts(
    codeable_concepts: List[Dict[str, Any]], 
    system: str,
    code: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find CodeableConcepts that match a specific system and optional code.
    
    Args:
        codeable_concepts: List of FHIR CodeableConcept objects
        system: The coding system URI to match
        code: Optional code value to match
        
    Returns:
        List of matching CodeableConcept objects
    """
    result = []
    
    for concept in codeable_concepts:
        if not concept or "coding" not in concept:
            continue
            
        for coding in concept.get("coding", []):
            if coding.get("system") == system:
                if code is None or coding.get("code") == code:
                    result.append(concept)
                    break
    
    return result


def has_coding(
    codeable_concept: Dict[str, Any], 
    system: str,
    code: Optional[str] = None
) -> bool:
    """
    Check if a CodeableConcept has a coding with the specified system and optional code.
    
    Args:
        codeable_concept: A FHIR CodeableConcept object
        system: The coding system URI to match
        code: Optional code value to match
        
    Returns:
        True if matching coding found, False otherwise
    """
    if not codeable_concept or "coding" not in codeable_concept:
        return False
        
    for coding in codeable_concept.get("coding", []):
        if coding.get("system") == system:
            if code is None or coding.get("code") == code:
                return True
    
    return False 