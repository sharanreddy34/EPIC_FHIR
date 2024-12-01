#!/usr/bin/env python3
"""
Enhanced module for obtaining access tokens from Epic FHIR API.
Uses configuration from environment variables or config files.
"""

import os
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import jwt
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("epic_auth")

# Load environment variables if .env file exists
env_path = Path('.env')
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configuration from environment variables or defaults
CLIENT_ID = os.getenv('EPIC_CLIENT_ID', '02317de4-f128-4607-989b-07892f678580')
JWKS_URL = os.getenv('EPIC_JWKS_URL', 'https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json')
EPIC_TOKEN_URL = os.getenv('EPIC_TOKEN_URL', 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token')
FHIR_BASE_URL = os.getenv('EPIC_FHIR_BASE_URL', 'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4')
PRIVATE_KEY_PATH = os.getenv('PRIVATE_KEY_PATH', 'epic-fhir-integration/secrets/rsa_private.pem')
TOKEN_CACHE_PATH = os.getenv('TOKEN_CACHE_PATH', 'epic-fhir-integration/secrets/epic_token.json')


def load_config_file(config_path: str = 'config/live_epic_auth.json') -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration values
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return {}


def get_private_key(private_key_path: Optional[str] = None) -> str:
    """
    Read the private key from file.
    
    Args:
        private_key_path: Path to the private key file
        
    Returns:
        Private key as string
        
    Raises:
        FileNotFoundError: If the private key file doesn't exist
    """
    # Use provided path, environment var, or default
    key_path = private_key_path or PRIVATE_KEY_PATH
    
    try:
        with open(key_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Private key not found at {key_path}")
        raise


def generate_jwt(private_key: str, 
                 client_id: Optional[str] = None, 
                 token_url: Optional[str] = None,
                 jwks_url: Optional[str] = None) -> str:
    """
    Generate a JWT token for Epic's OAuth 2.0 backend service authentication.
    
    Args:
        private_key: The RSA private key as string
        client_id: The client ID to use as issuer and subject
        token_url: The token URL to use as audience
        jwks_url: URL to the JWKS file
        
    Returns:
        The encoded JWT token
    """
    # Use provided values or defaults
    client_id = client_id or CLIENT_ID
    token_url = token_url or EPIC_TOKEN_URL
    jwks_url = jwks_url or JWKS_URL
    
    # Set the JWT headers
    headers = {
        "alg": "RS384",
        "kid": "atlas-key-001",
        "jku": jwks_url,
        "typ": "JWT"
    }

    # Get current time
    now = int(time.time())
    
    # Generate a unique JTI (max 151 chars)
    jti = str(uuid.uuid4())[:32]

    # Set the JWT claims exactly as Epic requires
    claims = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_url,
        "jti": jti,
        "iat": now,
        "nbf": now,
        "exp": now + 300  # 5 minutes (Epic's maximum)
    }
    
    logger.debug("Generating JWT with headers: %s", headers)
    logger.debug("JWT claims: %s", claims)

    # Generate the JWT
    token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )
    
    return token


def is_token_valid(token_data: Dict[str, Any]) -> bool:
    """
    Check if a token is still valid.
    
    Args:
        token_data: Dictionary containing token information
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token_data or "access_token" not in token_data:
        return False
    
    # Check if token has expiration info
    if "expires_at" in token_data:
        expires_at = token_data["expires_at"]
        now = datetime.now().timestamp()
        
        # Add buffer of 60 seconds to avoid using tokens that will expire very soon
        return now < (expires_at - 60)
    
    # If no expiration info or other error, consider it invalid
    return False


def get_cached_token() -> Optional[Dict[str, Any]]:
    """
    Get a cached token if available and valid.
    
    Returns:
        Token data dictionary or None if no valid token found
    """
    try:
        with open(TOKEN_CACHE_PATH, 'r') as f:
            token_data = json.load(f)
            
        if is_token_valid(token_data):
            logger.info("Using cached token (expires at %s)", 
                       datetime.fromtimestamp(token_data.get("expires_at", 0)))
            return token_data
        else:
            logger.info("Cached token has expired or is invalid")
            return None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.info("No valid cached token found: %s", e)
        return None


def save_token_to_cache(token_data: Dict[str, Any]) -> None:
    """
    Save token data to cache file.
    
    Args:
        token_data: Dictionary containing token information
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_CACHE_PATH), exist_ok=True)
    
    try:
        with open(TOKEN_CACHE_PATH, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info("Token saved to cache: %s", TOKEN_CACHE_PATH)
    except Exception as e:
        logger.warning("Failed to save token to cache: %s", e)


def get_access_token(force_refresh: bool = False, 
                     config_path: Optional[str] = None,
                     private_key_path: Optional[str] = None,
                     verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get an access token from Epic using JWT authentication.
    Checks for a cached token first unless force_refresh is True.
    
    Args:
        force_refresh: Force getting a new token even if cached one is valid
        config_path: Path to configuration file
        private_key_path: Path to the private key file
        verbose: Whether to print detailed information
        
    Returns:
        Dictionary containing token information or None if failed
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check for cached token unless force refresh is requested
    if not force_refresh:
        cached_token = get_cached_token()
        if cached_token:
            return cached_token
    
    # Load configuration if a path is provided
    config = {}
    if config_path:
        config = load_config_file(config_path)
    
    # Get client ID from config or default
    client_id = config.get('client_id', CLIENT_ID)
    token_url = config.get('token_url', EPIC_TOKEN_URL)
    jwks_url = config.get('jwks_url', JWKS_URL)
    
    # Get private key path from config, param, or default
    key_path = private_key_path or config.get('private_key_path', PRIVATE_KEY_PATH)
    
    try:
        # Get private key
        private_key = get_private_key(key_path)
        
        # Generate JWT
        jwt_token = generate_jwt(
            private_key=private_key,
            client_id=client_id,
            token_url=token_url,
            jwks_url=jwks_url
        )
        
        if verbose:
            logger.debug("Generated JWT Token: %s...", jwt_token[:30])
        
        # Set up request data
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': jwt_token,
            'scope': config.get('scope', 'system/*.read')
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # Make request to token endpoint
        logger.info("Requesting access token from Epic...")
        response = requests.post(token_url, data=data, headers=headers)
        
        # Check response
        if response.ok:
            token_data = response.json()
            logger.info("Successfully obtained access token")
            
            # Add expiration timestamp
            if "expires_in" in token_data:
                expires_at = datetime.now() + timedelta(seconds=int(token_data["expires_in"]))
                token_data["expires_at"] = expires_at.timestamp()
            
            # Save token to cache
            save_token_to_cache(token_data)
            
            return token_data
        else:
            logger.error("Failed to get access token. Status: %s, Response: %s", 
                       response.status_code, response.text)
            
            if "invalid_client" in response.text:
                logger.warning(
                    "NOTE: If you're getting invalid_client error:\n"
                    "1. Verify all JWT claims are correct\n"
                    "2. Wait for key propagation:\n"
                    "   - Sandbox: up to 60 minutes\n"
                    "   - Production: up to 12 hours"
                )
            
            return None
            
    except Exception as e:
        logger.error("Error getting access token: %s", e, exc_info=True)
        return None


def get_auth_headers() -> Dict[str, str]:
    """
    Get authorization headers for FHIR API requests.
    
    Returns:
        Dictionary with Authorization header
    """
    token_data = get_access_token()
    if not token_data or "access_token" not in token_data:
        raise ValueError("Failed to get valid access token")
    
    return {
        "Authorization": f"{token_data.get('token_type', 'Bearer')} {token_data['access_token']}"
    }


def get_token_with_retry(max_retries: int = 3) -> Optional[str]:
    """
    Get an access token with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        Access token string or None if all attempts fail
    """
    for attempt in range(max_retries):
        try:
            token_data = get_access_token(force_refresh=(attempt > 0))
            if token_data and "access_token" in token_data:
                return token_data["access_token"]
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
        
        # Don't sleep on the last attempt
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    logger.error(f"Failed to get token after {max_retries} attempts")
    return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Get Epic FHIR API access token")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--force-refresh", action="store_true", help="Force token refresh")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--save-to", help="Path to save token JSON (default: use cache path)")
    args = parser.parse_args()
    
    # Get token
    token_data = get_access_token(
        force_refresh=args.force_refresh,
        config_path=args.config,
        verbose=args.verbose
    )
    
    if token_data:
        print("\nAccess token details:")
        print(f"Token Type: {token_data.get('token_type')}")
        print(f"Expires In: {token_data.get('expires_in')} seconds")
        
        # Save token if requested
        if args.save_to:
            with open(args.save_to, "w") as f:
                json.dump(token_data, f, indent=2)
            print(f"\nAccess token saved to {args.save_to}")
        
        print("\nToken can now be used for FHIR API requests")
    else:
        print("\nFailed to get access token")
        exit(1) 