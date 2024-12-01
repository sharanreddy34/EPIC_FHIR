"""
JWT-based authentication for Epic FHIR API.

This module handles generation of JWT tokens and exchanging them for Epic FHIR API access tokens.
"""

import os
import time
import uuid
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import jwt
except ImportError:
    print("PyJWT package not found. Please install with: pip install PyJWT cryptography")
    import sys
    sys.exit(1)

logger = logging.getLogger("fhir_pipeline.auth.jwt")

# Default configuration
DEFAULT_JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
DEFAULT_KID = "atlas-key-001"
DEFAULT_TOKEN_URL_PROD = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
DEFAULT_TOKEN_URL_NON_PROD = "https://fhir-myapps.epic.com/interconnect-fhir-oauth/oauth2/token"
DEFAULT_SCOPE = "system/*.read"
DEFAULT_JWT_EXPIRATION_SECONDS = 300


class JWTAuthenticator:
    """JWT-based authenticator for Epic FHIR API."""
    
    def __init__(
        self,
        private_key_path: Optional[str] = None,
        private_key_content: Optional[str] = None,
        client_id: Optional[str] = None,
        jwks_url: str = DEFAULT_JWKS_URL,
        kid: str = DEFAULT_KID,
        token_url: Optional[str] = None,
        environment: str = "non-production",
        scope: str = DEFAULT_SCOPE,
        debug_mode: bool = False,
    ):
        """
        Initialize JWT authenticator.
        
        Args:
            private_key_path: Path to private key file
            private_key_content: Private key content as string (alternative to path)
            client_id: Epic client ID
            jwks_url: URL to JWKS (JSON Web Key Set)
            kid: Key ID in JWKS
            token_url: Token endpoint URL (default based on environment)
            environment: 'production' or 'non-production'
            scope: OAuth scope
            debug_mode: Whether to enable debug output
        """
        self.debug_mode = debug_mode
        
        # Get client ID from environment if not provided
        self.client_id = client_id or os.environ.get("EPIC_CLIENT_ID")
        if not self.client_id:
            raise ValueError("Client ID is required. Provide it directly or set EPIC_CLIENT_ID environment variable.")
        
        # Set token URL based on environment
        if token_url:
            self.token_url = token_url
        else:
            self.token_url = (
                DEFAULT_TOKEN_URL_PROD if environment == "production" 
                else DEFAULT_TOKEN_URL_NON_PROD
            )
        
        # Load private key
        if private_key_content:
            self.private_key = private_key_content
        elif private_key_path:
            try:
                with open(private_key_path, 'r') as f:
                    self.private_key = f.read()
            except (FileNotFoundError, IOError) as e:
                raise ValueError(f"Failed to load private key from {private_key_path}: {str(e)}")
        else:
            # Try to find key in standard locations
            key_files = ["rsa_private.pem", "private_key.pem", "../auth/rsa_private.pem", "../auth/private_key.pem"]
            for key_file in key_files:
                try:
                    with open(key_file, 'r') as f:
                        self.private_key = f.read()
                        logger.debug(f"Loaded private key from {key_file}")
                        break
                except (FileNotFoundError, IOError):
                    continue
            else:
                raise ValueError(
                    "Private key is required. Provide it directly, specify a file path, "
                    "or place a key file in one of the standard locations."
                )
        
        self.jwks_url = jwks_url
        self.kid = kid
        self.scope = scope
        
        logger.info(f"JWT Authenticator initialized for client ID: {self.client_id}")
        logger.info(f"Using token endpoint: {self.token_url}")
        
    def generate_jwt(self) -> str:
        """
        Generate a JWT token for Epic FHIR API authentication.
        
        Returns:
            str: JWT token
        """
        # Set the JWT headers
        headers = {
            "alg": "RS384",
            "kid": self.kid,
            "jku": self.jwks_url,
            "typ": "JWT"
        }
        
        # Get current time
        now = int(time.time())
        
        # Generate a unique JTI (max 32 chars)
        jti = str(uuid.uuid4())[:32]
        
        # Set the JWT claims exactly as Epic requires
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_url,
            "jti": jti,
            "iat": now,
            "nbf": now,
            "exp": now + DEFAULT_JWT_EXPIRATION_SECONDS
        }
        
        if self.debug_mode:
            logger.debug(f"Generating JWT with headers: {headers}")
            logger.debug(f"JWT claims: {claims}")
        
        # Generate the JWT
        try:
            token = jwt.encode(
                payload=claims,
                key=self.private_key,
                algorithm="RS384",
                headers=headers
            )
            
            if self.debug_mode:
                # Decode without verification for debugging
                decoded = jwt.decode(token, options={"verify_signature": False})
                logger.debug(f"Generated JWT token (decoded): {json.dumps(decoded, indent=2)}")
            
            return token
        except Exception as e:
            logger.error(f"Failed to generate JWT: {str(e)}")
            raise
    
    def get_access_token(self) -> Dict[str, Any]:
        """
        Get an access token from Epic using JWT authentication.
        
        Returns:
            Dict[str, Any]: Access token response with token and expiration
        """
        # Generate JWT
        jwt_token = self.generate_jwt()
        
        # Exchange JWT for access token
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': jwt_token,
            'scope': self.scope
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        if self.debug_mode:
            logger.debug(f"Requesting access token from {self.token_url}")
            logger.debug(f"Request data: {json.dumps({k: v if k != 'client_assertion' else f'{v[:50]}...' for k, v in data.items()})}")
        
        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers
            )
            
            if self.debug_mode:
                logger.debug(f"Response Status: {response.status_code}")
                logger.debug(f"Response Headers: {dict(response.headers)}")
                
                # Don't log the full response body if it might contain a token
                if response.status_code != 200:
                    logger.debug(f"Response Body: {response.text}")
            
            response.raise_for_status()
            
            token_data = response.json()
            if self.debug_mode:
                expiry = token_data.get('expires_in', 'unknown')
                token_type = token_data.get('token_type', 'unknown')
                logger.debug(f"Received {token_type} token, expires in {expiry} seconds")
            
            # Add expiration timestamp
            if 'expires_in' in token_data:
                token_data['expires_at'] = int(time.time()) + token_data['expires_in']
            
            return token_data
        except requests.RequestException as e:
            logger.error(f"Error getting access token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
                
                if "invalid_client" in e.response.text:
                    logger.error("\nNOTE: If you're getting invalid_client error:")
                    logger.error("1. Verify all JWT claims are correct")
                    logger.error("2. Wait for key propagation:")
                    logger.error("   - Sandbox: up to 60 minutes")
                    logger.error("   - Production: up to 12 hours")
                    logger.error("3. Verify the private key is correctly formatted")
                    logger.error("4. Check that the JWKS endpoint is accessible")
            raise


def create_token_provider(
    private_key_path: Optional[str] = None,
    client_id: Optional[str] = None,
    environment: str = "non-production",
    debug_mode: bool = False,
    cache_token: bool = True
):
    """
    Create a token provider function for the FHIR client.
    
    Args:
        private_key_path: Path to private key file
        client_id: Epic client ID
        environment: 'production' or 'non-production'
        debug_mode: Whether to enable debug output
        cache_token: Whether to cache the token
        
    Returns:
        Callable: Token provider function that returns an access token
    """
    # Create authenticator
    authenticator = JWTAuthenticator(
        private_key_path=private_key_path,
        client_id=client_id,
        environment=environment,
        debug_mode=debug_mode
    )
    
    # Cache for token
    token_cache = {
        'token_data': None,
        'expires_at': 0
    }
    
    # Token provider function
    def token_provider():
        current_time = int(time.time())
        
        # Check if we have a cached token that's still valid (with 30s buffer)
        if (
            cache_token and 
            token_cache['token_data'] is not None and
            token_cache['expires_at'] > current_time + 30
        ):
            logger.debug("Using cached access token")
            return token_cache['token_data']['access_token']
        
        # Get new token
        logger.debug("Getting fresh access token")
        token_data = authenticator.get_access_token()
        
        # Cache the token
        if cache_token:
            token_cache['token_data'] = token_data
            token_cache['expires_at'] = token_data.get('expires_at', 0)
        
        return token_data['access_token']
    
    return token_provider 