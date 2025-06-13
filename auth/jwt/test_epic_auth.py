import requests
from generate_jwt import generate_test_jwt, EPIC_TOKEN_URL

def test_epic_auth(use_prod=False):
    """
    Test Epic OAuth authentication following their strict requirements:
    - POST to /oauth2/token endpoint
    - Use application/x-www-form-urlencoded content type
    - All parameters in request body
    - Exact parameter names
    """
    # Generate a JWT token
    jwt_token = generate_test_jwt(use_prod=use_prod)
    
    # Prepare the token request with exact parameter names
    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': jwt_token,
        'scope': 'system/*.read'  # Adding required scope parameter for system-level read access
    }
    
    # Set proper headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    env_type = "Production" if use_prod else "Non-Production"
    print(f"\nTesting {env_type} Environment")
    print("=" * 50)
    print("Sending request to Epic's OAuth endpoint...")
    print(f"Token URL: {EPIC_TOKEN_URL}")
    
    print("\nRequest Headers:")
    for header, value in headers.items():
        print(f"{header}: {value}")
    
    print("\nRequest Payload:")
    for key, value in data.items():
        print(f"{key}: {value if key != 'client_assertion' else value[:50] + '...'}")
    
    try:
        response = requests.post(
            EPIC_TOKEN_URL,
            data=data,
            headers=headers
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print("\nResponse Headers:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print("\nResponse Body:")
        print(response.text)
        
        if response.ok:
            token_data = response.json()
            print("\nSuccessfully obtained access token!")
            print(f"Access Token: {token_data.get('access_token')[:50]}...")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')} seconds")
        else:
            print("\nNOTE: If you get invalid_client error:")
            print("1. Verify all JWT claims are correct")
            print("2. Wait for key propagation:")
            print("   - Sandbox: up to 60 minutes")
            print("   - Production: up to 12 hours")
        
    except requests.exceptions.RequestException as e:
        print(f"\nError making request: {e}")
    except ValueError as e:
        print(f"\nError parsing response: {e}")

if __name__ == "__main__":
    print("Epic OAuth Token Test")
    print("=" * 50)
    print("NOTE: After uploading a new public key, you must wait for propagation:")
    print("- Sandbox: up to 60 minutes")
    print("- Production: up to 12 hours")
    print("\nProceeding with test...")
    
    # Test non-production first
    test_epic_auth(use_prod=False)
    
    # Then test production
    test_epic_auth(use_prod=True) 