"""
JWT authentication client for FHIR API.
"""

import time
import uuid
import logging
import datetime
import jwt  # PyJWT package
import requests
import json

logger = logging.getLogger(__name__)

# JWKS Configuration
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"

class JWTClient:
    """
    Client for JWT-based authentication.
    
    Handles token generation, caching, and expiration based on JWT standards.
    """
    
    def __init__(self, client_id, private_key, token_url=None):
        """
        Initialize the JWT client.
        
        Args:
            client_id: Client ID for authentication
            private_key: Private key for JWT signing
            token_url: URL for token endpoint (if using OAuth flow)
        """
        self.client_id = client_id
        self.private_key = private_key
        self.token_url = token_url or "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
        self.token = None
        self.token_expiration = 0
    
    def get_token(self):
        """
        Get a valid JWT token, either from cache or by generating a new one.
        
        Returns:
            Valid JWT token as string
        """
        # Return cached token if still valid
        if self.token and time.time() < self.token_expiration - 60:  # Refresh 60s before expiry
            return self.token
        
        try:
            # Generate JWT for EPIC FHIR API
            now = datetime.datetime.utcnow()
            now_ts = int(now.timestamp())
            expiration = now + datetime.timedelta(minutes=5)  # Short expiration for JWT
            exp_ts = int(expiration.timestamp())
            
            # Set the JWT headers - CRITICAL for EPIC
            headers = {
                "alg": "RS384",  # EPIC requires RS384
                "kid": "atlas-key-001",  # Key ID
                "jku": JWKS_URL,  # JWKS URL
                "typ": "JWT"
            }
            
            # Create JWT payload
            payload = {
                "iss": self.client_id,  # Issuer claim
                "sub": self.client_id,  # Subject claim
                "aud": self.token_url,  # Audience claim
                "jti": str(uuid.uuid4())[:32],  # Unique ID for this JWT
                "iat": now_ts,  # Issued at time
                "nbf": now_ts,  # Not before time
                "exp": exp_ts  # Expiration time
            }
            
            # Log JWT payload and headers for debugging
            logger.debug(f"Creating JWT with headers: {headers}")
            logger.debug(f"Creating JWT with payload: {payload}")
            
            # Sign the JWT with the private key using RS384
            encoded_jwt = jwt.encode(
                payload=payload,
                key=self.private_key,  # Private key
                algorithm="RS384",  # EPIC uses RS384 for signing
                headers=headers
            )
            
            # EPIC requires a client_assertion token flow
            logger.debug(f"Requesting token from {self.token_url}")
            token_response = requests.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                    'client_assertion': encoded_jwt,
                    'scope': 'system/*.read'  # Standard read scope
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
            )
            
            # Check for error
            if token_response.status_code != 200:
                logger.error(f"Token request failed with status {token_response.status_code}")
                logger.debug(f"Token error response: {token_response.text}")
                
                # Detailed error info for debugging
                if "invalid_client" in token_response.text:
                    logger.error("Invalid client error - check client_id, key, and JWKS setup")
                    logger.error("Note: JWKS can take up to 60 min (sandbox) or 12 hours (prod) to propagate")
                
                raise Exception(f"Failed to get token: {token_response.text}")
            
            # Extract token from response
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            
            # Set token and expiration
            self.token = access_token
            self.token_expiration = time.time() + expires_in
            
            logger.info(f"Obtained new token, expires in {expires_in} seconds")
            return self.token
                
        except Exception as e:
            logger.error(f"Error creating JWT token: {str(e)}")
            
            # For error recovery, try to return a stored token from file if available
            try:
                with open("../auth/epic_token.json", "r") as f:
                    token_data = json.loads(f.read())
                    if token_data.get("access_token"):
                        logger.warning("Using fallback token from file")
                        return token_data.get("access_token")
            except:
                pass
                
            # Return error token as last resort
            return "error_creating_token" 