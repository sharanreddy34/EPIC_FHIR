from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json
import base64
import os

def int_to_base64url(value):
    """Convert an integer to a Base64URL-encoded string"""
    value_hex = format(value, 'x')
    # Ensure even length
    if len(value_hex) % 2 == 1:
        value_hex = '0' + value_hex
    value_bytes = bytes.fromhex(value_hex)
    encoded = base64.urlsafe_b64encode(value_bytes).rstrip(b'=')
    return encoded.decode('ascii')

def generate_and_save_keys():
    # Generate a new RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Get the public key
    public_key = private_key.public_key()
    
    # Get the public numbers for JWKS
    public_numbers = public_key.public_numbers()
    
    # Create JWKS
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "atlas-key-001",
                "alg": "RS384",
                "use": "sig",
                "n": int_to_base64url(public_numbers.n),
                "e": int_to_base64url(public_numbers.e)
            }
        ]
    }
    
    # Make sure .well-known directory exists
    os.makedirs(".well-known", exist_ok=True)
    
    # Save private key
    with open("private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save JWKS
    with open(".well-known/jwks.json", "w") as f:
        json.dump(jwks, f, indent=2)
    
    print("Generated and saved new key pair:")
    print("- Private key: private_key.pem")
    print("- JWKS file: .well-known/jwks.json")

if __name__ == "__main__":
    generate_and_save_keys() 