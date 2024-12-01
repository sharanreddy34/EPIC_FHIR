"""
Epic-specific FHIR client module.

This module extends the generic FHIR client with Epic-specific optimizations,
including $everything operation support and Epic-specific headers.
"""

import logging
import time
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

import requests

from epic_fhir_integration.io.fhir_client import FHIRClient, create_fhir_client

logger = logging.getLogger(__name__)

# Constants for Epic FHIR API
EPIC_SPECIAL_HEADERS = {
    "Epic-Client-ID": "",  # To be populated from config
    "Epic-Patient-Context": True,
    "Epic-Data-Access-Protection": "enabled",  # Enables protections against malicious data access patterns
}

# Epic FHIR extensions and operations
EPIC_EXTENSIONS = {
    "everything": "$everything",
    "lastn": "$lastn",
    "healthcare_service": "HealthcareService",
}


class EpicFHIRClient(FHIRClient):
    """Epic-specific FHIR client with optimizations."""
    
    def __init__(
        self,
        base_url: str,
        access_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        client_id: Optional[str] = None,
        use_epic_optimizations: bool = True,
        prefer_bulk: bool = True,
    ):
        """Initialize a new Epic FHIR client.
        
        Args:
            base_url: Base URL of the Epic FHIR API.
            access_token: Optional access token for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            retry_backoff_factor: Backoff factor for retries.
            client_id: Epic Client ID for API access.
            use_epic_optimizations: Whether to use Epic-specific optimizations.
            prefer_bulk: Whether to prefer $everything operations over standard paging.
        """
        super().__init__(
            base_url=base_url,
            access_token=access_token,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
        )
        
        self.client_id = client_id
        self.use_epic_optimizations = use_epic_optimizations
        self.prefer_bulk = prefer_bulk
        
        # Load configuration for Epic-specific settings
        self._load_epic_config()
    
    def _load_epic_config(self):
        """Load Epic-specific configuration."""
        try:
            from epic_fhir_integration.config.loader import get_config
            
            epic_config = get_config("epic")
            if epic_config:
                self.client_id = epic_config.get("client_id", self.client_id)
                self.use_epic_optimizations = epic_config.get(
                    "use_optimizations", self.use_epic_optimizations
                )
                self.prefer_bulk = epic_config.get("prefer_bulk", self.prefer_bulk)
        except Exception as e:
            logger.warning(f"Failed to load Epic configuration: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with Epic-specific optimizations.
        
        Returns:
            Dictionary of HTTP headers.
        """
        headers = super()._get_headers()
        
        # Add Epic-specific headers if optimizations are enabled
        if self.use_epic_optimizations:
            epic_headers = EPIC_SPECIAL_HEADERS.copy()
            if self.client_id:
                epic_headers["Epic-Client-ID"] = self.client_id
            headers.update(epic_headers)
        
        # Add preference for handling large responses
        if self.prefer_bulk:
            headers["Prefer"] = "respond-async"
        
        return headers
    
    def get_everything(
        self, 
        resource_type: str, 
        resource_id: str, 
        params: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_async: bool = True,
    ) -> Dict[str, Any]:
        """Get a resource and all related resources using Epic's $everything operation.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Encounter").
            resource_id: Resource ID to fetch everything for.
            params: Optional additional parameters.
            start_date: Optional start date filter (ISO format).
            end_date: Optional end date filter (ISO format).
            use_async: Whether to use asynchronous processing for large responses.
            
        Returns:
            Bundle containing the resource and all related resources.
        """
        # Build the URL for the $everything operation
        url = f"{self.base_url}/{resource_type}/{resource_id}/$everything"
        
        # Prepare parameters
        params = params or {}
        if start_date:
            params["_since"] = start_date
        if end_date:
            params["_till"] = end_date
        
        # Set up headers
        headers = self._get_headers()
        if use_async:
            headers["Prefer"] = "respond-async"
        
        # Make the request
        response = self.session.get(
            url,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        
        # Check if this is an asynchronous response
        if response.status_code == 202 and "Content-Location" in response.headers:
            # Get the status URL from the Content-Location header
            status_url = response.headers["Content-Location"]
            
            # Poll the status URL until the request is complete
            return self._poll_async_request(status_url)
        
        # For immediate responses, process normally
        return self._handle_response(response)
    
    def _poll_async_request(self, status_url: str, max_retries: int = 12, wait_time: int = 5) -> Dict[str, Any]:
        """Poll an asynchronous request until it completes.
        
        Args:
            status_url: URL to poll for status updates.
            max_retries: Maximum number of polling attempts.
            wait_time: Time to wait between polling attempts in seconds.
            
        Returns:
            Final response data.
            
        Raises:
            TimeoutError: If the request doesn't complete within max_retries.
        """
        retries = 0
        while retries < max_retries:
            # Wait before polling
            time.sleep(wait_time)
            
            # Poll the status URL
            logger.debug(f"Polling async request status: {status_url}")
            response = self.session.get(
                status_url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            # Check response status
            if response.status_code == 200:
                # Request completed successfully
                return self._handle_response(response)
            
            if response.status_code == 202:
                # Request still processing, continue polling
                retries += 1
                continue
            
            # Handle error responses
            response.raise_for_status()
        
        # If we reach here, the request timed out
        raise TimeoutError(f"Async request did not complete after {max_retries} retries")
    
    def get_patient_everything(
        self, 
        patient_id: str, 
        params: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a Patient and all related resources.
        
        This is a convenience method for get_everything("Patient", patient_id).
        
        Args:
            patient_id: Patient ID to fetch everything for.
            params: Optional additional parameters.
            start_date: Optional start date filter (ISO format).
            end_date: Optional end date filter (ISO format).
            
        Returns:
            Bundle containing the Patient and all related resources.
        """
        return self.get_everything(
            resource_type="Patient",
            resource_id=patient_id,
            params=params,
            start_date=start_date,
            end_date=end_date,
        )
    
    def get_last_n_observations(
        self,
        patient_id: str,
        code: Optional[str] = None,
        system: Optional[str] = None,
        n: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get the last N observations for a patient using Epic's $lastn operation.
        
        Args:
            patient_id: Patient ID to fetch observations for.
            code: Optional code to filter observations by.
            system: Optional code system for the code parameter.
            n: Number of most recent observations to fetch (default: 5).
            category: Optional category to filter observations by.
            
        Returns:
            List of Observation resources.
        """
        # Build the URL for the $lastn operation
        url = f"{self.base_url}/Observation/$lastn"
        
        # Prepare parameters
        params = {
            "patient": patient_id,
            "max": str(n),
        }
        
        if code:
            if system:
                params["code"] = f"{system}|{code}"
            else:
                params["code"] = code
        
        if category:
            params["category"] = category
        
        # Make the request
        response = self.session.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.timeout,
        )
        
        # Process the response
        data = self._handle_response(response)
        
        # Extract the observations from the bundle
        observations = []
        entries = data.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Observation":
                observations.append(resource)
        
        return observations
    
    def search_healthcare_services(
        self,
        params: Optional[Dict[str, Any]] = None,
        page_limit: Optional[int] = None,
        total_limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Search for Epic HealthcareService resources.
        
        Epic's HealthcareService resource contains information about services
        offered by healthcare organizations, including scheduling endpoints.
        
        Args:
            params: Optional search parameters.
            page_limit: Maximum number of pages to retrieve.
            total_limit: Maximum total number of resources to retrieve.
            
        Yields:
            HealthcareService resources.
        """
        # Epic uses a specific resource name for healthcare services
        return self.search_resources(
            resource_type=EPIC_EXTENSIONS["healthcare_service"],
            params=params,
            page_limit=page_limit,
            total_limit=total_limit,
        )
    
    def get_clinical_notes(
        self,
        patient_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get clinical notes (DocumentReference resources) for a patient.
        
        Epic stores clinical notes as DocumentReference resources.
        
        Args:
            patient_id: Patient ID to fetch notes for.
            date_from: Optional start date filter (ISO format).
            date_to: Optional end date filter (ISO format).
            category: Optional category to filter notes by.
            
        Returns:
            List of DocumentReference resources.
        """
        # Prepare search parameters
        params = {
            "patient": patient_id,
            "type": "http://loinc.org|34109-9",  # LOINC code for Note
            "_count": "100",
        }
        
        if date_from:
            params["date"] = f"ge{date_from}"
            
        if date_to:
            params["date"] = params.get("date", "") + f"&date=le{date_to}"
            
        if category:
            params["category"] = category
        
        # Search for DocumentReference resources
        notes = list(self.search_resources(
            resource_type="DocumentReference",
            params=params,
            total_limit=1000,  # Limit to 1000 notes for performance
        ))
        
        return notes


def create_epic_fhir_client(base_url: Optional[str] = None) -> EpicFHIRClient:
    """Create a configured Epic FHIR client with authentication.
    
    Args:
        base_url: Optional base URL of the Epic FHIR API. If not provided,
                 it will be loaded from configuration.
    
    Returns:
        Configured EpicFHIRClient instance.
    """
    from epic_fhir_integration.config.loader import get_config
    
    # Get FHIR base URL from config if not provided
    if not base_url:
        fhir_config = get_config("fhir")
        if not fhir_config or "base_url" not in fhir_config:
            raise ValueError("Missing FHIR base URL in configuration")
        base_url = fhir_config["base_url"]
    
    # Get Epic-specific configuration
    epic_config = get_config("epic") or {}
    client_id = epic_config.get("client_id")
    use_optimizations = epic_config.get("use_optimizations", True)
    
    # Get an access token
    from epic_fhir_integration.auth.jwt_auth import get_token_with_retry
    access_token = get_token_with_retry()
    
    # Create and return the Epic FHIR client
    return EpicFHIRClient(
        base_url=base_url,
        access_token=access_token,
        client_id=client_id,
        use_epic_optimizations=use_optimizations,
    ) 