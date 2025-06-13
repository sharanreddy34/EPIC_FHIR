#!/usr/bin/env python3
import requests
import json
import argparse
import sys
from generate_epic_jwt import generate_epic_jwt

def get_epic_token(jwt_token, token_endpoint='https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token', scope='system/*.read'):
    """
    Exchange a JWT token for an Epic access token
    
    Args:
        jwt_token (str): JWT assertion token
        token_endpoint (str): Epic token endpoint URL
        scope (str): Requested scope for the access token
        
    Returns:
        dict: The token response containing access_token and other details
    """
    data = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': jwt_token,
        'scope': scope
    }
    
    response = requests.post(token_endpoint, data=data)
    
    if response.status_code != 200:
        print(f"Error getting token: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def main():
    parser = argparse.ArgumentParser(description='Get Epic access token using JWT')
    parser.add_argument('--jwt', help='JWT token (if not provided, will be generated)')
    parser.add_argument('--key', help='Path to the RSA private key file (for JWT generation)')
    parser.add_argument('--client-id', help='Epic client ID (for JWT generation)')
    parser.add_argument('--jwks-url', help='URL to the JWKS file (for JWT generation)')
    parser.add_argument('--token-endpoint', default='https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token', 
                        help='Epic token endpoint URL')
    parser.add_argument('--scope', default='system/*.read', help='Requested scope')
    parser.add_argument('--output', help='Output file path for token response')
    
    args = parser.parse_args()
    
    # Generate JWT if not provided
    jwt_token = args.jwt
    if not jwt_token:
        if not args.key or not args.client_id:
            print("Error: Either --jwt or both --key and --client-id must be provided")
            sys.exit(1)
        
        jwt_token = generate_epic_jwt(args.key, args.client_id, args.jwks_url)
    
    # Get token
    token_response = get_epic_token(jwt_token, args.token_endpoint, args.scope)
    
    if not token_response:
        sys.exit(1)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(token_response, f, indent=2)
        print(f"Token response written to {args.output}")
    else:
        print(json.dumps(token_response, indent=2))
    
    # Print the access token for easy copying
    print("\nAccess Token:")
    print(token_response.get('access_token', 'No access token found'))

if __name__ == "__main__":
    main() 