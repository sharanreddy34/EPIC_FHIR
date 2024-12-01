#!/usr/bin/env python3
import jwt
import requests
import time
import uuid

# Configuration
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
CLIENT_ID = "02317de4-f128-4607-989b-07892f678580"  # Non-production client ID
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"

def get_access_token():
    # Read the private key
    with open('rsa_private.pem', 'r') as f:
        private_key = f.read()

    # Get current time
    now = int(time.time())
    
    # Generate JWT
    headers = {
        "alg": "RS384",
        "kid": "atlas-key-001",
        "jku": JWKS_URL,
        "typ": "JWT"
    }
    
    claims = {
        "iss": CLIENT_ID,
        "sub": CLIENT_ID,
        "aud": EPIC_TOKEN_URL,
        "jti": str(uuid.uuid4())[:32],
        "iat": now,
        "nbf": now,
        "exp": now + 300
    }
    
    print("\nGenerating JWT with:")
    print(f"Headers: {headers}")
    print(f"Claims: {claims}")
    
    jwt_token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )
    
    print(f"\nGenerated JWT token: {jwt_token}")
    
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
    
    print("\nRequesting access token from Epic...")
    print(f"Request data: {data}")
    response = requests.post(EPIC_TOKEN_URL, data=data, headers=headers)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.ok:
        token_data = response.json()
        print("\nSuccess! Access token details:")
        print(f"Token Type: {token_data.get('token_type')}")
        print(f"Expires In: {token_data.get('expires_in')} seconds")
        return token_data
    else:
        print("\nFailed to get access token")
        if "invalid_client" in response.text:
            print("\nNOTE: If you're getting invalid_client error:")
            print("1. Verify all JWT claims are correct")
            print("2. Wait for key propagation:")
            print("   - Sandbox: up to 60 minutes")
            print("   - Production: up to 12 hours")
        return None

if __name__ == "__main__":
    token_info = get_access_token()
    if token_info:
        with open("epic_token.json", "w") as f:
            import json
            json.dump(token_info, f, indent=2)
        print("\nAccess token saved to epic_token.json") 