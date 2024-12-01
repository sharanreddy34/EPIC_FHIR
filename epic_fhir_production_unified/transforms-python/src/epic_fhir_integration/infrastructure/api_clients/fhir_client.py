"""
FHIR client module for Epic FHIR API integration.

This module provides a generic client for interacting with FHIR APIs,
including pagination, rate limiting, and error handling.
"""

import json
import time
import uuid
import os
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import only logging utilities to avoid circular imports
from epic_fhir_integration.utils.logging import get_logger

# Import auth function lazily to avoid circular dependencies
def _get_token():
    from epic_fhir_integration.api_clients.jwt_auth import get_token_with_retry
    return get_token_with_retry()

logger = get_logger(__name__)


class FHIRClient:
    """Generic client for interacting with FHIR APIs."""
    
    def __init__(
        self,
        base_url: str,
        access_token: Optional[str] = None,
        token_provider=None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
    ):
        """Initialize a new FHIR client.
        
        Args:
            base_url: Base URL of the FHIR API.
            access_token: Optional access token for authentication.
            token_provider: Optional function that returns an access token.
                            Will be called if access_token is None.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
            retry_backoff_factor: Backoff factor for retries.
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.token_provider = token_provider
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
        
        logger.info("Initialized FHIR client", base_url=self.base_url)
    
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
        token = self.access_token
        
        # If no token but we have a token provider, get a token
        if not token and self.token_provider:
            token = self.token_provider()
            # Store for future use
            self.access_token = token
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
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
            logger.warning("Rate limited, waiting", seconds=wait_time)
            time.sleep(wait_time)
            response.raise_for_status()  # This will trigger a retry
        
        # Handle other errors
        if not response.ok:
            logger.error("FHIR API error", 
                        status_code=response.status_code, 
                        response=response.text[:500])
            response.raise_for_status()
        
        # Return JSON response data
        return response.json()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
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
        
        logger.info("Fetching FHIR resource", 
                   resource_type=resource_type, 
                   resource_id=resource_id,
                   params=params)
        
        # Make the request
        response = self.session.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.timeout,
        )
        
        result = self._handle_response(response)
        logger.debug("Received FHIR resource", 
                    resource_type=resource_type,
                    result_size=len(json.dumps(result)))
        return result
    
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
        
        logger.info("Fetching all FHIR resources", 
                   resource_type=resource_type,
                   params=params, 
                   max_pages=max_pages)
        
        # Use the search generator to retrieve all resources
        for resource in self.search_resources(
            resource_type=resource_type,
            params=params,
            page_limit=max_pages,
        ):
            resources.append(resource)
            
        logger.info("Completed fetching all resources", 
                   resource_type=resource_type,
                   count=len(resources))
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
        
        logger.info("Starting FHIR search", 
                   resource_type=resource_type, 
                   params=params)
        
        while url:
            # Check if we've hit the page limit
            if page_limit and page_count >= page_limit:
                logger.info("Page limit reached", page_count=page_count)
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
            logger.debug("Received page", 
                        page=page_count, 
                        entries=len(entries))
            
            for entry in entries:
                resource = entry.get("resource", {})
                if resource:
                    yield resource
                    resource_count += 1
                    
                    # Check if we've hit the total limit
                    if total_limit and resource_count >= total_limit:
                        logger.info("Resource limit reached", resource_count=resource_count)
                        return
            
            # Get the URL for the next page, if available
            url = None
            for link in data.get("link", []):
                if link.get("relation") == "next":
                    url = link.get("url")
                    break
            
            if not url:
                logger.info("No more pages", page_count=page_count, resource_count=resource_count)
    
    def batch_get_resources(
        self,
        resource_type: str,
        resource_ids: List[str],
        max_workers: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """Get multiple resources by ID in parallel.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            resource_ids: List of resource IDs to fetch.
            max_workers: Maximum number of concurrent requests.
            
        Returns:
            Dictionary mapping resource IDs to resources.
        """
        results = {}
        
        logger.info("Batch getting resources", 
                   resource_type=resource_type, 
                   count=len(resource_ids))
        
        # Function to fetch a single resource
        def fetch_resource(resource_id):
            try:
                resource = self.get_resource(resource_type, resource_id)
                return resource_id, resource
            except Exception as e:
                logger.error("Error fetching resource", 
                            resource_type=resource_type,
                            resource_id=resource_id,
                            error=str(e))
                return resource_id, None
        
        # Use ThreadPoolExecutor to fetch resources in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for resource_id, resource in executor.map(fetch_resource, resource_ids):
                if resource:
                    results[resource_id] = resource
        
        logger.info("Completed batch get", 
                   resource_type=resource_type,
                   fetched=len(results),
                   requested=len(resource_ids))
        return results


def create_fhir_client() -> FHIRClient:
    """Create a configured FHIR client with authentication.
    
    Returns:
        Configured FHIRClient instance.
    """
    # Get Epic base URL from environment
    epic_base_url = os.environ.get("EPIC_BASE_URL")
    if not epic_base_url:
        raise ValueError("EPIC_BASE_URL environment variable not set")
    
    # Create client with token provider instead of directly fetching token
    # This avoids circular imports and defers token acquisition until needed
    return FHIRClient(base_url=epic_base_url, token_provider=_get_token) 