#!/usr/bin/env bash
set -e

# Create and activate a virtual environment
echo "Creating virtual environment..."
python -m venv .venv && source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e "transforms-python/."
pip install -r requirements.txt

# Export environment variables for development
export EPIC_BASE_URL=https://fhir.epic.com/api/FHIR/R4
export PYTHONPATH=$PYTHONPATH:$(pwd)/transforms-python/src

# Echo setup instructions
echo "Local development environment ready."
echo "To run a bronze transform locally, use:"
echo "python -m epic_fhir_integration.bronze.patient_bronze"
echo ""
echo "Remember to set up local secrets for EPIC_CLIENT_ID and EPIC_PRIVATE_KEY by running:"
echo "export EPIC_CLIENT_ID=your_client_id"
echo "export EPIC_PRIVATE_KEY=path_to_your_private_key.pem" 