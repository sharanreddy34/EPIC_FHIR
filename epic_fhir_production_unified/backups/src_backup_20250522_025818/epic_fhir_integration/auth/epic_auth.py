"""
Epic FHIR API Authentication Wrapper

A reliable authentication module that uses configuration from multiple sources
to handle JWT token generation and exchange for Epic FHIR API.
"""

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any

import jwt
import requests
import logging

from epic_fhir_integration.config.loader import get_config

# Set up logging
logger = logging.getLogger(__name__)

# Default values
DEFAULT_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
DEFAULT_CACHE_PATH = Path.home() / "ATLAS Palantir" / "epic_token.json"

def _load_private_key() -> str:
    """
    Load the private key from the configured path.
    
    Returns:
        The private key as a string
    """
    # Get configured path
    auth_config = get_config("auth") or {}
    key_path = auth_config.get("private_key_path")
    
    # If no path configured, try standard locations
    if not key_path:
        key_files = [
            Path.home() / "ATLAS Palantir" / "epic_private_key.pem",
            Path.home() / "ATLAS Palantir" / "key.md",
            Path(__file__).parent.parent.parent / "secrets" / "epic_private_key.pem",
            Path(__file__).parent.parent.parent / "secrets" / "rsa_private.pem",
        ]
        
        for file_path in key_files:
            if file_path.exists():
                key_path = str(file_path)
                break
    
    # If still no key path found, raise error
    if not key_path or not Path(key_path).exists():
        raise FileNotFoundError(f"Private key not found. Searched: {key_path} and standard locations")
    
    # Read key file
    with open(key_path, "r") as key_file:
        return key_file.read().strip()

def _get_token_cache_path() -> Path:
    """
    Get the path to the token cache file.
    
    Returns:
        Path object for the token cache
    """
    auth_config = get_config("auth") or {}
    cache_path = auth_config.get("token_cache_path")
    
    if cache_path:
        return Path(cache_path)
    
    return DEFAULT_CACHE_PATH

def _generate_jwt() -> str:
    """
    Generate a JWT token for Epic OAuth authentication.
    
    Returns:
        JWT token string
    """
    # Load config
    auth_config = get_config("auth") or {}
    client_id = auth_config.get("client_id")
    jwt_issuer = auth_config.get("jwt_issuer") or client_id
    epic_base_url = auth_config.get("epic_base_url")
    
    # Fall back to defaults if not configured
    if not client_id:
        client_id = "02317de4-f128-4607-989b-07892f678580"  # Default client ID
        logger.warning(f"No client_id configured. Using default: {client_id}")
    
    if not jwt_issuer:
        jwt_issuer = client_id
    
    if not epic_base_url:
        epic_base_url = "https://fhir.epic.com/interconnect-fhir-oauth"
        logger.warning(f"No epic_base_url configured. Using default: {epic_base_url}")
    
    # Construct token URL
    token_url = f"{epic_base_url}/oauth2/token"
    
    # Load private key
    private_key = _load_private_key()
    
    # Create JWT headers
    headers = {
        "alg": "RS384",
        "kid": "atlas-key-001",
        "jku": JWKS_URL,
        "typ": "JWT"
    }
    
    # Create JWT claims
    now = int(time.time())
    jti = str(uuid.uuid4())[:32]
    
    claims = {
        "iss": jwt_issuer,
        "sub": client_id,
        "aud": token_url,
        "jti": jti,
        "iat": now,
        "nbf": now,
        "exp": now + 300  # 5 minutes (Epic's maximum)
    }
    
    # Generate and sign JWT
    token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )
    
    return token

def _token_is_valid(token_data: Dict[str, Any]) -> bool:
    """
    Check if a token is valid and not close to expiration.
    
    Args:
        token_data: Token data dictionary
        
    Returns:
        True if token is valid, False otherwise
    """
    # Minimum required fields
    if not token_data or 'access_token' not in token_data or 'expires_in' not in token_data:
        return False
    
    # Check if we have a timestamp
    if 'timestamp' in token_data:
        timestamp = token_data['timestamp']
        expires_in = token_data['expires_in']
        
        # Add a 5-minute buffer
        buffer = 300
        now = datetime.now().timestamp()
        
        # Token is valid if we're more than 5 minutes from expiration
        return now < (timestamp + expires_in - buffer)
    
    return False

def _load_cached_token() -> Optional[Dict[str, Any]]:
    """
    Load token from cache if available and valid.
    
    Returns:
        Token data dictionary or None if no valid token is cached
    """
    cache_path = _get_token_cache_path()
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r") as f:
            token_data = json.load(f)
        
        if _token_is_valid(token_data):
            return token_data
            
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        # If any error occurs, return None to force token refresh
        pass
    
    return None

def _save_token_to_cache(token_data: Dict[str, Any]) -> None:
    """
    Save token data to cache file.
    
    Args:
        token_data: Token data dictionary
    """
    # Add timestamp for validity checking
    token_data['timestamp'] = datetime.now().timestamp()
    
    # Create directory if it doesn't exist
    cache_path = _get_token_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write token data
    with open(cache_path, "w") as f:
        json.dump(token_data, f, indent=2)
    
    logger.debug(f"Token cached to {cache_path}")

def exchange_jwt_for_token(jwt_token: str, scope: str = "system/*.read") -> Dict[str, Any]:
    """
    Exchange a JWT token for an Epic access token.
    
    Args:
        jwt_token: JWT token string
        scope: OAuth scope to request
        
    Returns:
        Token data dictionary
    """
    # Load config
    auth_config = get_config("auth") or {}
    epic_base_url = auth_config.get("epic_base_url")
    
    # Construct token URL
    if not epic_base_url:
        epic_base_url = "https://fhir.epic.com/interconnect-fhir-oauth"
    
    token_url = f"{epic_base_url}/oauth2/token"
    
    # Set up request data
    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': jwt_token,
        'scope': scope
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    # Make request
    response = requests.post(
        token_url,
        data=data,
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

def get_token(scope: str = "system/*.read", force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get an Epic access token, using cache or requesting a new one.
    
    Args:
        scope: OAuth scope to request
        force_refresh: Force refreshing the token even if cached token is valid
        
    Returns:
        Token data dictionary
    """
    # Try to use cached token unless force_refresh is True
    if not force_refresh:
        cached_token = _load_cached_token()
        if cached_token:
            logger.debug("Using cached token")
            return cached_token
    
    # Generate JWT
    try:
        jwt_token = _generate_jwt()
        
        # Exchange for access token
        token_data = exchange_jwt_for_token(jwt_token, scope)
        
        # Save to cache
        _save_token_to_cache(token_data)
        
        return token_data
        
    except Exception as e:
        logger.error(f"Error obtaining token: {str(e)}")
        raise

def get_auth_headers() -> Dict[str, str]:
    """
    Get authorization headers for API requests.
    
    Returns:
        Header dictionary with Authorization header
    """
    token_data = get_token()
    token = token_data['access_token']
    
    return {
        'Authorization': f"Bearer {token}",
        'Accept': 'application/json'
    }

def get_token_with_retry(max_retries: int = 3, backoff_factor: float = 1.5, scope: str = "system/*.read") -> Dict[str, Any]:
    """
    Get a token with retry and exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff multiplier between retries
        scope: OAuth scope to request
        
    Returns:
        Token data dictionary
    """
    last_error = None
    delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return get_token(scope=scope, force_refresh=(attempt > 0))
        except Exception as e:
            last_error = e
            logger.warning(f"Token attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                delay *= backoff_factor
    
    raise RuntimeError(f"Failed to obtain token after {max_retries} attempts: {last_error}") 