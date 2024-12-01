"""
Terminology validation for FHIR resources.

This module provides utilities for validating coded values in FHIR resources
against standard terminology services.
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple, Union, Any

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding

logger = logging.getLogger(__name__)

# Default terminology servers
DEFAULT_TERMINOLOGY_SERVERS = {
    "tx.fhir.org": "https://tx.fhir.org/r4",  # Public FHIR terminology server
    "loinc": "https://fhir.loinc.org",        # LOINC terminology server
    "vsac": "https://cts.nlm.nih.gov/fhir/",  # VSAC terminology server (requires API key)
}

class TerminologyValidator:
    """Validate coded values against terminology servers."""
    
    def __init__(self, terminology_server_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize a new terminology validator.
        
        Args:
            terminology_server_url: URL of the terminology server to use. 
                                   If None, will use tx.fhir.org.
            api_key: API key for terminology server if required (e.g., for VSAC)
        """
        self.terminology_server_url = terminology_server_url or DEFAULT_TERMINOLOGY_SERVERS["tx.fhir.org"]
        self.api_key = api_key
        
        logger.info(f"Using terminology server at {self.terminology_server_url}")
    
    def validate_code(
        self, 
        code: str, 
        system: str, 
        display: Optional[str] = None,
        version: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate a code against the terminology server.
        
        Args:
            code: The code to validate
            system: The code system (e.g., http://loinc.org)
            display: Optional display name for the code
            version: Optional version of the code system
            
        Returns:
            Tuple of (is_valid, display, details) where:
            - is_valid is a boolean indicating if the code is valid
            - display is the official display for the code if found
            - details is a dictionary with additional information
        """
        try:
            # Prepare request
            params = {
                "code": code,
                "system": system,
            }
            
            if display:
                params["display"] = display
                
            if version:
                params["version"] = version
                
            headers = {}
            if self.api_key:
                headers["apikey"] = self.api_key
            
            # Make the request
            response = requests.get(
                f"{self.terminology_server_url}/CodeSystem/$validate-code",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Terminology server returned status {response.status_code}: {response.text}")
                return False, None, {"error": f"HTTP {response.status_code}: {response.text}"}
            
            # Parse the response
            data = response.json()
            
            if data.get("resourceType") == "OperationOutcome" and "issue" in data:
                # Handle error responses
                issues = [issue.get("diagnostics", "Unknown issue") for issue in data["issue"]]
                logger.warning(f"Terminology validation issues: {issues}")
                return False, None, {"issues": issues}
            
            # Normal response - should have a Parameters resource
            result = {
                "valid": False,
                "display": None,
                "details": {}
            }
            
            if data.get("resourceType") == "Parameters":
                for param in data.get("parameter", []):
                    if param.get("name") == "result" and "valueBoolean" in param:
                        result["valid"] = param["valueBoolean"]
                    elif param.get("name") == "display" and "valueString" in param:
                        result["display"] = param["valueString"]
                    elif param.get("name") == "message" and "valueString" in param:
                        result["details"]["message"] = param["valueString"]
            
            return result["valid"], result["display"], result["details"]
            
        except Exception as e:
            logger.error(f"Error validating code {code} in system {system}: {e}")
            return False, None, {"error": str(e)}
    
    def validate_coding(self, coding: Coding) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate a FHIR Coding object against the terminology server.
        
        Args:
            coding: FHIR Coding object to validate
            
        Returns:
            Tuple of (is_valid, display, details)
        """
        if not coding.system or not coding.code:
            return False, None, {"error": "Missing system or code"}
            
        return self.validate_code(
            code=coding.code,
            system=coding.system,
            display=coding.display,
            version=getattr(coding, "version", None)
        )
    
    def validate_codeable_concept(self, concept: CodeableConcept) -> Dict[str, Any]:
        """
        Validate a FHIR CodeableConcept object against the terminology server.
        
        Args:
            concept: FHIR CodeableConcept object to validate
            
        Returns:
            Dictionary with validation results
        """
        if not concept.coding or len(concept.coding) == 0:
            return {
                "valid": False,
                "message": "No coding elements found"
            }
        
        # Validate each coding
        results = []
        for coding in concept.coding:
            is_valid, display, details = self.validate_coding(coding)
            
            results.append({
                "valid": is_valid,
                "coding": {
                    "system": coding.system,
                    "code": coding.code,
                    "display": coding.display,
                    "version": getattr(coding, "version", None)
                },
                "validated_display": display,
                "details": details
            })
        
        # Overall result is valid if at least one coding is valid
        valid = any(result["valid"] for result in results)
        
        return {
            "valid": valid,
            "text": concept.text,
            "coding_results": results,
            "message": "At least one coding is valid" if valid else "No valid codings found"
        }
    
    def validate_value_set(
        self, 
        code: str, 
        system: str, 
        value_set_url: str,
        display: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate a code against a specific value set.
        
        Args:
            code: The code to validate
            system: The code system
            value_set_url: URL of the value set to validate against
            display: Optional display name
            
        Returns:
            Tuple of (is_valid, display, details)
        """
        try:
            # Prepare request
            params = {
                "code": code,
                "system": system,
                "url": value_set_url
            }
            
            if display:
                params["display"] = display
                
            headers = {}
            if self.api_key:
                headers["apikey"] = self.api_key
            
            # Make the request
            response = requests.get(
                f"{self.terminology_server_url}/ValueSet/$validate-code",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Terminology server returned status {response.status_code}: {response.text}")
                return False, None, {"error": f"HTTP {response.status_code}: {response.text}"}
            
            # Parse the response
            data = response.json()
            
            if data.get("resourceType") == "OperationOutcome" and "issue" in data:
                # Handle error responses
                issues = [issue.get("diagnostics", "Unknown issue") for issue in data["issue"]]
                logger.warning(f"Terminology validation issues: {issues}")
                return False, None, {"issues": issues}
            
            # Normal response
            result = {
                "valid": False,
                "display": None,
                "details": {}
            }
            
            if data.get("resourceType") == "Parameters":
                for param in data.get("parameter", []):
                    if param.get("name") == "result" and "valueBoolean" in param:
                        result["valid"] = param["valueBoolean"]
                    elif param.get("name") == "display" and "valueString" in param:
                        result["display"] = param["valueString"]
                    elif param.get("name") == "message" and "valueString" in param:
                        result["details"]["message"] = param["valueString"]
            
            return result["valid"], result["display"], result["details"]
            
        except Exception as e:
            logger.error(f"Error validating code {code} in system {system} against value set {value_set_url}: {e}")
            return False, None, {"error": str(e)}
    
    def validate_resource_codings(self, resource: Any) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find and validate all coded elements in a FHIR resource.
        
        Args:
            resource: FHIR resource (any resource type)
            
        Returns:
            Dictionary mapping element paths to validation results
        """
        # Convert resource to a dictionary if it's a FHIR resource model
        if hasattr(resource, "model_dump"):
            resource_dict = resource.model_dump()
        elif hasattr(resource, "dict"):
            resource_dict = resource.dict()
        else:
            resource_dict = resource
            
        # Find all CodeableConcept and Coding elements
        results = {}
        self._find_codings_recursive(resource_dict, "", results)
        
        return results
        
    def _find_codings_recursive(self, data: Any, path: str, results: Dict[str, List[Dict[str, Any]]]):
        """
        Recursively find all codings in a data structure.
        
        Args:
            data: Data to search
            path: Current path in the data structure
            results: Dictionary to update with results
        """
        if not data:
            return
            
        if isinstance(data, dict):
            # Check if this is a Coding
            if "system" in data and "code" in data:
                is_valid, display, details = self.validate_code(
                    code=data["code"],
                    system=data["system"],
                    display=data.get("display")
                )
                
                if path not in results:
                    results[path] = []
                    
                results[path].append({
                    "valid": is_valid,
                    "coding": {
                        "system": data["system"],
                        "code": data["code"],
                        "display": data.get("display")
                    },
                    "validated_display": display,
                    "details": details
                })
                
            # Check if this is a CodeableConcept
            elif "coding" in data and isinstance(data["coding"], list):
                for i, coding in enumerate(data["coding"]):
                    if isinstance(coding, dict) and "system" in coding and "code" in coding:
                        is_valid, display, details = self.validate_code(
                            code=coding["code"],
                            system=coding["system"],
                            display=coding.get("display")
                        )
                        
                        coding_path = f"{path}.coding[{i}]"
                        if coding_path not in results:
                            results[coding_path] = []
                            
                        results[coding_path].append({
                            "valid": is_valid,
                            "coding": {
                                "system": coding["system"],
                                "code": coding["code"],
                                "display": coding.get("display")
                            },
                            "validated_display": display,
                            "details": details
                        })
            
            # Recurse into sub-dictionaries
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                self._find_codings_recursive(value, new_path, results)
                
        elif isinstance(data, list):
            # Recurse into arrays
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                self._find_codings_recursive(item, new_path, results) 