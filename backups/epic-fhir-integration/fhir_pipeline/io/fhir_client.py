"""
Enhanced FHIR client for Epic FHIR API.

Improvements over the original client:
- Better handling of OperationOutcome errors
- Token refresh on 401 responses
- More comprehensive retry logic
- Concurrent resource fetching
"""

import time
import logging
import urllib.parse
import traceback
import json
import asyncio
import aiohttp
import requests
import backoff
import os
from typing import Dict, Any, List, Iterator, Optional, Callable, Union, Set, Tuple
from pathlib import Path

# Setup logging
logger = logging.getLogger("fhir_pipeline.fhir_client")


class FHIRError(Exception):
    """Base exception for FHIR client errors."""
    pass


class FHIRAuthError(FHIRError):
    """Authentication error."""
    pass


class FHIRRateLimitError(FHIRError):
    """Rate limit exceeded error."""
    pass


class FHIROperationOutcomeError(FHIRError):
    """Error from FHIR OperationOutcome resource."""
    
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details


class FHIRClient:
    """Enhanced client for Epic FHIR API."""

    def __init__(
        self,
        base_url: str,
        token_provider: Optional[Callable[[], str]] = None,
        api_config: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: int = 30,
        verify_ssl: bool = True,
        debug_mode: bool = False,
        concurrent_requests: int = 3,
        rate_limit: Optional[int] = None,
        mock_mode: bool = False
    ):
        """
        Initialize the FHIR client.

        Args:
            base_url: Base URL for the FHIR API
            token_provider: Function that returns an access token
            api_config: API configuration parameters
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            debug_mode: Whether to enable detailed debug logging
            concurrent_requests: Maximum number of concurrent requests
            rate_limit: Maximum requests per minute (None for no limit)
            mock_mode: Whether to run in mock mode (no real API calls)
        """
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self._token = None  # Cache the token
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.debug_mode = debug_mode
        self.concurrent_requests = concurrent_requests
        self.session = self._create_session()
        
        # For async requests
        self.async_session = None
        
        logger.info(f"FHIR client initialized with base URL: {self.base_url}")
        logger.debug(f"Client config: max_retries={max_retries}, timeout={timeout}, "
                     f"verify_ssl={verify_ssl}, debug_mode={debug_mode}, "
                     f"concurrent_requests={concurrent_requests}")
        
        # Diagnostic counters
        self.request_count = 0
        self.error_count = 0
        self.retry_count = 0
        self.rate_limit_count = 0
        self.auth_error_count = 0
        self.outcome_error_count = 0
        
        # Token handling
        self.token_data = None  # Token data including expiry
        self.token_path = Path("secrets/epic_token.json")  # Default token path
        
        # Mock mode settings
        self.mock_token = mock_mode
        self.mock_mode = mock_mode
        
        # Token expiry buffer
        self.token_expiry_buffer = 300  # 5 minutes buffer for token expiry

    def _create_session(self) -> requests.Session:
        """Create a session with default headers."""
        logger.debug("Creating new requests session")
        session = requests.Session()
        session.headers.update({
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        })
        return session
        
    async def _create_async_session(self) -> aiohttp.ClientSession:
        """Create an async session with default headers."""
        if self.async_session is None or self.async_session.closed:
            logger.debug("Creating new async session")
            self.async_session = aiohttp.ClientSession(
                headers={
                    "Accept": "application/fhir+json",
                    "Content-Type": "application/fhir+json",
                }
            )
        return self.async_session

    def _get_token(self, force_refresh=False):
        """
        Get access token from provider or cached data.
        
        Args:
            force_refresh: Whether to force a token refresh
            
        Returns:
            Access token
        """
        try:
            # For tests, we can bypass the token provider entirely
            if self.mock_token:
                return "MOCK-TOKEN-FOR-TESTING"
            
            # Check if token is already loaded and not forcing refresh
            if not force_refresh and self.token_data is not None:
                # Check if token is about to expire
                if self._is_token_valid(self.token_data, self.token_expiry_buffer):
                    # Return existing token 
                    return self.token_data.get("access_token")
            
            # Try to load token directly from the root token file first if it exists
            # This is important for running tests and other functions from the project root
            root_token_path = Path("epic_token.json")
            if root_token_path.exists() and root_token_path.is_file():
                try:
                    with open(root_token_path, "r") as f:
                        token_data = json.load(f)
                        if self._is_token_valid(token_data, self.token_expiry_buffer):
                            self.token_data = token_data
                            self.logger.info(f"Loaded valid token from project root: {root_token_path}")
                            return token_data.get("access_token")
                except Exception as e:
                    self.logger.warning(f"Error loading token from project root: {e}")
            
            # Try from the token provider
            if self.token_provider:
                # Get fresh token from provider
                token = self.token_provider()
                if token:
                    self.logger.debug(f"Obtained token from provider")
                    return token
                    
            # Try to load from token path
            if self.token_path and self.token_path.exists() and self.token_path.is_file():
                try:
                    with open(self.token_path, "r") as f:
                        token_data = json.load(f)
                        if self._is_token_valid(token_data, self.token_expiry_buffer):
                            self.token_data = token_data
                            return token_data.get("access_token")
                except Exception as e:
                    self.logger.warning(f"Error loading token from path: {e}")
            
            self.logger.error("No valid token available")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting token: {e}")
            return None

    def _get_headers(self, force_token_refresh: bool = False) -> Dict[str, str]:
        """
        Get headers with current auth token.
        
        Args:
            force_token_refresh: Whether to force a token refresh
            
        Returns:
            Headers dict
        """
        try:
            token = self._get_token(force_refresh=force_token_refresh)
            logger.debug(f"Generated auth headers with token (length: {len(token) if token else 0})")
            return {
                "Authorization": f"Bearer {token}",
            }
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            logger.debug(f"Token error details: {traceback.format_exc()}")
            self.auth_error_count += 1
            raise FHIRAuthError(f"Failed to get authorization headers: {str(e)}")

    def _log_request(self, method: str, url: str, params: Dict, start_time: float, response=None, error=None):
        """
        Log request details for debugging.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Request parameters
            start_time: Request start time
            response: Response object if successful
            error: Exception if failed
        """
        if not self.debug_mode:
            return
            
        elapsed = time.time() - start_time
        log_data = {
            "method": method,
            "url": url,
            "params": params,
            "elapsed_seconds": f"{elapsed:.3f}",
            "request_id": self.request_count,
        }
        
        if response:
            log_data.update({
                "status_code": response.status_code,
                "response_size_bytes": len(response.content),
                "headers": dict(response.headers),
            })
            
        if error:
            log_data.update({
                "error": str(error),
                "error_type": type(error).__name__,
            })
            
        logger.debug(f"FHIR Request: {json.dumps(log_data, indent=2, default=str)}")
        
        # Log response details for further debugging
        if response and response.status_code != 200 and self.debug_mode:
            try:
                logger.debug(f"Response content: {response.content[:1000]}...")
            except:
                pass

    def _check_for_operation_outcome(self, response: requests.Response) -> None:
        """
        Check if response contains an OperationOutcome resource and raise if it's an error.
        
        Args:
            response: Response to check
            
        Raises:
            FHIROperationOutcomeError: If response contains an error OperationOutcome
        """
        try:
            data = response.json()
            if data.get("resourceType") == "OperationOutcome":
                # Extract issue details
                issues = data.get("issue", [])
                error_issues = [i for i in issues if i.get("severity") in ["error", "fatal"]]
                
                if error_issues:
                    # Format error message from the issues
                    error_messages = []
                    for issue in error_issues:
                        code = issue.get("code", "unknown")
                        details = issue.get("details", {}).get("text", "No details")
                        error_messages.append(f"{code}: {details}")
                    
                    error_message = "; ".join(error_messages)
                    logger.error(f"FHIR OperationOutcome error: {error_message}")
                    self.outcome_error_count += 1
                    
                    # Determine if this error is retriable
                    retriable_codes = ["timeout", "too-costly", "transient", "throttled"]
                    is_retriable = any(
                        any(code in issue.get("code", "").lower() for code in retriable_codes)
                        for issue in error_issues
                    )
                    
                    raise FHIROperationOutcomeError(
                        error_message, 
                        {"outcome": data, "retriable": is_retriable}
                    )
                    
        except (ValueError, KeyError, json.JSONDecodeError):
            # Not JSON or not an OperationOutcome
            pass

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout),
        max_tries=3,
        on_backoff=lambda details: logger.info(f"Backing off {details['target'].__name__}(...) for {details['wait']:.1f}s ({details['exception']})")
    )
    def _make_request(self, method, endpoint, params=None, data=None, force_token_refresh=False):
        """
        Make an HTTP request to the FHIR API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            force_token_refresh: Whether to force a token refresh
            
        Returns:
            Response object
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            # Add auth headers
            headers = self._get_headers(force_token_refresh=force_token_refresh)
            self.session.headers.update(headers)
            
            # Track start time for metrics
            start_time = time.time()
            
            # Make request
            logger.debug(f"Making {method} request to {url}")
            if params:
                logger.debug(f"Query parameters: {params}")
            if data:
                logger.debug(f"Request body: {json.dumps(data) if isinstance(data, dict) else str(data)[:100]}")
                
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data if data else None,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            
            # Track response time
            elapsed = time.time() - start_time
            logger.debug(f"Request completed in {elapsed:.3f}s with status {response.status_code}")
            
            # Increment counters
            self.request_count += 1
            
            # Handle errors
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    logger.warning("Authentication failed. Token might be expired.")
                    # Try to load new token from file if available
                    try:
                        for token_path in ["secrets/epic_token.json", "../auth/epic_token.json", "epic_token.json"]:
                            try:
                                if os.path.exists(token_path):
                                    with open(token_path, "r") as f:
                                        token_data = json.load(f)
                                        self._token = token_data.get("access_token")
                                        if self._token:
                                            logger.info(f"Loaded fresh token from {token_path}")
                                            break
                            except Exception as te:
                                logger.debug(f"Failed to load token from {token_path}: {str(te)}")
                        if force_token_refresh:
                            raise # If already tried to refresh, don't try again
                    except Exception as te:
                        logger.debug(f"Failed to refresh token: {str(te)}")
                        
                    # If we're not already doing a token refresh, try again with a fresh token
                    if not force_token_refresh:
                        logger.debug("Retrying request with fresh token")
                        return self._make_request(
                            method, endpoint, params, data, force_token_refresh=True
                        )
                
                # For actual FHIR OperationOutcome errors, extract the details
                if 'application/fhir+json' in response.headers.get('Content-Type', ''):
                    try:
                        outcome = response.json()
                        if outcome.get('resourceType') == 'OperationOutcome':
                            issue_details = []
                            for issue in outcome.get('issue', []):
                                severity = issue.get('severity', 'unknown')
                                code = issue.get('code', 'unknown')
                                details = issue.get('details', {}).get('text', 'No details')
                                issue_details.append(f"{severity}: {code} - {details}")
                            
                            error_details = '; '.join(issue_details)
                            self.outcome_error_count += 1
                            logger.error(f"FHIR operation error: {error_details}")
                            
                            # Special handling for certain error types
                            if any('Account closed' in detail for detail in issue_details):
                                logger.error("Account closed error detected - this is a critical issue")
                    except Exception as parse_e:
                        logger.debug(f"Error parsing FHIR OperationOutcome: {str(parse_e)}")
                
                # Track error
                self.error_count += 1
                
                # Log the error
                logger.error(f"Request failed after {elapsed:.3f}s: {str(e)}")
                
                # Re-raise
                raise
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.debug(f"Response status: {e.response.status_code}")
                logger.debug(f"Response content: {e.response.text[:500]}...")
            else:
                logger.debug("No response details available")
            raise

    def search_resource(
        self,
        resource_type: str,
        search_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """
        Search for resources of the specified type.

        Args:
            resource_type: FHIR resource type (Patient, Encounter, etc.)
            search_params: Search parameters
            page_size: Number of results per page

        Yields:
            FHIR Bundle for each page of results
        """
        params = search_params.copy() if search_params else {}
        params["_count"] = page_size

        # Make initial request
        next_url = f"{resource_type}"
        
        page_num = 0
        while next_url:
            logger.debug(f"Fetching page {page_num} from {next_url}")
            
            if next_url.startswith(self.base_url):
                # Absolute URL - use as is, extract params from URL
                url = next_url
                parsed_url = urllib.parse.urlparse(next_url)
                
                # Fix for URL path duplication
                # Extract the path correctly, accounting for multiple occurrences of base paths
                base_path = urllib.parse.urlparse(self.base_url).path
                path = parsed_url.path
                
                # If the path contains the base path more than once, keep only the last occurrence
                if base_path and path.count(base_path) > 1:
                    # Find the position after the first instance of base_path
                    path_parts = path.split(base_path)
                    endpoint = path_parts[-1].lstrip('/')
                else:
                    # Normal case - just remove the base path
                    endpoint = path.replace(base_path, "", 1).lstrip('/')
                
                query_params = urllib.parse.parse_qs(parsed_url.query)
                # Convert list values to single values since parse_qs returns lists
                query_params = {k: v[0] for k, v in query_params.items()}
                
                # Always include page size - some Epic implementations drop it
                query_params["_count"] = page_size
                
                # Make request
                response = self._make_request("GET", endpoint, params=query_params)
            else:
                # Relative URL - combine with base URL
                endpoint = next_url
                
                # Always include page size 
                if "_count" not in params:
                    params["_count"] = page_size
                    
                response = self._make_request("GET", endpoint, params=params)
            
            # Reset params for subsequent requests (they'll be in the next URL)
            params = {}
            
            bundle = response.json()
            page_num += 1
            
            yield bundle
            
            # Check for next link
            next_url = None
            if "link" in bundle:
                for link in bundle["link"]:
                    if link.get("relation") == "next":
                        next_url = link.get("url")
                        break

    async def search_resource_async(
        self,
        resource_type: str,
        search_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search for resources asynchronously.
        
        Args:
            resource_type: FHIR resource type
            search_params: Search parameters
            page_size: Number of results per page
            
        Returns:
            List of FHIR Bundles
        """
        params = search_params.copy() if search_params else {}
        params["_count"] = page_size
        
        endpoint = f"{resource_type}"
        session = await self._create_async_session()
        
        # We'll collect all bundles and return them
        all_bundles = []
        next_url = f"{self.base_url}/{endpoint.lstrip('/')}"
        page_num = 0
        
        while next_url:
            logger.debug(f"Async fetching page {page_num} from {next_url}")
            
            # Get token
            token = self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make async request
            try:
                query_params = params.copy()
                
                # If it's an absolute URL, parse the params from it
                if next_url.startswith(self.base_url):
                    parsed_url = urllib.parse.urlparse(next_url)
                    
                    # Fix for URL path duplication in async method
                    base_path = urllib.parse.urlparse(self.base_url).path
                    path = parsed_url.path
                    
                    # If the base URL has a path and it's duplicated in the next URL
                    if base_path and path.count(base_path) > 1:
                        # Get the URL without duplicated paths
                        scheme = parsed_url.scheme
                        netloc = parsed_url.netloc
                        
                        # Build the correct path by taking the first occurrence of base_path
                        path_parts = path.split(base_path)
                        correct_path = base_path + path_parts[-1]
                        next_url = f"{scheme}://{netloc}{correct_path}"
                    
                    query_dict = urllib.parse.parse_qs(parsed_url.query)
                    # Convert lists to single values
                    query_params = {k: v[0] for k, v in query_dict.items()}
                
                # Always include page size
                query_params["_count"] = page_size
                
                async with session.get(
                    next_url,
                    params=query_params,
                    headers=headers,
                    timeout=self.timeout,
                    ssl=None if self.verify_ssl else False
                ) as response:
                    # Check status
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 10))
                        logger.warning(f"Rate limit exceeded in async request. Retry after {retry_after}s")
                        self.rate_limit_count += 1
                        await asyncio.sleep(retry_after)
                        continue
                        
                    if response.status == 401:
                        logger.warning("Authentication failed in async request. Refreshing token.")
                        self.auth_error_count += 1
                        self._get_token(force_refresh=True)
                        continue
                        
                    response.raise_for_status()
                    
                    # Parse response - explicitly await the json coroutine
                    bundle = await response.json()
                    
                    # Check for OperationOutcome errors
                    if bundle.get("resourceType") == "OperationOutcome":
                        issues = bundle.get("issue", [])
                        error_issues = [i for i in issues if i.get("severity") in ["error", "fatal"]]
                        
                        if error_issues:
                            error_message = "; ".join(
                                f"{i.get('code', 'unknown')}: {i.get('details', {}).get('text', 'No details')}"
                                for i in error_issues
                            )
                            logger.error(f"FHIR OperationOutcome error in async request: {error_message}")
                            self.outcome_error_count += 1
                            
                            # Check if retriable
                            retriable_codes = ["timeout", "too-costly", "transient", "throttled"]
                            is_retriable = any(
                                any(code in i.get("code", "").lower() for code in retriable_codes)
                                for i in error_issues
                            )
                            
                            if is_retriable:
                                # Wait and retry
                                await asyncio.sleep(2)
                                continue
                            else:
                                # Not retriable, raise
                                raise FHIROperationOutcomeError(
                                    error_message,
                                    {"outcome": bundle, "retriable": False}
                                )
                    
                    # Add to results
                    all_bundles.append(bundle)
                    page_num += 1
                    
                    # Look for next link
                    next_url = None
                    if "link" in bundle:
                        for link in bundle["link"]:
                            if link.get("relation") == "next":
                                next_url = link.get("url")
                                break
                    
                    # If no next link, we're done
                    if not next_url:
                        break
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Async request error: {str(e)}")
                self.error_count += 1
                
                # For most errors, we'll try again after a short delay
                await asyncio.sleep(2)
                continue
        
        logger.debug(f"Async search completed for {resource_type}, fetched {len(all_bundles)} pages")
        return all_bundles

    async def get_patient_resources_for_multiple_types(
        self,
        patient_id: str,
        resource_types: List[str],
        additional_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get multiple resource types for a patient concurrently.
        
        Args:
            patient_id: Patient ID
            resource_types: List of resource types to fetch
            additional_params: Additional search parameters
            page_size: Number of results per page
            
        Returns:
            Dict mapping resource types to lists of bundles
        """
        logger.info(f"Fetching {len(resource_types)} resource types for patient {patient_id}")
        
        # Create tasks for each resource type
        tasks = []
        for resource_type in resource_types:
            params = additional_params.copy() if additional_params else {}
            
            # Special case for Patient
            if resource_type == "Patient":
                params["_id"] = patient_id
            else:
                params["patient"] = patient_id
                
            # Add required category parameter for Observation resources
            if resource_type == "Observation" and "category" not in params:
                params["category"] = "laboratory"
                
            task = self.search_resource_async(resource_type, params, page_size)
            tasks.append((resource_type, task))
            
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def fetch_with_semaphore(resource_type, task):
            async with semaphore:
                logger.debug(f"Starting fetch for {resource_type}")
                try:
                    result = await task
                    logger.debug(f"Completed fetch for {resource_type}, got {len(result)} bundles")
                    return resource_type, result
                except Exception as e:
                    logger.error(f"Error fetching {resource_type}: {str(e)}")
                    return resource_type, []
        
        # Run tasks with semaphore
        fetch_tasks = [fetch_with_semaphore(rt, task) for rt, task in tasks]
        results = await asyncio.gather(*fetch_tasks)
        
        # Organize results by resource type
        return {rt: bundles for rt, bundles in results}

    def extract_patient_resources_parallel(
        self,
        patient_id: str,
        resource_types: List[str],
        additional_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract resources for a patient using parallel requests.
        
        Args:
            patient_id: Patient ID
            resource_types: Resource types to extract
            additional_params: Additional search parameters
            page_size: Number of results per page
            
        Returns:
            Dict mapping resource types to lists of bundles
        """
        logger.info(f"Extracting {len(resource_types)} resource types for patient {patient_id}")
        
        # Create and run event loop
        # Check if we're already in an event loop to avoid recursion errors
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop if the current one is running
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop exists yet
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            # Run the async method and capture results
            coro = self.get_patient_resources_for_multiple_types(
                patient_id, resource_types, additional_params, page_size
            )
            results = loop.run_until_complete(coro)
            
            # Only close the session if we're not in a running event loop
            if hasattr(self, 'async_session') and self.async_session is not None:
                loop.run_until_complete(self.async_session.close())
            
            return results
        finally:
            # Only close the loop if we created it
            if not loop.is_running():
                loop.close()
            
    def get_resource(
        self,
        resource_type: str,
        resource_id: str,
    ) -> Dict[str, Any]:
        """
        Get a specific resource by ID.

        Args:
            resource_type: FHIR resource type (Patient, Encounter, etc.)
            resource_id: Resource ID

        Returns:
            FHIR resource
        """
        endpoint = f"{resource_type}/{resource_id}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def batch_get_resources(
        self,
        resource_type: str,
        resource_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Get multiple resources by ID using a batch request.

        Args:
            resource_type: FHIR resource type (Patient, Encounter, etc.)
            resource_ids: List of resource IDs

        Returns:
            List of FHIR resources
        """
        # Prepare batch request
        entries = []
        for resource_id in resource_ids:
            entries.append({
                "request": {
                    "method": "GET",
                    "url": f"{resource_type}/{resource_id}"
                }
            })
        
        batch_data = {
            "resourceType": "Bundle",
            "type": "batch",
            "entry": entries
        }
        
        # Send batch request
        response = self._make_request("POST", "", data=batch_data)
        bundle = response.json()
        
        # Extract resources from response
        resources = []
        for entry in bundle.get("entry", []):
            if "resource" in entry:
                resources.append(entry["resource"])
        
        return resources
    
    def get_patient_resources(
        self,
        resource_type: str,
        patient_id: str,
        additional_params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get resources for a specific patient.

        Args:
            resource_type: FHIR resource type (Encounter, Observation, etc.)
            patient_id: Patient ID
            additional_params: Additional search parameters
            page_size: Number of results per page

        Yields:
            FHIR Bundle for each page of results
        """
        params = additional_params.copy() if additional_params else {}
        
        # Handle Patient resource differently
        if resource_type == "Patient":
            params["_id"] = patient_id
        else:
            params["patient"] = patient_id
        
        # Add required category parameter for Observation resources
        if resource_type == "Observation" and "category" not in params:
            params["category"] = "laboratory"
        
        return self.search_resource(resource_type, params, page_size)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get FHIR server metadata (capability statement).

        Returns:
            FHIR capability statement
        """
        response = self._make_request("GET", "metadata")
        return response.json()
    
    def validate_connection(self) -> bool:
        """
        Validate connection to the FHIR server.

        Returns:
            True if connection is valid
        """
        try:
            self.get_metadata()
            return True
        except Exception as e:
            logger.error(f"Failed to validate connection: {str(e)}")
            return False

    def get_metrics(self) -> Dict[str, int]:
        """
        Get client metrics.
        
        Returns:
            Dict of metrics
        """
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "rate_limit_count": self.rate_limit_count,
            "auth_error_count": self.auth_error_count,
            "outcome_error_count": self.outcome_error_count,
        } 

    def _on_backoff(self, details):
        """
        Function called when backoff occurs.
        
        Args:
            details: Backoff details
        """
        logger.info(f"Backing off {details['target'].__name__}(...) for {details['wait']:.1f}s ({details['exception']})")
        self.retry_count += 1
        return 

    def _is_token_valid(self, token_data: Dict[str, Any], buffer_seconds: int = 300) -> bool:
        """
        Check if a token is still valid with a buffer time.
        
        Args:
            token_data: Token data dictionary with expires_in or expires_at
            buffer_seconds: Number of seconds buffer before expiry to consider invalid
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # If no token data, it's invalid
            if not token_data or not isinstance(token_data, dict):
                return False
                
            # Get current time
            now = time.time()
            
            # Check if token has expires_at (absolute timestamp)
            if "expires_at" in token_data:
                expires_at = token_data["expires_at"]
                return now < (expires_at - buffer_seconds)
                
            # Check if token has expires_in (relative seconds)
            elif "expires_in" in token_data:
                # If we don't know when the token was created, assume it was just now
                # This is not ideal but better than failing
                created_at = token_data.get("created_at", now)
                expires_in = token_data["expires_in"]
                expires_at = created_at + expires_in
                return now < (expires_at - buffer_seconds)
                
            # If no expiration info, can't determine validity
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking token validity: {e}")
            return False 