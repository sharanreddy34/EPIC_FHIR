import jwt
import time
import uuid
from datetime import datetime, timedelta

# JWT Configuration
JWKS_URL = "https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json"
PROD_CLIENT_ID = "43e4309a-67ab-4c3a-b583-f062c35d3791"
NON_PROD_CLIENT_ID = "02317de4-f128-4607-989b-07892f678580"
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"

def generate_test_jwt(use_prod=False):
    """
    Generate a JWT following Epic's strict requirements:
    - iss and sub must both equal the client ID
    - aud must exactly match the token URL
    - iat/nbf ≤ now; exp > now but no more than 5 minutes after iat
    - jti must be unique and ≤ 151 characters
    - RS384 algorithm is preferred
    """
    # Read the private key
    with open("private_key.pem", "rb") as f:
        private_key = f.read()
    
    client_id = PROD_CLIENT_ID if use_prod else NON_PROD_CLIENT_ID
    
    # Set the JWT headers
    headers = {
        "alg": "RS384",  # Epic's preferred algorithm
        "kid": "atlas-key-001",
        "jku": JWKS_URL,
        "typ": "JWT"
    }

    # Get current time
    now = int(time.time())
    
    # Generate a unique JTI (max 151 chars)
    jti = str(uuid.uuid4())[:32]  # Using first 32 chars of a UUID

    # Set the JWT claims exactly as Epic requires
    claims = {
        "iss": client_id,  # Must be client ID
        "sub": client_id,  # Must be client ID
        "aud": EPIC_TOKEN_URL,  # Must exactly match token URL
        "jti": jti,  # Unique identifier
        "iat": now,  # Issued at time
        "nbf": now,  # Not before time
        "exp": now + 300  # Expires in exactly 5 minutes (Epic's maximum)
    }

    # Generate the JWT
    token = jwt.encode(
        payload=claims,
        key=private_key,
        algorithm="RS384",
        headers=headers
    )

    return token

if __name__ == "__main__":
    try:
        # Generate both production and non-production tokens
        non_prod_token = generate_test_jwt(use_prod=False)
        
        print("\nNon-Production Environment")
        print("=" * 50)
        print("Client ID:", NON_PROD_CLIENT_ID)
        print("\nJWT Token:")
        print(non_prod_token)
        
        print("\nProduction Environment")
        print("=" * 50)
        print("Client ID:", PROD_CLIENT_ID)
        prod_token = generate_test_jwt(use_prod=True)
        print("\nJWT Token:")
        print(prod_token)
        
        print("\nImportant Notes:")
        print("1. Verify tokens at https://jwt.io")
        print("2. JWKS URL for verification:", JWKS_URL)
        print("3. Wait for key propagation:")
        print("   - Sandbox: up to 60 minutes")
        print("   - Production: up to 12 hours")
        print("4. Use correct environment-specific token")
    except Exception as e:
        print(f"Error generating JWT: {e}") 