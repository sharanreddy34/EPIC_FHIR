#!/bin/bash
# Run FHIR pipeline with test patient using JWT authentication

set -e  # Exit on error

# Test patient ID
TEST_PATIENT_ID="T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

# Check if .env file exists and source it
if [ -f ".env" ]; then
    echo "Loading environment from .env file"
    source .env
else
    echo "No .env file found, environment variables must be set manually"
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "Virtual environment not found, running setup script"
    ./setup_dev.sh
fi

# Activate virtual environment
source venv/bin/activate

# Check for JWT requirements
if ! pip freeze | grep -q PyJWT; then
    echo "Installing JWT requirements"
    pip install PyJWT cryptography
fi

# Check for required environment variables
if [ -z "$EPIC_CLIENT_ID" ]; then
    echo "EPIC_CLIENT_ID environment variable is not set"
    echo "Either set it manually or run setup_epic_jwt.sh"
    exit 1
fi

# Check for private key
if [ -z "$EPIC_PRIVATE_KEY_PATH" ]; then
    EPIC_PRIVATE_KEY_PATH="auth/keys/rsa_private.pem"
    echo "Using default private key path: $EPIC_PRIVATE_KEY_PATH"
fi

if [ ! -f "$EPIC_PRIVATE_KEY_PATH" ]; then
    echo "Private key not found at $EPIC_PRIVATE_KEY_PATH"
    echo "Run setup_epic_jwt.sh to configure JWT authentication"
    exit 1
fi

# Default to non-production environment
ENVIRONMENT=${EPIC_ENVIRONMENT:-"non-production"}

echo "----------------------------------------"
echo "Running FHIR pipeline with test patient"
echo "----------------------------------------"
echo "Patient ID: $TEST_PATIENT_ID"
echo "Environment: $ENVIRONMENT"
echo "Private key: $EPIC_PRIVATE_KEY_PATH"
echo "----------------------------------------"

# Run the pipeline
python -m fhir_pipeline.cli extract \
    --patient-id $TEST_PATIENT_ID \
    --environment $ENVIRONMENT \
    --private-key $EPIC_PRIVATE_KEY_PATH \
    --debug

# Check if the extraction was successful
if [ $? -eq 0 ]; then
    echo "----------------------------------------"
    echo "Extraction completed successfully!"
    echo "Results saved to: patient_data/$TEST_PATIENT_ID"
    echo "----------------------------------------"
else
    echo "----------------------------------------"
    echo "Extraction failed!"
    echo "Check the logs for more information."
    echo "----------------------------------------"
    exit 1
fi 