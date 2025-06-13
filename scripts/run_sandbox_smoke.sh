#!/bin/bash

# EPIC FHIR Sandbox Smoke Test Runner
# This script runs a quick end-to-end test with the EPIC Sandbox API
# to verify auth, extract, transform, and validation logic.

set -e  # Exit on any error

# Default test patient from testing plan
SANDBOX_PATIENT_ID=${PATIENT_ID:-"Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"}

# Check for required environment variables
if [ -z "$EPIC_BASE_URL" ] || [ -z "$EPIC_CLIENT_ID" ] || [ -z "$EPIC_PRIVATE_KEY" ]; then
    if [ -f "epic_token.json" ]; then
        echo "Using local epic_token.json (not recommended for production)"
    else
        echo "Error: Required environment variables not set. Set them or run setup_epic_jwt.sh first."
        echo "Required: EPIC_BASE_URL, EPIC_CLIENT_ID, EPIC_PRIVATE_KEY"
        exit 1
    fi
fi

echo "==== EPIC FHIR Sandbox Smoke Test ===="
echo "Patient ID: $SANDBOX_PATIENT_ID"
echo "Base URL: $EPIC_BASE_URL"

# Check if venv exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
fi

# Create output directory if it doesn't exist
mkdir -p local_output/bronze local_output/silver

echo "==== Running smoke test pipeline ===="
python run_local_fhir_pipeline.py \
  --patient-id "$SANDBOX_PATIENT_ID" \
  --resources patient,observation,encounter,condition,medicationrequest,diagnosticreport \
  --steps token,extract,transform \
  --debug

# Check exit code
if [ $? -eq 0 ]; then
    echo "==== Smoke test completed successfully! ===="
    
    # Verify the output files exist
    echo "==== Verifying output files ===="
    
    if ls local_output/bronze/*.json 1> /dev/null 2>&1; then
        BRONZE_COUNT=$(ls local_output/bronze/*.json | wc -l)
        echo "✅ Bronze files created: $BRONZE_COUNT"
    else
        echo "❌ No Bronze files found!"
        exit 1
    fi
    
    if ls local_output/silver/* 1> /dev/null 2>&1; then
        SILVER_COUNT=$(find local_output/silver -type f | wc -l)
        echo "✅ Silver files/directories created: $SILVER_COUNT"
    else
        echo "❌ No Silver output found!"
        exit 1
    fi
    
    echo "==== Smoke test PASSED ===="
    exit 0
else
    echo "==== Smoke test FAILED ===="
    exit 1
fi 