import jwt
import time
import uuid
import requests
import os
from datetime import datetime
import json  # Add json import for pretty printing

# JWT Configuration
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
PROD_CLIENT_ID = "43e4309a-67ab-4c3a-b583-f062c35d3791"
NON_PROD_CLIENT_ID = "02317de4-f128-4607-989b-07892f678580"
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"

# Save the private key to a file
def save_private_key(key_content):
    with open("private_key.pem", "w") as f:
        f.write(key_content)
    print("Private key saved to private_key.pem")

def generate_jwt(private_key_path, use_prod=False):
    """Generate a JWT token for Epic's OAuth 2.0 backend service authentication"""
    # Read the private key
    with open(private_key_path, "r") as f:
        private_key = f.read()
    
    client_id = PROD_CLIENT_ID if use_prod else NON_PROD_CLIENT_ID
    
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

def get_access_token(client_id, private_key):
    """Exchange JWT for an access token from Epic"""
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

    # Debug output
    print("\nGenerating JWT with:")
    print("\nHeaders:")
    print(json.dumps(headers, indent=2))
    print("\nClaims:")
    print(json.dumps(claims, indent=2))
    
    # Generate the JWT
    jwt_token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )
    
    # Debug: Decode the JWT to verify its contents
    try:
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        print("\nDecoded JWT payload:")
        print(json.dumps(decoded, indent=2))
    except Exception as e:
        print(f"\nError decoding JWT: {e}")
    
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
        print("\nRequesting access token from Epic...")
        print(f"Token URL: {EPIC_TOKEN_URL}")
        print("\nRequest Data:")
        print(json.dumps({k: v if k != 'client_assertion' else f"{v[:50]}..." for k, v in data.items()}, indent=2))
        
        response = requests.post(
            EPIC_TOKEN_URL,
            data=data,
            headers=headers
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.ok:
            token_data = response.json()
            print("\nSuccessfully obtained access token!")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')} seconds")
            return token_data
        else:
            print("\nFailed to obtain access token.")
            if "invalid_client" in response.text:
                print("\nNOTE: If you're getting invalid_client error:")
                print("1. Verify all JWT claims are correct")
                print("2. Wait for key propagation:")
                print("   - Sandbox: up to 60 minutes")
                print("   - Production: up to 12 hours")
                print("3. Verify the private key is correctly formatted")
                print("4. Check that the JWKS endpoint is accessible")
            return None
            
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

if __name__ == "__main__":
    # Read the private key from file
    try:
        # Try both possible key file locations
        key_files = ["rsa_private.pem", "key.md", "private_key.pem"]
        private_key = None
        used_file = None
        
        for key_file in key_files:
            try:
                with open(key_file, "r") as f:
                    private_key = f.read().strip()
                    used_file = key_file
                    break
            except FileNotFoundError:
                continue
        
        if not private_key:
            raise FileNotFoundError("No private key file found. Tried: " + ", ".join(key_files))
            
        print(f"\nUsing private key from: {used_file}")
        
        # Try non-production first
        print("\nTrying Non-Production Environment")
        print("=" * 50)
        print(f"Client ID: {NON_PROD_CLIENT_ID}")
        token_info = get_access_token(NON_PROD_CLIENT_ID, private_key)
        
        if token_info:
            with open("epic_token.json", "w") as f:
                json.dump(token_info, f, indent=2)
            print("\nAccess token saved to epic_token.json")
    except Exception as e:
        print(f"Error: {e}") 