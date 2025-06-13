#!/usr/bin/env python3
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import json
import base64
import os

def int_to_base64(value):
    """Convert an integer to a base64url-encoded string"""
    value_hex = format(value, 'x')
    # Ensure even length
    if len(value_hex) % 2 == 1:
        value_hex = '0' + value_hex
    value_bytes = bytes.fromhex(value_hex)
    encoded = base64.urlsafe_b64encode(value_bytes).rstrip(b'=')
    return encoded.decode('ascii')

def generate_jwks(private_key_path):
    """Generate JWKS from RSA private key"""
    # Read the private key
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("Key is not an RSA private key")

    # Get the public key numbers
    public_numbers = private_key.public_key().public_numbers()

    # Create the JWK
    jwk = {
        "kty": "RSA",
        "kid": "atlas-key-001",
        "alg": "RS384",
        "use": "sig",
        "n": int_to_base64(public_numbers.n),
        "e": int_to_base64(public_numbers.e)
    }

    # Create the JWKS
    jwks = {
        "keys": [jwk]
    }

    # Create .well-known directory if it doesn't exist
    os.makedirs('.well-known', exist_ok=True)
    
    # Save to file
    with open('.well-known/jwks.json', 'w') as f:
        json.dump(jwks, f, indent=2)

    print("\nGenerated JWKS:")
    print(json.dumps(jwks, indent=2))
    print("\nJWKS has been saved to .well-known/jwks.json")
    print("\nPlease update your JWKS endpoint (https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json)")
    print("with the contents of jwks.json")

if __name__ == "__main__":
    generate_jwks('private_key.pem') 