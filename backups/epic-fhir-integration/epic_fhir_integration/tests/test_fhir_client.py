"""
Unit tests for the FHIR client.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import asyncio
import urllib.parse

import pytest
import requests
import responses

from fhir_pipeline.io.fhir_client import (
    FHIRClient, 
    FHIRAuthError, 
    FHIRRateLimitError, 
    FHIROperationOutcomeError
)

# Import for async tests
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class TestFHIRClient(unittest.TestCase):
    """Tests for the FHIR client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "https://fhir.example.com/api/FHIR/R4"
        self.token_provider = lambda: "test-token"
    
    def test_init(self):
        """Test client initialization."""
        client = FHIRClient(self.base_url, self.token_provider)
        self.assertEqual(client.base_url, self.base_url)
        self.assertEqual(client._token, None)  # Token not fetched until needed
    
    def test_get_token(self):
        """Test token fetching."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Token should be fetched on first call
        token = client.get_token()
        self.assertEqual(token, "test-token")
        self.assertEqual(client._token, "test-token")
        
        # Subsequent calls should use cached token
        with patch.object(client, 'token_provider') as mock_provider:
            token = client.get_token()
            self.assertEqual(token, "test-token")
            mock_provider.assert_not_called()
        
        # Force refresh should call provider again
        with patch.object(client, 'token_provider', return_value="new-token") as mock_provider:
            token = client.get_token(force_refresh=True)
            self.assertEqual(token, "new-token")
            self.assertEqual(client._token, "new-token")
            mock_provider.assert_called_once()
    
    def test_get_headers(self):
        """Test header generation."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        headers = client._get_headers()
        self.assertEqual(headers, {"Authorization": "Bearer test-token"})
        
        # Force token refresh
        with patch.object(client, 'token_provider', return_value="new-token"):
            headers = client._get_headers(force_token_refresh=True)
            self.assertEqual(headers, {"Authorization": "Bearer new-token"})
    
    @responses.activate
    def test_check_for_operation_outcome_success(self):
        """Test operation outcome check with successful response."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Mock a successful response
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": []
        }).encode()
        
        # Should not raise
        try:
            client._check_for_operation_outcome(response)
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")
    
    @responses.activate
    def test_check_for_operation_outcome_error(self):
        """Test operation outcome check with error response."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Mock an error response
        response = requests.Response()
        response.status_code = 400
        response._content = json.dumps({
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "error",
                    "code": "invalid",
                    "details": {
                        "text": "Invalid request"
                    }
                }
            ]
        }).encode()
        
        # Should raise FHIROperationOutcomeError
        with self.assertRaises(FHIROperationOutcomeError) as context:
            client._check_for_operation_outcome(response)
        
        self.assertIn("invalid: Invalid request", str(context.exception))
        self.assertEqual(client.outcome_error_count, 1)
    
    @responses.activate
    def test_make_request_success(self):
        """Test successful request."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Mock successful response
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"resourceType": "Patient", "id": "123"},
            status=200
        )
        
        response = client._make_request("GET", "Patient/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"resourceType": "Patient", "id": "123"})
        self.assertEqual(client.request_count, 1)
        self.assertEqual(client.error_count, 0)
    
    @responses.activate
    def test_make_request_401_with_retry(self):
        """Test 401 response with token refresh retry."""
        def token_provider_mock():
            token_provider_mock.calls += 1
            return f"token-{token_provider_mock.calls}"
        
        token_provider_mock.calls = 0
        
        client = FHIRClient(self.base_url, token_provider_mock)
        
        # First call returns 401, second call succeeds
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"error": "Unauthorized"},
            status=401
        )
        
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"resourceType": "Patient", "id": "123"},
            status=200
        )
        
        response = client._make_request("GET", "Patient/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"resourceType": "Patient", "id": "123"})
        self.assertEqual(client.request_count, 2)  # Initial request + retry
        self.assertEqual(client.auth_error_count, 1)
    
    @responses.activate
    def test_make_request_rate_limit(self):
        """Test rate limit response."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Mock rate limit response
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"error": "Rate limit exceeded"},
            status=429,
            headers={"Retry-After": "1"}
        )
        
        # Second request succeeds
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"resourceType": "Patient", "id": "123"},
            status=200
        )
        
        # Should retry after delay
        with patch('time.sleep') as mock_sleep:
            response = client._make_request("GET", "Patient/123")
            
            # Check that sleep was called at least once, and one of the calls was with value 1
            # (the backoff decorator may also add additional sleep calls)
            self.assertTrue(mock_sleep.called, "sleep should be called at least once")
            sleep_values = [call[0][0] for call in mock_sleep.call_args_list]
            self.assertIn(1, sleep_values, "sleep should be called with value 1 (Retry-After value)")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.rate_limit_count, 1)
    
    @responses.activate
    def test_make_request_operation_outcome_retriable(self):
        """Test retriable OperationOutcome error."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # First response has retriable OperationOutcome
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "timeout",
                        "details": {"text": "Request timed out"}
                    }
                ]
            },
            status=200
        )
        
        # Second request succeeds
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={"resourceType": "Patient", "id": "123"},
            status=200
        )
        
        response = client._make_request("GET", "Patient/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"resourceType": "Patient", "id": "123"})
        self.assertEqual(client.outcome_error_count, 1)
    
    @responses.activate
    def test_make_request_operation_outcome_non_retriable(self):
        """Test non-retriable OperationOutcome error."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # Response has non-retriable OperationOutcome
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient/123",
            json={
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "invalid",
                        "details": {"text": "Invalid request"}
                    }
                ]
            },
            status=200
        )
        
        with self.assertRaises(FHIROperationOutcomeError):
            client._make_request("GET", "Patient/123")
        
        self.assertEqual(client.outcome_error_count, 1)
    
    @responses.activate
    def test_search_resource(self):
        """Test resource search."""
        client = FHIRClient(self.base_url, self.token_provider)
        
        # First page
        first_page = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 2,
            "link": [
                {
                    "relation": "next",
                    "url": f"{self.base_url}/Patient?_page=2"
                }
            ],
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "1"}}
            ]
        }
        
        # Second page
        second_page = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 2,
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "2"}}
            ]
        }
        
        # Instead of using responses, let's mock the _make_request method
        # to avoid issues with URL matching
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = first_page
        mock_resp1.status_code = 200
        
        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = second_page
        mock_resp2.status_code = 200
        
        with patch.object(client, '_make_request') as mock_make_request:
            mock_make_request.side_effect = [mock_resp1, mock_resp2]
            
            results = list(client.search_resource("Patient"))
            
            # Verify the results
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["entry"][0]["resource"]["id"], "1")  
            self.assertEqual(results[1]["entry"][0]["resource"]["id"], "2")
            
            # Verify make_request was called with the right parameters
            self.assertEqual(mock_make_request.call_count, 2)
            
            # First call should be for Patient endpoint
            first_call = mock_make_request.call_args_list[0]
            self.assertEqual(first_call[0][0], "GET")  
            self.assertEqual(first_call[0][1], "Patient")
            
            # Second call should have a query param for _page=2
            second_call = mock_make_request.call_args_list[1]
            self.assertEqual(second_call[0][0], "GET")  # Method is GET
            
            # Check if _page is in the params (might be in kwargs as 'params')
            if len(second_call[0]) > 2 and isinstance(second_call[0][2], dict):
                # Params passed as positional arg
                self.assertIn("_page", second_call[0][2])
                self.assertEqual(second_call[0][2]["_page"], "2")
            elif 'params' in second_call[1]:
                # Params passed as keyword arg
                self.assertIn("_page", second_call[1]['params'])
                self.assertEqual(second_call[1]['params']["_page"], "2")
            else:
                self.fail("No params found in second call")


@pytest.mark.asyncio
async def test_search_resource_async():
    """Test async resource search."""
    # Skip if aiohttp is not available
    if not HAS_AIOHTTP:
        pytest.skip("aiohttp is not available")
        
    base_url = "https://fhir.example.com/api/FHIR/R4"
    token_provider = lambda: "test-token"
    client = FHIRClient(base_url, token_provider)
    
    # Create a bundle to return
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 1,
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "1"}}
        ]
    }
    
    # Mock the async session
    mock_session = MagicMock()
    
    # Mock the context manager returned by session.get
    mock_response = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__.return_value = mock_response
    mock_session.get.return_value = mock_context
    
    # Set response attributes
    mock_response.status = 200
    
    # Create an awaitable for the json method
    async def mock_json():
        return bundle
    
    # Set json method to return the awaitable
    mock_response.json = mock_json
    
    # Patch the session creation
    with patch.object(client, '_create_async_session', return_value=mock_session):
        results = await client.search_resource_async("Patient")
        
        assert len(results) == 1
        assert results[0]["entry"][0]["resource"]["id"] == "1"
        mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_patient_resources_for_multiple_types():
    """Test fetching multiple resource types."""
    base_url = "https://fhir.example.com/api/FHIR/R4"
    token_provider = lambda: "test-token"
    client = FHIRClient(base_url, token_provider)
    
    # Mock the search_resource_async method
    async def mock_search(resource_type, *args, **kwargs):
        return [{
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {"resource": {"resourceType": resource_type, "id": "1"}}
            ]
        }]
    
    with patch.object(client, 'search_resource_async', side_effect=mock_search):
        results = await client.get_patient_resources_for_multiple_types(
            "test-patient",
            ["Patient", "Encounter"]
        )
        
        assert len(results) == 2
        assert "Patient" in results
        assert "Encounter" in results
        assert len(results["Patient"]) == 1
        assert len(results["Encounter"]) == 1


def test_extract_patient_resources_parallel():
    """Test parallel resource extraction."""
    # Skip if asyncio is not available
    if not HAS_AIOHTTP:
        pytest.skip("aiohttp is not available")
        
    base_url = "https://fhir.example.com/api/FHIR/R4"
    token_provider = lambda: "test-token"
    client = FHIRClient(base_url, token_provider)
    
    # Mock the async method
    async def mock_get_resources(*args, **kwargs):
        return {
            "Patient": [{
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 1,
                "entry": [
                    {"resource": {"resourceType": "Patient", "id": "1"}}
                ]
            }],
            "Encounter": [{
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 1,
                "entry": [
                    {"resource": {"resourceType": "Encounter", "id": "1"}}
                ]
            }]
        }
    
    # Mock asyncio.run_until_complete to simply execute the coroutine directly
    def run_coro(coro):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    mock_loop = MagicMock()
    mock_loop.run_until_complete.side_effect = run_coro
    
    with patch('asyncio.new_event_loop', return_value=mock_loop), \
         patch('asyncio.set_event_loop'), \
         patch.object(client, 'get_patient_resources_for_multiple_types', mock_get_resources), \
         patch.object(mock_loop, 'close'):  # To avoid actually closing the loop
        
        results = client.extract_patient_resources_parallel(
            "test-patient",
            ["Patient", "Encounter"]
        )
        
        assert len(results) == 2
        assert "Patient" in results
        assert "Encounter" in results
        assert len(results["Patient"]) == 1
        assert len(results["Encounter"]) == 1 