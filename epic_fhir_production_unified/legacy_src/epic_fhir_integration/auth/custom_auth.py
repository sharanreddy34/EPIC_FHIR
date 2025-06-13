"""
Custom Epic FHIR authentication module for direct token acquisition.
"""

import os
import json
import time
import uuid
import requests
from pathlib import Path
import jwt

# Authentication constants
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
DEFAULT_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
NON_PROD_CLIENT_ID = "02317de4-f128-4607-989b-07892f678580"
TOKEN_CACHE_FILE = "epic_token.json"

def generate_jwt(private_key, client_id=None, token_url=None):
    """
    Generate a JWT token for Epic's OAuth 2.0 backend service authentication.
    
    Args:
        private_key: The RSA private key as string
        client_id: The client ID to use as issuer and subject (default uses NON_PROD_CLIENT_ID)
        token_url: The token URL to use as audience (default uses DEFAULT_TOKEN_URL)
        
    Returns:
        str: The encoded JWT token
    """
    if client_id is None:
        client_id = NON_PROD_CLIENT_ID
        
    if token_url is None:
        token_url = DEFAULT_TOKEN_URL
    
    # Set the JWT headers
    headers = {
        "alg": "RS384",
        "kid": "atlas-key-001",
        "jku": JWKS_URL,
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

    # Generate the JWT
    token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )
    
    return token

def get_access_token(private_key_path=None, client_id=None, token_url=None, scope="system/*.read", verbose=False):
    """
    Get an access token from Epic using JWT authentication.
    
    Args:
        private_key_path: Path to the private key file
        client_id: The client ID to use
        token_url: The token URL to use
        scope: The scope to request
        verbose: Whether to print debug information
        
    Returns:
        dict: The token response data or None if failed
    """
    # Determine private key
    if private_key_path is None:
        # Try secrets directory
        package_dir = Path(__file__).resolve().parent.parent.parent
        private_key_path = package_dir / "secrets" / "epic_private_key.pem"
    
    # Read the private key
    try:
        with open(private_key_path, "r") as f:
            private_key = f.read()
    except FileNotFoundError:
        print(f"Error: Private key file not found at {private_key_path}")
        return None
    
    # Generate JWT
    jwt_token = generate_jwt(private_key, client_id, token_url)
    
    if verbose:
        print(f"Generated JWT Token: {jwt_token[:50]}...")
    
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
    
    # Set up token URL
    if token_url is None:
        token_url = DEFAULT_TOKEN_URL
    
    # Make the request
    try:
        if verbose:
            print(f"Requesting token from {token_url}...")
        
        response = requests.post(
            token_url,
            data=data,
            headers=headers
        )
        
        if verbose:
            print(f"Response Status: {response.status_code}")
        
        if response.ok:
            token_data = response.json()
            
            # Cache the token for future use
            cache_path = Path(__file__).resolve().parent / TOKEN_CACHE_FILE
            with open(cache_path, "w") as f:
                json.dump(token_data, f, indent=2)
            
            if verbose:
                print(f"Token valid for {token_data.get('expires_in')} seconds")
                print(f"Token cached to {cache_path}")
            
            return token_data
        else:
            print(f"Error getting token: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception during token request: {e}")
        return None

def get_cached_token():
    """
    Get a cached token if available and not expired.
    
    Returns:
        str: The access token or None if not available
    """
    cache_path = Path(__file__).resolve().parent / TOKEN_CACHE_FILE
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r") as f:
            token_data = json.load(f)
        
        # Check if token is still valid (with 5 minute buffer)
        if 'expires_in' in token_data:
            # Get file modification time
            mod_time = cache_path.stat().st_mtime
            current_time = time.time()
            elapsed = current_time - mod_time
            
            # Check if token is still valid with a 5-minute buffer
            if elapsed < (token_data['expires_in'] - 300):
                return token_data['access_token']
    except:
        pass
    
    return None

def get_token():
    """
    Get a token, using cached token if available or requesting a new one.
    
    Returns:
        str: The access token or None if failed
    """
    # Try cached token first
    token = get_cached_token()
    if token:
        return token
    
    # Otherwise get a new token
    token_data = get_access_token()
    if token_data:
        return token_data.get('access_token')
    
    return None

def main():
    """Command-line interface for token generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Get EPIC FHIR access token")
    parser.add_argument("--key", help="Path to private key file")
    parser.add_argument("--client-id", help="Client ID")
    parser.add_argument("--token-url", help="Token URL")
    parser.add_argument("--scope", default="system/*.read", help="Requested scope")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    
    args = parser.parse_args()
    
    token_data = get_access_token(
        private_key_path=args.key,
        client_id=args.client_id,
        token_url=args.token_url,
        scope=args.scope,
        verbose=args.verbose
    )
    
    if token_data:
        print("\nAccess Token:")
        print(token_data.get('access_token'))
        return 0
    else:
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 