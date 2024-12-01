import jwt
import json
from datetime import datetime

def decode_and_validate_jwt(token):
    """Decode JWT without verification and validate claims format."""
    # Decode without verification to check the claims
    decoded = jwt.decode(token, options={"verify_signature": False})
    
    # Pretty print the decoded token
    print("\nDecoded JWT Claims:")
    print(json.dumps(decoded, indent=2))
    
    # Validate required claims
    print("\nClaims Validation:")
    
    # Check iss and sub match
    print(f"✓ iss and sub match: {decoded['iss'] == decoded['sub']}")
    
    # Check aud format
    expected_aud = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
    print(f"✓ aud exact match: {decoded['aud'] == expected_aud}")
    
    # Check timing claims
    now = datetime.now().timestamp()
    print(f"✓ iat ≤ now: {decoded['iat'] <= now}")
    print(f"✓ nbf ≤ now: {decoded['nbf'] <= now}")
    print(f"✓ exp > now: {decoded['exp'] > now}")
    print(f"✓ exp - iat ≤ 300s: {decoded['exp'] - decoded['iat'] <= 300}")
    
    # Check jti length
    print(f"✓ jti length ≤ 151: {len(decoded['jti']) <= 151}")
    
    # Get header
    header = jwt.get_unverified_header(token)
    print("\nJWT Header:")
    print(json.dumps(header, indent=2))
    
    return decoded, header

if __name__ == "__main__":
    # Get the JWT from generate_jwt.py
    import subprocess
    result = subprocess.run(['python', 'generate_jwt.py'], 
                          capture_output=True, text=True)
    
    # Extract tokens from output
    lines = result.stdout.split('\n')
    sandbox_token = None
    prod_token = None
    
    for i, line in enumerate(lines):
        if "JWT Token:" in line and i+1 < len(lines):
            if sandbox_token is None:
                sandbox_token = lines[i+1].strip()
            else:
                prod_token = lines[i+1].strip()
    
    print("\nSandbox Environment JWT Analysis")
    print("=" * 50)
    sandbox_claims, sandbox_header = decode_and_validate_jwt(sandbox_token)
    
    print("\nProduction Environment JWT Analysis")
    print("=" * 50)
    prod_claims, prod_header = decode_and_validate_jwt(prod_token) 