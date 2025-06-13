#!/usr/bin/env python3
import jwt
import datetime
import uuid
import json
import argparse

def generate_epic_jwt(private_key_path, client_id, jwks_url=None, expiration_minutes=5):
    """
    Generate a JWT token for Epic API authentication
    
    Args:
        private_key_path (str): Path to the RSA private key file
        client_id (str): Epic client ID
        jwks_url (str): URL to the JWKS file (optional)
        expiration_minutes (int): Token expiration time in minutes
        
    Returns:
        str: Generated JWT token
    """
    with open(private_key_path, 'r') as key_file:
        private_key = key_file.read()
    
    # Current time and expiration time
    now = datetime.datetime.utcnow()
    exp_time = now + datetime.timedelta(minutes=expiration_minutes)
    
    # Create the JWT payload
    payload = {
        'iss': client_id,               # Issuer - your client ID
        'sub': client_id,               # Subject - typically same as issuer for client_credentials
        'aud': 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token',  # Audience - Epic token endpoint
        'jti': str(uuid.uuid4()),       # JWT ID - unique identifier
        'iat': now,                     # Issued at
        'nbf': now,                     # Not valid before
        'exp': exp_time                 # Expiration time
    }
    
    # Headers
    headers = {
        'alg': 'RS384',                 # Algorithm
        'typ': 'JWT',                   # Type
        'kid': 'atlas-key-001'          # Key ID - must match the kid in your JWKS
    }
    
    # Add JKU header if JWKS URL is provided
    if jwks_url:
        headers['jku'] = jwks_url
    
    # Generate the JWT
    token = jwt.encode(
        payload=payload,
        key=private_key,
        algorithm='RS384',
        headers=headers
    )
    
    return token

def main():
    parser = argparse.ArgumentParser(description='Generate JWT token for Epic API authentication')
    parser.add_argument('--key', required=True, help='Path to the RSA private key file')
    parser.add_argument('--client-id', required=True, help='Epic client ID')
    parser.add_argument('--jwks-url', help='URL to the JWKS file')
    parser.add_argument('--expiration', type=int, default=5, help='Token expiration time in minutes (default: 5)')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    token = generate_epic_jwt(
        args.key,
        args.client_id, 
        args.jwks_url,
        args.expiration
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(token)
        print(f"JWT token written to {args.output}")
    else:
        print(token)

if __name__ == "__main__":
    main() 