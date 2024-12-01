"""
FHIR client module for Epic FHIR API integration.

This module provides a generic client for interacting with FHIR APIs,
including pagination, rate limiting, and error handling.
"""

import json
import time
import uuid
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from epic_fhir_integration.auth.jwt_auth import get_token_with_retry


class FHIRClient:
    """Generic client for interacting with FHIR APIs."""
    
    def __init__(
        self,
        base_url: str,
        access_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
    ):
        """Initialize a new FHIR client.
        
        Args:
            base_url: Base URL of the FHIR API.
            access_token: Optional access token for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            retry_backoff_factor: Backoff factor for retries.
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            backoff_factor=retry_backoff_factor,
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        self.session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.
        
        Returns:
            Dictionary of HTTP headers.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Add authorization header if access token is available
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response and check for errors.
        
        Args:
            response: HTTP response object.
            
        Returns:
            Response data as dictionary.
            
        Raises:
            requests.HTTPError: If the request fails.
        """
        # Check for rate limiting response
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            wait_time = int(retry_after)
            time.sleep(wait_time)
            response.raise_for_status()  # This will trigger a retry
        
        # Handle other errors
        if not response.ok:
            response.raise_for_status()
        
        # Return JSON response data
        return response.json()
    
    def get_resource(
        self, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a FHIR resource by type and optional ID.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            resource_id: Optional resource ID.
            params: Optional query parameters.
            
        Returns:
            Resource data as dictionary.
        """
        # Build the URL
        url = f"{self.base_url}/{resource_type}"
        if resource_id:
            url = f"{url}/{resource_id}"
        
        # Make the request
        response = self.session.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.timeout,
        )
        
        return self._handle_response(response)
    
    def get_all_resources(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all resources of a given type using pagination.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            params: Optional query parameters.
            max_pages: Maximum number of pages to retrieve (default: 50).
            
        Returns:
            List of resources.
            
        Raises:
            ValueError: If an invalid resource type is provided.
        """
        resources = []
        
        # Use the search generator to retrieve all resources
        for resource in self.search_resources(
            resource_type=resource_type,
            params=params,
            page_limit=max_pages,
        ):
            resources.append(resource)
            
        return resources
    
    def search_resources(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None,
        page_limit: Optional[int] = None,
        total_limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Search for FHIR resources with pagination.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            params: Optional search parameters.
            page_limit: Maximum number of pages to retrieve.
            total_limit: Maximum total number of resources to retrieve.
            
        Yields:
            FHIR resource dictionaries.
        """
        params = params or {}
        url = f"{self.base_url}/{resource_type}"
        
        resource_count = 0
        page_count = 0
        
        while url:
            # Check if we've hit the page limit
            if page_limit and page_count >= page_limit:
                break
            
            # Make the request
            response = self.session.get(
                url,
                headers=self._get_headers(),
                params=params if page_count == 0 else None,  # Only use params on first request
                timeout=self.timeout,
            )
            
            data = self._handle_response(response)
            page_count += 1
            
            # Process entries
            entries = data.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                if resource:
                    yield resource
                    resource_count += 1
                    
                    # Check if we've hit the total limit
                    if total_limit and resource_count >= total_limit:
                        return
            
            # Get the URL for the next page, if available
            url = None
            for link in data.get("link", []):
                if link.get("relation") == "next":
                    url = link.get("url")
                    break
    
    def create_resource(
        self, resource_type: str, resource_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new FHIR resource.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            resource_data: Resource data to create.
            
        Returns:
            Created resource data as dictionary.
        """
        url = f"{self.base_url}/{resource_type}"
        
        response = self.session.post(
            url,
            headers=self._get_headers(),
            json=resource_data,
            timeout=self.timeout,
        )
        
        return self._handle_response(response)
    
    def update_resource(
        self, resource_type: str, resource_id: str, resource_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing FHIR resource.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            resource_id: Resource ID to update.
            resource_data: Updated resource data.
            
        Returns:
            Updated resource data as dictionary.
        """
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        
        response = self.session.put(
            url,
            headers=self._get_headers(),
            json=resource_data,
            timeout=self.timeout,
        )
        
        return self._handle_response(response)
    
    def create_batch_request(
        self, 
        requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a FHIR batch request containing multiple operations.
        
        Args:
            requests: List of request objects, each with "method", "url", and optionally "resource"
                     Example: {"method": "GET", "url": "Patient/123"}
                     
        Returns:
            Batch request bundle.
        """
        batch_bundle = {
            "resourceType": "Bundle",
            "type": "batch",
            "entry": []
        }
        
        # Add each request to the bundle
        for request in requests:
            entry = {
                "request": {
                    "method": request.get("method", "GET"),
                    "url": request.get("url", "")
                }
            }
            
            # Add resource if it's a POST or PUT request
            if "resource" in request and request.get("method") in ["POST", "PUT"]:
                entry["resource"] = request["resource"]
                
            # Add fullUrl for references within the batch
            if "fullUrl" in request:
                entry["fullUrl"] = request["fullUrl"]
            elif request.get("method") in ["POST"]:
                # Generate a temporary UUID for new resources
                entry["fullUrl"] = f"urn:uuid:{uuid.uuid4()}"
                
            batch_bundle["entry"].append(entry)
            
        return batch_bundle
    
    def process_batch_response(
        self, 
        batch_response: Dict[str, Any]
    ) -> List[Tuple[bool, Dict[str, Any]]]:
        """Process a FHIR batch response bundle.
        
        Args:
            batch_response: The response bundle from a batch request.
            
        Returns:
            List of tuples with (success, resource/error).
            
        Raises:
            ValueError: If the response is not a valid batch response bundle.
        """
        if batch_response.get("resourceType") != "Bundle" or batch_response.get("type") != "batch-response":
            raise ValueError("Invalid batch response bundle")
            
        results = []
        
        for entry in batch_response.get("entry", []):
            # Get the response part
            response = entry.get("response", {})
            status = response.get("status", "")
            
            # Check if the request was successful (2xx status code)
            success = status.startswith("2")
            
            if success and "resource" in entry:
                # Return the resource for successful requests
                results.append((True, entry["resource"]))
            else:
                # Return the response for failed requests
                results.append((False, response))
                
        return results
    
    def execute_batch(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Tuple[bool, Dict[str, Any]]]:
        """Execute a batch request and process the response.
        
        Args:
            requests: List of request objects, each with "method", "url", and optionally "resource"
            
        Returns:
            List of tuples with (success, resource/error).
        """
        # Create the batch request bundle
        batch_bundle = self.create_batch_request(requests)
        
        # Send the batch request
        url = f"{self.base_url}"
        response = self.session.post(
            url,
            headers=self._get_headers(),
            json=batch_bundle,
            timeout=self.timeout,
        )
        
        # Process the response
        batch_response = self._handle_response(response)
        return self.process_batch_response(batch_response)
    
    def batch_get_resources(
        self,
        resource_type: str,
        resource_ids: List[str],
        parallel: bool = False,
        max_workers: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """Get multiple resources of the same type efficiently.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            resource_ids: List of resource IDs to retrieve
            parallel: If True, use parallel processing instead of batching
            max_workers: Maximum number of parallel workers if parallel=True
            
        Returns:
            Dictionary mapping resource IDs to their data
        """
        if not resource_ids:
            return {}
            
        result = {}
        
        # Parallel processing approach
        if parallel and len(resource_ids) > 1:
            def get_single_resource(resource_id):
                try:
                    return resource_id, self.get_resource(resource_type, resource_id)
                except Exception as e:
                    return resource_id, {"error": str(e)}
                    
            # Use ThreadPoolExecutor for parallel requests
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for resource_id, resource_data in executor.map(get_single_resource, resource_ids):
                    if "error" not in resource_data:
                        result[resource_id] = resource_data
                        
            return result
            
        # Batch processing approach
        batch_requests = [
            {"method": "GET", "url": f"{resource_type}/{resource_id}"}
            for resource_id in resource_ids
        ]
        
        # Execute batch request
        batch_results = self.execute_batch(batch_requests)
        
        # Process results
        for i, (success, data) in enumerate(batch_results):
            if success and i < len(resource_ids):
                resource_id = resource_ids[i]
                result[resource_id] = data
                
        return result


def create_fhir_client(base_url: Optional[str] = None) -> FHIRClient:
    """Create a configured FHIR client with authentication.
    
    Args:
        base_url: Optional base URL of the FHIR API. If not provided,
                 it will be loaded from configuration.
    
    Returns:
        Configured FHIRClient instance.
    """
    from epic_fhir_integration.config.loader import get_config
    
    if not base_url:
        config = get_config("fhir")
        if not config or "base_url" not in config:
            raise ValueError("Missing FHIR base URL in configuration")
        base_url = config["base_url"]
    
    # Get an access token
    access_token = get_token_with_retry()
    
    return FHIRClient(base_url=base_url, access_token=access_token) 