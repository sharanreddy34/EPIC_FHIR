#!/bin/bash
# Setup development environment for FHIR pipeline

set -e  # Exit on error

echo "Setting up FHIR pipeline development environment"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Create directories for tests
mkdir -p fhir_pipeline/io/
mkdir -p fhir_pipeline/transforms/
mkdir -p fhir_pipeline/tests/

# Copy FHIR client to proper location if needed
if [ ! -f "fhir_pipeline/io/fhir_client.py" ]; then
    echo "Copying FHIR client to package..."
    cp -n lib/fhir_client.py fhir_pipeline/io/fhir_client.py || true
fi

# Create required __init__.py files if they don't exist
touch fhir_pipeline/io/__init__.py
touch fhir_pipeline/transforms/__init__.py
touch fhir_pipeline/tests/__init__.py

echo "Setup complete! You can now run:"
echo "  source venv/bin/activate"
echo "  python -m fhir_pipeline.cli extract --patient-id <ID>"
echo ""
echo "For real FHIR API calls, set environment variables:"
echo "  export EPIC_CLIENT_ID=your-client-id"
echo "  export EPIC_CLIENT_SECRET=your-client-secret" 