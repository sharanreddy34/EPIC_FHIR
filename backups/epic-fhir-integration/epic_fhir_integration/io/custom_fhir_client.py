"""
Custom FHIR client for Epic FHIR API integration using the custom auth module.
"""

import logging
from typing import Any, Dict, Generator, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from epic_fhir_integration.auth.custom_auth import get_token
from epic_fhir_integration.io.fhir_client import FHIRClient

logger = logging.getLogger(__name__)

# Resource-specific parameter maps for different FHIR resources
RESOURCE_PARAMETERS = {
    "Observation": {
        "default": {"_count": 50},
        "date_filter": {"date": "ge2010-01-01"},
        "vital_signs": {"category": "vital-signs"},
        "laboratory": {"category": "laboratory"},
        "all_categories": {},  # No category filter to get all
    },
    "CarePlan": {
        "default": {"_count": 50},
        "active": {"status": "active"},
        "completed": {"status": "completed"},
        "draft": {"status": "draft"},
        "all_statuses": {"status": "active,completed,draft"},
    },
    "MedicationRequest": {
        "default": {"_count": 50},
        "active": {"status": "active"},
        "completed": {"status": "completed"},
    },
    "Condition": {
        "default": {"_count": 50},
        "active": {"clinical-status": "active"},
        "confirmed": {"verification-status": "confirmed"},
    },
    "DiagnosticReport": {
        "default": {"_count": 50},
        "recent": {"date": "ge2020-01-01"},
    },
    "AllergyIntolerance": {
        "default": {"_count": 50},
        "active": {"clinical-status": "active"},
    },
    "Procedure": {
        "default": {"_count": 50},
        "completed": {"status": "completed"},
    },
    "Immunization": {
        "default": {"_count": 50},
        "completed": {"status": "completed"},
    },
    "DocumentReference": {
        "default": {"_count": 50},
        "clinical_notes": {"category": "clinical-note"},
    },
    "RelatedPerson": {
        "default": {"_count": 20},
    },
    "Encounter": {
        "default": {"_count": 50},
        "inpatient": {"class": "IMP"},
        "emergency": {"class": "EMER"},
        "ambulatory": {"class": "AMB"},
    }
}

class EpicFHIRClient(FHIRClient):
    """
    Custom FHIR client for Epic FHIR API using our custom authentication.
    This extends the standard FHIRClient with Epic-specific behaviors.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
    ):
        """
        Initialize a new Epic FHIR client.
        
        Args:
            base_url: Base URL of the Epic FHIR API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            retry_backoff_factor: Backoff factor for retries.
        """
        # Get an access token using our custom auth module
        self.token_provider = get_token
        access_token = self.token_provider()
        
        # Initialize the standard FHIR client with our token
        super().__init__(
            base_url=base_url,
            access_token=access_token,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
        )
        
        logger.debug(f"Initialized Epic FHIR client for {base_url}")
    
    def _refresh_token_if_needed(self):
        """Refresh the access token if needed before making a request."""
        # Get a fresh token using our custom auth module
        self.access_token = self.token_provider()
        if not self.access_token:
            raise ValueError("Failed to obtain access token")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication, refreshing token if needed.
        
        Returns:
            Dictionary of HTTP headers.
        """
        # Refresh token if needed
        self._refresh_token_if_needed()
        
        # Return headers with the fresh token
        return super()._get_headers()
    
    def get_resource_parameters(self, resource_type: str, parameter_set: str = "default") -> Dict[str, Any]:
        """
        Get resource-specific parameters based on the resource type and parameter set.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            parameter_set: The specific parameter set to use (e.g., "default", "vital_signs")
            
        Returns:
            Dictionary of parameters for the resource type
        """
        if resource_type not in RESOURCE_PARAMETERS:
            return {}
            
        if parameter_set not in RESOURCE_PARAMETERS[resource_type]:
            parameter_set = "default"
            
        return RESOURCE_PARAMETERS[resource_type][parameter_set].copy()
    
    def search_resources_with_fallback(
        self,
        resource_type: str,
        base_params: Dict[str, Any],
        parameter_sets: List[str] = ["default"],
        page_limit: Optional[int] = None,
        total_limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Search for FHIR resources with fallback to alternative parameter sets if initial search fails.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            base_params: Base parameters to include in all searches (e.g., {"patient": "123"})
            parameter_sets: List of parameter sets to try in order
            page_limit: Maximum number of pages to retrieve
            total_limit: Maximum total number of resources to retrieve
            
        Yields:
            FHIR resource dictionaries
        """
        # Try each parameter set in sequence until one succeeds
        for param_set in parameter_sets:
            try:
                # Get resource-specific parameters for this set
                resource_params = self.get_resource_parameters(resource_type, param_set)
                
                # Merge with base parameters
                merged_params = {**base_params, **resource_params}
                
                # Try the search with these parameters
                logger.debug(f"Trying {resource_type} search with parameter set '{param_set}': {merged_params}")
                
                for resource in self.search_resources(
                    resource_type=resource_type,
                    params=merged_params,
                    page_limit=page_limit,
                    total_limit=total_limit,
                ):
                    yield resource
                
                # If we get here without an exception, the search was successful
                logger.debug(f"Successfully retrieved {resource_type} resources with parameter set '{param_set}'")
                return
                
            except Exception as e:
                logger.warning(f"Error with {resource_type} parameter set '{param_set}': {e}")
                continue
        
        # If we get here, all parameter sets failed
        logger.error(f"All parameter sets failed for {resource_type}")
        return
    
    def search_patient_by_id(self, patient_id: str) -> Dict[str, Any]:
        """
        Get a specific patient by ID.
        
        Args:
            patient_id: The patient ID to search for.
            
        Returns:
            Patient resource as dictionary.
        """
        return self.get_resource("Patient", patient_id)
    
    def get_all_resources(
        self, 
        resource_type: str, 
        params: Dict[str, Any], 
        max_pages: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all resources of a specified type with pagination support.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            params: Query parameters
            max_pages: Maximum number of pages to retrieve (default: 50)
            
        Returns:
            List of resource dictionaries
        """
        return list(self.search_resources(
            resource_type=resource_type,
            params=params,
            page_limit=max_pages
        ))
    
    def get_patient_data(self, patient_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get comprehensive data for a specific patient including observations, encounters, etc.
        
        Args:
            patient_id: The patient ID to search for.
            
        Returns:
            Dictionary with patient data organized by resource type.
        """
        # First, get the patient record
        patient = self.get_resource("Patient", patient_id)
        
        # Initialize results with expanded resource types
        results = {
            "Patient": [patient],
            "Observation": [],
            "Encounter": [],
            "Condition": [],
            "MedicationRequest": [],
            "Procedure": [],
            "AllergyIntolerance": [],
            "DiagnosticReport": [],
            "CarePlan": [],
            "Immunization": [],
            "DocumentReference": [],
            "RelatedPerson": []
        }
        
        # Get related resources
        for resource_type in results.keys():
            if resource_type == "Patient":
                continue  # We already have the patient
                
            try:
                base_params = {"patient": patient_id}
                
                # Use parameter sets with fallback for better error recovery
                if resource_type == "Observation":
                    parameter_sets = ["date_filter", "all_categories"]
                elif resource_type == "CarePlan":
                    parameter_sets = ["all_statuses", "active", "completed"]
                else:
                    parameter_sets = ["default"]
                
                # Get resources of this type for the patient with fallback
                resources = list(self.search_resources_with_fallback(
                    resource_type=resource_type,
                    base_params=base_params,
                    parameter_sets=parameter_sets,
                    total_limit=100
                ))
                
                results[resource_type] = resources
                
                logger.debug(f"Found {len(resources)} {resource_type} resources for patient {patient_id}")
            except Exception as e:
                logger.error(f"Error getting {resource_type} for patient {patient_id}: {e}")
        
        return results


def create_epic_fhir_client(base_url: Optional[str] = None) -> EpicFHIRClient:
    """
    Create a configured Epic FHIR client with authentication.
    
    Args:
        base_url: Optional base URL of the FHIR API. If not provided,
                 it will be loaded from configuration.
    
    Returns:
        Configured EpicFHIRClient instance.
    """
    from epic_fhir_integration.config.loader import get_config
    
    if not base_url:
        config = get_config("fhir")
        if not config or "base_url" not in config:
            raise ValueError("Missing FHIR base URL in configuration")
        base_url = config["base_url"]
    
    return EpicFHIRClient(base_url=base_url) 