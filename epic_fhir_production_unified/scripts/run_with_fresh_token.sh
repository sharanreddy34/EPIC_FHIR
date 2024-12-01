#!/bin/bash
# Script to refresh Epic FHIR API token and run E2E test

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Epic FHIR API Token Refresh and E2E Test ===${NC}"

# Change to the project root directory
cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd)"

# Check if the key file exists
KEY_FILE="${ROOT_DIR}/../docs/key.md"
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}Error: Key file not found at $KEY_FILE${NC}"
    echo "Please ensure the key file exists before running this script"
    exit 1
fi

# Set up environment variables
export EPIC_CLIENT_ID="atlas-client-001"
echo -e "${GREEN}Set EPIC_CLIENT_ID to $EPIC_CLIENT_ID${NC}"

export EPIC_PRIVATE_KEY="$(cat "$KEY_FILE")"
echo -e "${GREEN}Loaded EPIC_PRIVATE_KEY from $KEY_FILE${NC}"

# Create secrets directory if it doesn't exist
mkdir -p secrets

# Refresh the token
echo -e "\n${YELLOW}Step 1: Refreshing Epic FHIR API token${NC}"
python scripts/refresh_epic_token.py --token-file secrets/epic_token.json --debug

# Check if token refresh was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Token refresh failed${NC}"
    echo "Check the error logs above for details"
    exit 1
fi

echo -e "${GREEN}Token refresh successful${NC}"

# Run the E2E test
echo -e "\n${YELLOW}Step 2: Running E2E test with fresh token${NC}"

# Parse any extra arguments
EXTRA_ARGS=""
if [ "$1" == "--strict" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --strict"
    echo "Running in strict mode (no mock data fallbacks)"
fi

if [ "$1" == "--debug" ] || [ "$2" == "--debug" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --debug"
    echo "Running with debug logging enabled"
fi

# Run the test
python e2e_test_fhir_pipeline.py --output-dir e2e_test_output $EXTRA_ARGS

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}E2E test completed successfully${NC}"
else
    echo -e "\n${RED}E2E test failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE 