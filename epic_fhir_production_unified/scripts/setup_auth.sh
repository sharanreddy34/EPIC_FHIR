#!/bin/bash

# Exit on error
set -e

# Function to check if command succeeded
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1 failed"
        exit 1
    fi
}

echo "Starting Backend Services Client Setup..."

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Using project: $PROJECT_ID"

# 1. Create service account
echo "Creating service account..."
gcloud iam service-accounts create bulk-fhir-client \
    --display-name="Bulk FHIR Export Client" \
    --description="Service account for bulk FHIR exports"
check_success "Created service account: bulk-fhir-client"

# Get the service account email
SA_EMAIL="bulk-fhir-client@${PROJECT_ID}.iam.gserviceaccount.com"

# 2. Grant Healthcare FHIR Resource Reader role
echo "Granting Healthcare FHIR Resource Reader role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/healthcare.fhirResourceReader"
check_success "Granted FHIR Resource Reader role"

# 3. Create and download service account key
echo "Creating service account key..."
gcloud iam service-accounts keys create bulk-fhir-client.json \
    --iam-account=${SA_EMAIL}
check_success "Created and downloaded service account key"

# 4. Generate JWKS from the service account key
echo "Generating JWKS from service account key..."
python3 - <<'EOF'
import jwt, json, datetime, uuid, sys, base64, os
from cryptography.hazmat.primitives import serialization

# Load the service account key
key_data = json.load(open('bulk-fhir-client.json'))
private_key = key_data['private_key']

# Convert PEM to key object
key = serialization.load_pem_private_key(
    private_key.encode(),
    password=None
)

# Get public key and create JWK
pub = key.public_key()
jwk = jwt.algorithms.RSAAlgorithm.to_jwk(pub)

# Write JWKS
with open('jwks.json','w') as f:
    f.write('{"keys":['+jwk+']}')

print("✅ Generated JWKS file: jwks.json")
EOF

echo "
✨ Backend Services Client Setup Complete! ✨
- Created service account: ${SA_EMAIL}
- Granted FHIR Resource Reader role
- Downloaded key: bulk-fhir-client.json
- Generated JWKS file: jwks.json

Next steps:
1. Host the jwks.json file at a public URL (e.g., GitHub Pages)
2. Update your application configuration with the service account key path
3. Test authentication using test_epic_auth.py
" 