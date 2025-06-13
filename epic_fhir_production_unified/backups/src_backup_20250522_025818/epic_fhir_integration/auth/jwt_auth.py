"""
JWT authentication module for Epic FHIR API integration.

This module provides functions to handle JWT-based authentication with Epic's FHIR API,
including token generation, exchange, refresh, and retry logic.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import jwt
import requests

from epic_fhir_integration.config.loader import get_config
from epic_fhir_integration.security.secret_store import (
    load_secret, save_secret, SecretValue
)


def build_jwt(private_key_name: str = "epic_private_key.pem") -> str:
    """Build a JWT token for authentication with Epic.
    
    Args:
        private_key_name: Name of the private key file in the secrets directory.
        
    Returns:
        JWT token string.
        
    Raises:
        FileNotFoundError: If the private key file doesn't exist.
        ValueError: If the configuration is invalid.
    """
    # Load configuration
    auth_config = get_config("auth")
    if not auth_config:
        raise ValueError("Missing 'auth' configuration section")
    
    required_fields = ["client_id", "jwt_issuer", "epic_base_url"]
    missing_fields = [field for field in required_fields if field not in auth_config]
    if missing_fields:
        raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
    
    # Load private key
    private_key = load_secret(private_key_name).get()
    
    # Prepare JWT claims
    now = int(time.time())
    expiration = now + 300  # 5 minutes
    
    claims = {
        "iss": auth_config["jwt_issuer"],
        "sub": auth_config["client_id"],
        "aud": f"{auth_config['epic_base_url']}/oauth2/token",
        "jti": str(int(time.time() * 1000)),  # Unique ID based on timestamp
        "iat": now,
        "exp": expiration,
    }
    
    # Sign JWT
    return jwt.encode(claims, private_key, algorithm="RS384")


def exchange_for_access_token(jwt_token: str) -> Dict:
    """Exchange a JWT token for an access token.
    
    Args:
        jwt_token: JWT token string.
        
    Returns:
        Dictionary containing the access token response.
        
    Raises:
        requests.RequestException: If the token exchange fails.
    """
    auth_config = get_config("auth")
    if not auth_config:
        raise ValueError("Missing 'auth' configuration section")
    
    token_url = f"{auth_config['epic_base_url']}/oauth2/token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": jwt_token,
    }
    
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    
    token_data = response.json()
    
    # Add expiration timestamp to the token data
    if "expires_in" in token_data:
        expiration_time = datetime.now() + timedelta(seconds=token_data["expires_in"])
        token_data["expiration_timestamp"] = expiration_time.timestamp()
    
    return token_data


def token_needs_refresh(token_data: Dict) -> bool:
    """Check if a token needs to be refreshed.
    
    Args:
        token_data: Token data dictionary.
        
    Returns:
        True if the token needs to be refreshed, False otherwise.
    """
    # If there's no expiration timestamp, assume we need to refresh
    if "expiration_timestamp" not in token_data:
        return True
    
    # Add a 5-minute buffer to ensure we refresh before expiration
    buffer_seconds = 300  # 5 minutes
    current_time = datetime.now().timestamp()
    
    return current_time + buffer_seconds >= token_data["expiration_timestamp"]


def get_or_refresh_token(token_file_name: str = "epic_token.json") -> str:
    """Get a valid access token, refreshing if necessary.
    
    Args:
        token_file_name: Name of the token file in the secrets directory.
        
    Returns:
        Valid access token string.
    """
    try:
        # Try to load existing token
        token_data = load_secret(token_file_name).get()
    except FileNotFoundError:
        # No existing token, get a new one
        token_data = {}
    
    # Check if token needs refresh
    if token_needs_refresh(token_data):
        # Build JWT and exchange for access token
        jwt_token = build_jwt()
        token_data = exchange_for_access_token(jwt_token)
        
        # Save the new token
        save_secret(token_file_name, token_data)
    
    return token_data["access_token"]


def get_token_with_retry(max_retries: int = 3, backoff_factor: float = 1.5) -> str:
    """Get a valid access token with retry and exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff.
        
    Returns:
        Valid access token string.
        
    Raises:
        RuntimeError: If all retry attempts fail.
    """
    last_error = None
    delay = 1.0  # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            return get_or_refresh_token()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            
            if attempt < max_retries - 1:
                # Wait with exponential backoff before retrying
                time.sleep(delay)
                delay *= backoff_factor
    
    # All retry attempts failed
    raise RuntimeError(f"Failed to obtain token after {max_retries} attempts: {last_error}") 