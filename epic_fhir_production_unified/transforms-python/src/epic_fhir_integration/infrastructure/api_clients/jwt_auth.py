"""
JWT authentication module for Epic FHIR API integration.

This module provides functions to handle JWT-based authentication with Epic's FHIR API,
including token generation, exchange, refresh, and retry logic.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)

# Cache for token data
_token_cache = {}


def get_secret(name: str) -> str:
    """Get a secret from Foundry's secret manager or environment variables.
    
    This function provides a unified approach to secrets that works both in 
    Foundry and local development environments.
    
    Args:
        name: Secret name
        
    Returns:
        Secret value
        
    Raises:
        ValueError: If the secret is not found in any source
    """
    # Try Foundry's Secret API first
    try:
        from transforms.api import Secret
        return Secret(name).get()
    except (ImportError, Exception) as e:
        logger.debug(f"Could not get secret {name} from Foundry, trying environment", error=str(e))
    
    # Fall back to environment variables
    env_value = os.environ.get(name)
    if env_value:
        return env_value
    
    # If still nothing, raise error
    raise ValueError(f"Secret {name} not found in Foundry secrets or environment variables")


def build_jwt() -> str:
    """Build a JWT token for authentication with Epic.
    
    Returns:
        JWT token string.
        
    Raises:
        ValueError: If the configuration is invalid.
    """
    # Load private key and client ID from secrets
    private_key = get_secret("EPIC_PRIVATE_KEY")
    client_id = get_secret("EPIC_CLIENT_ID")
    
    # Get Epic base URL from environment or secrets
    epic_base_url = os.environ.get("EPIC_BASE_URL")
    if not epic_base_url:
        try:
            epic_base_url = get_secret("EPIC_BASE_URL")
        except ValueError:
            raise ValueError("EPIC_BASE_URL not found in environment or secrets")
    
    # Prepare JWT claims
    now = int(time.time())
    expiration = now + 300  # 5 minutes
    
    claims = {
        "iss": client_id,  # Issuer is the client ID
        "sub": client_id,  # Subject is also the client ID
        "aud": f"{epic_base_url}/oauth2/token",
        "jti": str(int(time.time() * 1000)),  # Unique ID based on timestamp
        "iat": now,
        "exp": expiration,
    }
    
    # Sign JWT
    logger.info("Building JWT for token exchange", 
                client_id=client_id,
                epic_base_url=epic_base_url)
    
    try:
        return jwt.encode(claims, private_key, algorithm="RS384")
    except Exception as e:
        logger.error("Failed to encode JWT", error=str(e))
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def exchange_for_access_token(jwt_token: str) -> Dict:
    """Exchange a JWT token for an access token.
    
    Args:
        jwt_token: JWT token string.
        
    Returns:
        Dictionary containing the access token response.
        
    Raises:
        requests.RequestException: If the token exchange fails.
    """
    # Get Epic base URL from environment or secrets
    epic_base_url = os.environ.get("EPIC_BASE_URL")
    if not epic_base_url:
        try:
            epic_base_url = get_secret("EPIC_BASE_URL")
        except ValueError:
            raise ValueError("EPIC_BASE_URL not found in environment or secrets")
    
    token_url = f"{epic_base_url}/oauth2/token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": jwt_token,
    }
    
    logger.info("Exchanging JWT for access token", url=token_url)
    
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


def get_or_refresh_token(cache_key: str = "default") -> str:
    """Get a valid access token, refreshing if necessary.
    
    Args:
        cache_key: Optional key for token caching.
        
    Returns:
        Valid access token string.
    """
    global _token_cache
    
    # Check if we have a cached token
    if cache_key in _token_cache:
        token_data = _token_cache[cache_key]
        
        # Check if token needs refresh
        if not token_needs_refresh(token_data):
            logger.debug("Using cached token", cache_key=cache_key)
            return token_data["access_token"]
    
    # Build JWT and exchange for access token
    logger.info("Refreshing token", cache_key=cache_key)
    jwt_token = build_jwt()
    token_data = exchange_for_access_token(jwt_token)
    
    # Cache the new token
    _token_cache[cache_key] = token_data
    
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
    # This function is redundant now since we use tenacity for retries
    # But keeping it for backward compatibility
    return get_or_refresh_token() 