"""
Unit tests for JWT authentication in the FHIR pipeline.
"""

import os
import json
import pytest
import time
from unittest.mock import patch, MagicMock, mock_open

import requests

from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.auth.token_manager import TokenManager
from fhir_pipeline.utils.retry import retry_with_backoff, RetryableError

# Mock JWT token for testing
MOCK_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
MOCK_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj
MzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvu
NMoSfm76oqFvAp8Gy0iz5sxjZmSnXyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZ
agUv34mahQxsTQiBma3nwj/C+QVWM+2Mx0uG0kPbQxh3/8/4FX8sj45QV82Qjk5C
-----END PRIVATE KEY-----"""


class TestJWTClient:
    """Test suite for JWTClient."""

    @patch('requests.post')
    def test_get_token_success(self, mock_post):
        """Test successful token retrieval."""
        # Mock response for successful token request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": MOCK_JWT_TOKEN,
            "expires_in": 300,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response

        # Create JWTClient and get token
        client = JWTClient(client_id="test-client", private_key=MOCK_PRIVATE_KEY)
        token = client.get_token()

        # Verify token and expiration
        assert token == MOCK_JWT_TOKEN
        assert client.token_expiration > time.time()
        assert mock_post.called

    @patch('requests.post')
    def test_get_token_failure(self, mock_post):
        """Test token retrieval failure."""
        # Mock response for failed token request
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid_client"}
        mock_post.return_value = mock_response

        # Create JWTClient and attempt to get token
        client = JWTClient(client_id="test-client", private_key=MOCK_PRIVATE_KEY)
        
        # Should raise exception on failure
        with pytest.raises(Exception):
            client.get_token()

    @patch('requests.post')
    def test_token_caching(self, mock_post):
        """Test that tokens are cached until expiration."""
        # Mock response for successful token request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": MOCK_JWT_TOKEN,
            "expires_in": 300,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response

        # Create JWTClient and get token multiple times
        client = JWTClient(client_id="test-client", private_key=MOCK_PRIVATE_KEY)
        token1 = client.get_token()
        token2 = client.get_token()  # Should use cached token

        # Verify token and that request was only made once
        assert token1 == token2 == MOCK_JWT_TOKEN
        assert mock_post.call_count == 1

    @patch('requests.post')
    def test_token_expiration(self, mock_post):
        """Test that expired tokens are refreshed."""
        # Mock response for successful token request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": MOCK_JWT_TOKEN,
            "expires_in": 300,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response

        # Create JWTClient and get token
        client = JWTClient(client_id="test-client", private_key=MOCK_PRIVATE_KEY)
        token1 = client.get_token()
        
        # Simulate token expiration
        client.token_expiration = time.time() - 10
        
        # Get token again (should request a new one)
        token2 = client.get_token()
        
        # Verify token and that request was made twice
        assert token1 == token2 == MOCK_JWT_TOKEN
        assert mock_post.call_count == 2


class TestTokenManager:
    """Test suite for TokenManager."""

    def test_get_token_from_client(self):
        """Test that TokenManager gets token from client."""
        # Create mock token client
        mock_client = MagicMock()
        mock_client.get_token.return_value = MOCK_JWT_TOKEN
        
        # Create TokenManager and get token
        manager = TokenManager(token_client=mock_client)
        token = manager.get_token()
        
        # Verify token and that client was called
        assert token == MOCK_JWT_TOKEN
        assert mock_client.get_token.called

    def test_get_cached_token(self):
        """Test that TokenManager caches tokens."""
        # Create mock token client
        mock_client = MagicMock()
        mock_client.get_token.return_value = MOCK_JWT_TOKEN
        
        # Create TokenManager and get token multiple times
        manager = TokenManager(token_client=mock_client)
        token1 = manager.get_token()
        token2 = manager.get_token()  # Should use cached token
        
        # Verify token and that client was called only once
        assert token1 == token2 == MOCK_JWT_TOKEN
        assert mock_client.get_token.call_count == 1

    @patch('time.time')
    def test_refresh_expired_token(self, mock_time):
        """Test that TokenManager refreshes expired tokens."""
        # Create mock token client
        mock_client = MagicMock()
        mock_client.get_token.return_value = MOCK_JWT_TOKEN
        
        # Mock time to control token expiration
        mock_time.return_value = 1000  # Initial time
        
        # Create TokenManager and get token
        manager = TokenManager(token_client=mock_client)
        token1 = manager.get_token()
        
        # Advance time past token expiration
        mock_time.return_value = 2000  # Time after expiration
        
        # Get token again (should request a new one)
        token2 = manager.get_token()
        
        # Verify token and that client was called twice
        assert token1 == token2 == MOCK_JWT_TOKEN
        assert mock_client.get_token.call_count == 2


@patch('requests.post')
def test_retry_with_backoff(mock_post):
    """Test the retry_with_backoff decorator."""
    # Mock responses that fail twice then succeed
    mock_responses = [
        MagicMock(status_code=429),  # Rate limited
        MagicMock(status_code=500),  # Server error
        MagicMock(status_code=200, json=lambda: {"access_token": MOCK_JWT_TOKEN})  # Success
    ]
    mock_post.side_effect = mock_responses
    
    # Define test function with retry
    @retry_with_backoff(retries=3, backoff_in_seconds=0.1)
    def get_token():
        response = requests.post("https://example.org/token")
        if response.status_code != 200:
            raise RetryableError(f"Failed with status {response.status_code}")
        return response.json()["access_token"]
    
    # Call function and verify it succeeds after retries
    token = get_token()
    assert token == MOCK_JWT_TOKEN
    assert mock_post.call_count == 3 