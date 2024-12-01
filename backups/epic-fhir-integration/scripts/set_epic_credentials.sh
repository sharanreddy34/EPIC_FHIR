#!/bin/bash
# Set Epic FHIR API credentials for testing
# These values should be kept secure and not committed to version control

# Production Client ID
export EPIC_CLIENT_ID="43e4309a-67ab-4c3a-b583-f062c35d3791"

# Uncomment to use Non-Production Client ID instead
# export EPIC_CLIENT_ID="02317de4-f128-4607-989b-07892f678580"

# You'll need to set your client secret - this would typically be provided separately
# and should never be committed to version control
echo "Please enter your Epic FHIR API client secret: "
read -s EPIC_CLIENT_SECRET
export EPIC_CLIENT_SECRET

echo "Epic FHIR API credentials set:"
echo "  EPIC_CLIENT_ID: $EPIC_CLIENT_ID"
echo "  EPIC_CLIENT_SECRET: [hidden]"
echo ""
echo "You can now run the FHIR pipeline with real API calls:"
echo "  python -m fhir_pipeline.cli extract --patient-id <ID> --debug" 