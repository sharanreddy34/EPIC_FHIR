#!/bin/bash
# Set up JWT-based authentication for Epic FHIR API
# This script helps to set up the required files and environment variables

set -e  # Exit on error

echo "Setting up JWT-based authentication for Epic FHIR API"

# Create auth directory if it doesn't exist
mkdir -p auth/keys

# Check if we need to get the private key - only if it doesn't exist
if [ ! -f "auth/keys/rsa_private.pem" ]; then
    echo "Private key file not found. Either:"
    echo "1. Copy an existing key to auth/keys/rsa_private.pem, or"
    echo "2. Generate a new key"
    echo ""
    read -p "Generate new RSA key? (y/n): " generate_key
    
    if [ "$generate_key" = "y" ]; then
        echo "Generating RSA key pair..."
        openssl genrsa -out auth/keys/rsa_private.pem 4096
        echo "Generated private key: auth/keys/rsa_private.pem"
        
        # Generate public key for JWKS
        openssl rsa -in auth/keys/rsa_private.pem -pubout -out auth/keys/rsa_public.pem
        echo "Generated public key: auth/keys/rsa_public.pem"
        
        # Generate key modulus and exponent for JWKS
        echo "Generating modulus and exponent for JWKS..."
        # This requires additional processing to create a JWKS file
        echo "JWKS creation requires manual steps."
        echo "See https://fhir.epic.com/Documentation?docId=oauth2&section=BackendOAuth2Guide for details."
        echo ""
        echo "NOTE: You'll need to host the JWKS file at a public URL and register it with Epic."
    fi
fi

# Get the client ID
read -p "Use production client ID? (y/n): " use_prod
if [ "$use_prod" = "y" ]; then
    client_id="43e4309a-67ab-4c3a-b583-f062c35d3791"
    environment="production"
else
    client_id="02317de4-f128-4607-989b-07892f678580"
    environment="non-production"
fi

# Symlink the private key to the expected location for the FHIR pipeline
if [ ! -f "fhir_pipeline/auth/keys" ]; then
    mkdir -p fhir_pipeline/auth/keys
fi

# Create a symlink to the private key if it exists
if [ -f "auth/keys/rsa_private.pem" ]; then
    ln -sf "../../../auth/keys/rsa_private.pem" "fhir_pipeline/auth/keys/rsa_private.pem"
    echo "Created symlink to private key in fhir_pipeline/auth/keys/"
fi

# Create a .env file with the configuration
cat > .env << EOF
# Epic FHIR API Configuration
EPIC_CLIENT_ID=$client_id
EPIC_PRIVATE_KEY_PATH=auth/keys/rsa_private.pem
EPIC_ENVIRONMENT=$environment

# JWKS Configuration
EPIC_JWKS_URL=https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json
EPIC_KEY_ID=atlas-key-001

# Pipeline Configuration
FHIR_DEBUG=true
EOF

echo "Created .env file with configuration"

# Add an entry to .gitignore to prevent committing private keys and tokens
if [ ! -f ".gitignore" ]; then
    touch .gitignore
fi

if ! grep -q "auth/keys/" .gitignore; then
    echo "auth/keys/" >> .gitignore
    echo "*.pem" >> .gitignore
    echo "epic_token.json" >> .gitignore
    echo ".env" >> .gitignore
    echo "Added private keys, tokens, and .env file to .gitignore"
fi

echo ""
echo "JWT Setup Complete!"
echo "----------------------------------------"
echo "To use JWT authentication for Epic FHIR API:"
echo ""
echo "1. Source the environment variables:"
echo "   source .env"
echo ""
echo "2. Run the FHIR pipeline:"
echo "   python -m fhir_pipeline.cli extract --patient-id <ID> --environment $environment --debug"
echo ""
echo "3. For more information, see the README.md"
echo "----------------------------------------"
echo ""
echo "IMPORTANT: If using a new private key, you must:"
echo "1. Create and publish a JWKS file containing the public key"
echo "2. Register the JWKS URL with Epic"
echo "3. Wait for key propagation (Sandbox: 60 min, Production: 12 hrs)" 