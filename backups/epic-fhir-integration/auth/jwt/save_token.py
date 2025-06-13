#!/usr/bin/env python3
import json
import os
import requests
from generate_jwt import generate_test_jwt, EPIC_TOKEN_URL

def get_and_save_token(use_prod=False):
    """
    Get an access token from Epic and save it to a file
    
    Args:
        use_prod (bool): Whether to use production environment
    
    Returns:
        str: The access token
    """
    # Generate a JWT token
    jwt_token = generate_test_jwt(use_prod=use_prod)
    
    # Prepare the token request
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
    
    env_type = "Production" if use_prod else "Non-Production"
    print(f"Getting token for {env_type} environment...")
    
    try:
        response = requests.post(
            EPIC_TOKEN_URL,
            data=data,
            headers=headers
        )
        
        if response.ok:
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            # Save token to file
            token_file = "../../epic_token.json"
            with open(token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            print(f"Token saved to {os.path.abspath(token_file)}")
            return access_token
        else:
            print(f"Error getting token: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    token = get_and_save_token(use_prod=False)
    if token:
        print("Successfully obtained and saved token!")
        print(f"Token: {token[:50]}...")
    else:
        print("Failed to get token") 