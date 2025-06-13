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
from typing import Dict, Any, List, Iterator, Optional, Callable, Union, Set, Tuple

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
        token_provider: Callable[[], str],
        max_retries: int = 3,
        timeout: int = 30,
        verify_ssl: bool = True,
        debug_mode: bool = False,
        concurrent_requests: int = 3
    ):
        """
        Initialize the FHIR client.

        Args:
            base_url: Base URL for the FHIR API
            token_provider: Callable that returns a valid token
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            debug_mode: Whether to enable detailed debug logging
            concurrent_requests: Maximum number of concurrent requests
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

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get the access token, refreshing if needed.
        
        Args:
            force_refresh: Whether to force a token refresh
            
        Returns:
            Access token
        """
        if self._token is None or force_refresh:
            logger.debug("Getting fresh token" + (" (forced)" if force_refresh else ""))
            self._token = self.token_provider()
            if not self._token:
                logger.error("Token provider returned empty token")
                raise FHIRAuthError("Failed to get valid token")
        return self._token

    def _get_headers(self, force_token_refresh: bool = False) -> Dict[str, str]:
        """
        Get headers with current auth token.
        
        Args:
            force_token_refresh: Whether to force a token refresh
            
        Returns:
            Headers dict
        """
        try:
            token = self.get_token(force_refresh=force_token_refresh)
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
        (requests.exceptions.RequestException, FHIRRateLimitError, FHIROperationOutcomeError),
        max_tries=3,
        giveup=lambda e: (
            isinstance(e, requests.exceptions.HTTPError) and 
            e.response is not None and 
            e.response.status_code in [400, 403, 404]
        ) or (
            isinstance(e, FHIROperationOutcomeError) and
            not e.details.get("retriable", False)
        ),
        on_backoff=lambda details: logger.debug(
            f"Retrying request after {details['wait']:.2f}s. Attempt {details['tries']}"
        )
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        force_token_refresh: bool = False,
    ) -> requests.Response:
        """
        Make a request to the FHIR API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body for POST/PUT
            force_token_refresh: Whether to force a token refresh

        Returns:
            Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(force_token_refresh=force_token_refresh)
        self.request_count += 1
        
        logger.debug(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Request params: {params}")
        if data and self.debug_mode:
            logger.debug(f"Request data: {json.dumps(data, indent=2)[:500]}...")
            
        start_time = time.time()

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Request completed in {elapsed:.3f}s with status {response.status_code}")

            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"Rate limit exceeded. Retry after {retry_after} seconds")
                self.rate_limit_count += 1
                self._log_request(method, url, params, start_time, response, 
                                 error=f"Rate limit exceeded, retry after {retry_after}s")
                time.sleep(retry_after)
                raise FHIRRateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")

            # Token might be expired
            if response.status_code == 401:
                logger.warning("Authentication failed. Token might be expired.")
                self.auth_error_count += 1
                
                if not force_token_refresh:
                    # Try again with a fresh token
                    logger.debug("Retrying with fresh token")
                    return self._make_request(
                        method, endpoint, params, data, force_token_refresh=True
                    )
                else:
                    # Already tried with a fresh token
                    self._log_request(method, url, params, start_time, response, 
                                     error="Authentication failed even with fresh token")
                    response.raise_for_status()

            # Check for OperationOutcome errors
            self._check_for_operation_outcome(response)

            # Log response details for any non-200 status
            if response.status_code != 200:
                logger.warning(f"Non-200 status code: {response.status_code} for {url}")
                if self.debug_mode:
                    try:
                        logger.debug(f"Response headers: {dict(response.headers)}")
                        logger.debug(f"Response content: {response.text[:500]}...")
                    except:
                        pass

            # Check for server errors
            response.raise_for_status()
            
            # Log successful request
            self._log_request(method, url, params, start_time, response)
            
            # Parse response for debugging
            if self.debug_mode:
                try:
                    response_size = len(response.content)
                    response_data = response.json()
                    if "resourceType" in response_data:
                        resource_type = response_data.get("resourceType", "Unknown")
                        entry_count = len(response_data.get("entry", [])) if resource_type == "Bundle" else 1
                        logger.debug(f"Received {resource_type} with {entry_count} entries, size: {response_size} bytes")
                except:
                    pass

            return response

        except (FHIRAuthError, FHIRRateLimitError, FHIROperationOutcomeError):
            # Let these be handled by the backoff decorator
            self.error_count += 1
            raise

        except requests.exceptions.RequestException as e:
            self.error_count += 1
            elapsed = time.time() - start_time
            logger.error(f"Request failed after {elapsed:.3f}s: {str(e)}")
            
            # Log detailed error info
            self._log_request(method, url, params, start_time, error=e)
            
            if hasattr(e, 'response') and e.response:
                try:
                    logger.debug(f"Error response status: {e.response.status_code}")
                    logger.debug(f"Error response headers: {dict(e.response.headers)}")
                    logger.debug(f"Error response content: {e.response.text[:500]}...")
                    
                    # Check for OperationOutcome in error response
                    try:
                        self._check_for_operation_outcome(e.response)
                    except FHIROperationOutcomeError:
                        # Re-raise to be handled by backoff
                        raise
                except:
                    pass
                    
            logger.debug(f"Error details: {traceback.format_exc()}")
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
                endpoint = parsed_url.path.replace(self.base_url, "").lstrip("/")
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
            token = self.get_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make async request
            try:
                query_params = params.copy()
                
                # If it's an absolute URL, parse the params from it
                if next_url.startswith(self.base_url):
                    parsed_url = urllib.parse.urlparse(next_url)
                    query_dict = urllib.parse.parse_qs(parsed_url.query)
                    # Convert lists to single values
                    query_params = {k: v[0] for k, v in query_dict.items()}
                    next_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                
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
                        self.get_token(force_refresh=True)
                        continue
                        
                    response.raise_for_status()
                    
                    # Parse response
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                self.get_patient_resources_for_multiple_types(
                    patient_id, resource_types, additional_params, page_size
                )
            )
            
            # Close the event loop
            loop.run_until_complete(self.async_session.close())
            return results
        finally:
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