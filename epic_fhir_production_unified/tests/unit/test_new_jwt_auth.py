"""
Unit tests for the JWT authentication module.
"""

import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock

import jwt
import pytest
import requests

from epic_fhir_integration.auth.jwt_auth import (
    build_jwt,
    exchange_for_access_token,
    token_needs_refresh,
    get_or_refresh_token,
    get_token_with_retry,
)


class TestJWTAuth:
    """Test suite for JWT authentication module."""

    @patch('epic_fhir_integration.config.loader.get_config')
    @patch('epic_fhir_integration.security.secret_store.load_secret')
    def test_build_jwt(self, mock_load_secret, mock_get_config):
        """Test building a JWT token."""
        # Mock config and private key
        mock_get_config.return_value = {
            "client_id": "test-client",
            "jwt_issuer": "test-issuer",
            "epic_base_url": "https://example.org/epic"
        }
        
        mock_secret_value = MagicMock()
        mock_secret_value.get.return_value = "test-private-key"
        mock_load_secret.return_value = mock_secret_value
        
        # Mock jwt.encode
        with patch('jwt.encode', return_value="test-jwt-token") as mock_encode:
            # Call the function
            token = build_jwt()
            
            # Verify the JWT was created with the right parameters
            assert token == "test-jwt-token"
            
            # Verify the private key was loaded
            mock_load_secret.assert_called_once_with("epic_private_key.pem")
            
            # Verify the JWT claims
            args, kwargs = mock_encode.call_args
            claims, private_key = args
            
            assert claims["iss"] == "test-issuer"
            assert claims["sub"] == "test-client"
            assert claims["aud"] == "https://example.org/epic/oauth2/token"
            assert "jti" in claims
            assert "iat" in claims
            assert "exp" in claims
            assert claims["exp"] > claims["iat"]
            
            assert private_key == "test-private-key"
            assert kwargs["algorithm"] == "RS384"

    @patch('epic_fhir_integration.config.loader.get_config')
    def test_build_jwt_missing_config(self, mock_get_config):
        """Test building a JWT token with missing configuration."""
        # Mock missing config
        mock_get_config.return_value = {}
        
        # Call the function and verify it raises ValueError
        with pytest.raises(ValueError, match="Missing 'auth' configuration section"):
            build_jwt()

    @patch('epic_fhir_integration.config.loader.get_config')
    def test_build_jwt_incomplete_config(self, mock_get_config):
        """Test building a JWT token with incomplete configuration."""
        # Mock incomplete config
        mock_get_config.return_value = {"client_id": "test-client"}
        
        # Call the function and verify it raises ValueError
        with pytest.raises(ValueError, match="Missing required configuration"):
            build_jwt()

    @patch('epic_fhir_integration.config.loader.get_config')
    @patch('requests.post')
    def test_exchange_for_access_token(self, mock_post, mock_get_config):
        """Test exchanging a JWT token for an access token."""
        # Mock config
        mock_get_config.return_value = {
            "epic_base_url": "https://example.org/epic"
        }
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response
        
        # Call the function
        token_data = exchange_for_access_token("test-jwt-token")
        
        # Verify the token was exchanged
        assert token_data["access_token"] == "test-access-token"
        assert token_data["expires_in"] == 3600
        assert "expiration_timestamp" in token_data
        
        # Verify the request was made correctly
        mock_post.assert_called_once_with(
            "https://example.org/epic/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": "test-jwt-token",
            }
        )

    @patch('epic_fhir_integration.config.loader.get_config')
    @patch('requests.post')
    def test_exchange_for_access_token_failure(self, mock_post, mock_get_config):
        """Test handling errors when exchanging a JWT token."""
        # Mock config
        mock_get_config.return_value = {
            "epic_base_url": "https://example.org/epic"
        }
        
        # Mock failed response
        mock_post.side_effect = requests.RequestException("Failed request")
        
        # Call the function and verify it raises the exception
        with pytest.raises(requests.RequestException):
            exchange_for_access_token("test-jwt-token")

    def test_token_needs_refresh_no_expiration(self):
        """Test token refresh check with no expiration timestamp."""
        # Call the function with token data that has no expiration
        result = token_needs_refresh({})
        
        # Verify it returns True (needs refresh)
        assert result is True

    @patch('datetime.datetime')
    def test_token_needs_refresh_expired(self, mock_datetime):
        """Test token refresh check with an expired token."""
        # Mock current time
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1000  # Current time
        mock_datetime.now.return_value = mock_now
        
        # Token expired 10 seconds ago
        token_data = {"expiration_timestamp": 990}
        
        # Call the function
        result = token_needs_refresh(token_data)
        
        # Verify it returns True (needs refresh)
        assert result is True

    @patch('datetime.datetime')
    def test_token_needs_refresh_buffer(self, mock_datetime):
        """Test token refresh check with token in buffer period."""
        # Mock current time
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1000  # Current time
        mock_datetime.now.return_value = mock_now
        
        # Token expires in 200 seconds (within the 5-minute buffer)
        token_data = {"expiration_timestamp": 1200}
        
        # Call the function
        result = token_needs_refresh(token_data)
        
        # Verify it returns True (needs refresh)
        assert result is True

    @patch('datetime.datetime')
    def test_token_needs_refresh_valid(self, mock_datetime):
        """Test token refresh check with a valid token."""
        # Mock current time
        mock_now = MagicMock()
        mock_now.timestamp.return_value = 1000  # Current time
        mock_datetime.now.return_value = mock_now
        
        # Token expires in 600 seconds (outside the 5-minute buffer)
        token_data = {"expiration_timestamp": 1600}
        
        # Call the function
        result = token_needs_refresh(token_data)
        
        # Verify it returns False (doesn't need refresh)
        assert result is False

    @patch('epic_fhir_integration.security.secret_store.load_secret')
    @patch('epic_fhir_integration.auth.jwt_auth.build_jwt')
    @patch('epic_fhir_integration.auth.jwt_auth.exchange_for_access_token')
    @patch('epic_fhir_integration.security.secret_store.save_secret')
    def test_get_or_refresh_token_existing_valid(self, mock_save_secret, mock_exchange, mock_build_jwt, mock_load_secret):
        """Test getting a token that already exists and is valid."""
        # Mock an existing valid token
        mock_secret = MagicMock()
        mock_secret.get.return_value = {
            "access_token": "existing-token",
            "expiration_timestamp": time.time() + 3600  # Far in the future
        }
        mock_load_secret.return_value = mock_secret
        
        # Call the function
        token = get_or_refresh_token()
        
        # Verify the existing token was returned
        assert token == "existing-token"
        
        # Verify no new token was created
        assert not mock_build_jwt.called
        assert not mock_exchange.called
        assert not mock_save_secret.called

    @patch('epic_fhir_integration.security.secret_store.load_secret')
    @patch('epic_fhir_integration.auth.jwt_auth.build_jwt')
    @patch('epic_fhir_integration.auth.jwt_auth.exchange_for_access_token')
    @patch('epic_fhir_integration.security.secret_store.save_secret')
    def test_get_or_refresh_token_existing_expired(self, mock_save_secret, mock_exchange, mock_build_jwt, mock_load_secret):
        """Test refreshing a token that exists but is expired."""
        # Mock an existing expired token
        mock_secret = MagicMock()
        mock_secret.get.return_value = {
            "access_token": "expired-token",
            "expiration_timestamp": time.time() - 60  # In the past
        }
        mock_load_secret.return_value = mock_secret
        
        # Mock building and exchanging a new token
        mock_build_jwt.return_value = "new-jwt-token"
        mock_exchange.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600
        }
        
        # Call the function
        token = get_or_refresh_token()
        
        # Verify a new token was created and returned
        assert token == "new-access-token"
        
        # Verify the token was built, exchanged, and saved
        mock_build_jwt.assert_called_once()
        mock_exchange.assert_called_once_with("new-jwt-token")
        mock_save_secret.assert_called_once()

    @patch('epic_fhir_integration.security.secret_store.load_secret')
    @patch('epic_fhir_integration.auth.jwt_auth.build_jwt')
    @patch('epic_fhir_integration.auth.jwt_auth.exchange_for_access_token')
    @patch('epic_fhir_integration.security.secret_store.save_secret')
    def test_get_or_refresh_token_nonexistent(self, mock_save_secret, mock_exchange, mock_build_jwt, mock_load_secret):
        """Test creating a new token when none exists."""
        # Mock a missing token
        mock_load_secret.side_effect = FileNotFoundError("No token file")
        
        # Mock building and exchanging a new token
        mock_build_jwt.return_value = "new-jwt-token"
        mock_exchange.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600
        }
        
        # Call the function
        token = get_or_refresh_token()
        
        # Verify a new token was created and returned
        assert token == "new-access-token"
        
        # Verify the token was built, exchanged, and saved
        mock_build_jwt.assert_called_once()
        mock_exchange.assert_called_once_with("new-jwt-token")
        mock_save_secret.assert_called_once()

    @patch('epic_fhir_integration.auth.jwt_auth.get_or_refresh_token')
    def test_get_token_with_retry_success(self, mock_get_token):
        """Test getting a token with retry (success on first try)."""
        # Mock successful token retrieval
        mock_get_token.return_value = "test-token"
        
        # Call the function
        token = get_token_with_retry()
        
        # Verify the token was returned
        assert token == "test-token"
        
        # Verify only one attempt was made
        assert mock_get_token.call_count == 1

    @patch('epic_fhir_integration.auth.jwt_auth.get_or_refresh_token')
    @patch('time.sleep')
    def test_get_token_with_retry_failure_then_success(self, mock_sleep, mock_get_token):
        """Test getting a token with retry (failure then success)."""
        # Mock token retrieval to fail once then succeed
        mock_get_token.side_effect = [
            requests.RequestException("First failure"),
            "test-token"
        ]
        
        # Call the function
        token = get_token_with_retry()
        
        # Verify the token was returned after retry
        assert token == "test-token"
        
        # Verify two attempts were made
        assert mock_get_token.call_count == 2
        
        # Verify sleep was called once
        mock_sleep.assert_called_once()

    @patch('epic_fhir_integration.auth.jwt_auth.get_or_refresh_token')
    @patch('time.sleep')
    def test_get_token_with_retry_all_failures(self, mock_sleep, mock_get_token):
        """Test getting a token with retry (all attempts fail)."""
        # Mock all token retrieval attempts to fail
        mock_get_token.side_effect = [
            requests.RequestException("First failure"),
            requests.RequestException("Second failure"),
            requests.RequestException("Third failure")
        ]
        
        # Call the function and verify it raises RuntimeError
        with pytest.raises(RuntimeError):
            get_token_with_retry(max_retries=3)
        
        # Verify three attempts were made
        assert mock_get_token.call_count == 3
        
        # Verify sleep was called twice
        assert mock_sleep.call_count == 2 