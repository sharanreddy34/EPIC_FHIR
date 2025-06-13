"""
Unit tests for the FHIR client.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

import pytest
import requests
import responses

from fhir_pipeline.io.fhir_client import (
    FHIRClient, 
    FHIRAuthError, 
    FHIRRateLimitError, 
    FHIROperationOutcomeError
)


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
            mock_sleep.assert_called_with(1)
        
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
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient",
            json={
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
            },
            status=200
        )
        
        # Second page
        responses.add(
            responses.GET,
            f"{self.base_url}/Patient",
            json={
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 2,
                "entry": [
                    {"resource": {"resourceType": "Patient", "id": "2"}}
                ]
            },
            status=200,
            match=[responses.matchers.query_param_matcher({"_page": "2"})]
        )
        
        results = list(client.search_resource("Patient"))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["entry"][0]["resource"]["id"], "1")
        self.assertEqual(results[1]["entry"][0]["resource"]["id"], "2")
        self.assertEqual(client.request_count, 2)


@pytest.mark.asyncio
async def test_search_resource_async():
    """Test async resource search."""
    base_url = "https://fhir.example.com/api/FHIR/R4"
    token_provider = lambda: "test-token"
    client = FHIRClient(base_url, token_provider)
    
    # Mock session and response
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.json.return_value = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 1,
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "1"}}
        ]
    }
    mock_session.get.return_value = mock_response
    
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
    
    # Mock asyncio.run_until_complete
    mock_loop = MagicMock()
    mock_loop.run_until_complete.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(coro)
    
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