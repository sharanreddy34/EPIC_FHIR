import jwt
import time
import uuid
import requests
import os
from datetime import datetime
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT Configuration
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
PROD_CLIENT_ID = "43e4309a-67ab-4c3a-b583-f062c35d3791"
NON_PROD_CLIENT_ID = "02317de4-f128-4607-989b-07892f678580"
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"

def generate_jwt(private_key, client_id):
    """Generate a JWT token for Epic's OAuth 2.0 backend service authentication"""
    
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
        "aud": EPIC_TOKEN_URL,
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

def get_access_token(debug=False):
    """Exchange JWT for an access token from Epic"""
    if debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Loading private key for EPIC authentication")
    
    # Try both possible key file locations
    key_files = [
        "rsa_private.pem", 
        "key.md", 
        "private_key.pem",
        "../docs/key.md",  # From previous error logs
        Path.home() / "ATLAS Palantir/docs/key.md"
    ]
    
    private_key = None
    used_file = None
    
    for key_file in key_files:
        try:
            key_path = Path(key_file)
            if key_path.exists():
                logger.debug(f"Found key file: {key_path}")
                with open(key_path, "r") as f:
                    private_key = f.read().strip()
                    used_file = key_file
                    break
        except Exception as e:
            logger.debug(f"Could not read key from {key_file}: {str(e)}")
            continue
    
    if not private_key:
        logger.error(f"No private key file found. Tried: {', '.join([str(kf) for kf in key_files])}")
        return None
        
    logger.info(f"Using private key from: {used_file}")
    
    # Try non-production first
    logger.info("Generating authentication token for EPIC FHIR API")
    client_id = NON_PROD_CLIENT_ID
    
    # Generate the JWT
    try:
        jwt_token = generate_jwt(private_key, client_id)
        logger.debug("JWT token generated successfully")
    except Exception as e:
        logger.error(f"Error generating JWT: {str(e)}")
        return None
    
    # Exchange JWT for access token
    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': jwt_token,
        'scope': 'system/*.read'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    try:
        logger.info(f"Requesting access token from Epic: {EPIC_TOKEN_URL}")
        
        response = requests.post(
            EPIC_TOKEN_URL,
            data=data,
            headers=headers
        )
        
        logger.debug(f"Response Status Code: {response.status_code}")
        
        if response.ok:
            token_data = response.json()
            logger.info(f"Successfully obtained access token! Expires in: {token_data.get('expires_in')} seconds")
            
            # Save token to file
            with open("epic_token.json", "w") as f:
                json.dump(token_data, f, indent=2)
            logger.info("Access token saved to epic_token.json")
            
            return token_data
        else:
            logger.error(f"Failed to obtain access token: {response.status_code} - {response.text}")
            if "invalid_client" in response.text:
                logger.warning("If you're getting invalid_client error:")
                logger.warning("1. Verify all JWT claims are correct")
                logger.warning("2. Wait for key propagation: Sandbox (60 min) or Production (12 hours)")
                logger.warning("3. Verify the private key is correctly formatted")
                logger.warning("4. Check that the JWKS endpoint is accessible")
            return None
            
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None

def refresh_token():
    """Refresh the EPIC access token and save to file"""
    return get_access_token()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EPIC FHIR API Authentication Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Get and save token
    token_info = get_access_token(debug=args.debug)
    
    if token_info:
        print("Token successfully obtained and saved to epic_token.json")
    else:
        print("Failed to obtain token. Check logs for details.")
        exit(1) 