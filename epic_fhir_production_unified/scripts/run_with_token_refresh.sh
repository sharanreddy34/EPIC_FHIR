#!/bin/bash
# Script to refresh Epic FHIR API token and run E2E test with fallback to existing token

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
    echo -e "${RED}Warning: Key file not found at $KEY_FILE${NC}"
    echo "Will attempt to use existing token if available"
else
    # Set up environment variables
    export EPIC_CLIENT_ID="atlas-client-001"
    echo -e "${GREEN}Set EPIC_CLIENT_ID to $EPIC_CLIENT_ID${NC}"

    export EPIC_PRIVATE_KEY="$(cat "$KEY_FILE")"
    echo -e "${GREEN}Loaded EPIC_PRIVATE_KEY from $KEY_FILE${NC}"
fi

# Create secrets directory if it doesn't exist
mkdir -p secrets

# Attempt to refresh the token
echo -e "\n${YELLOW}Step 1: Attempting to refresh Epic FHIR API token${NC}"
./simple_token_refresh.py --token-file secrets/epic_token.json --debug

# Check if token refresh failed
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Token refresh failed, checking for existing token${NC}"
    
    # Check if we have an existing token
    if [ -f "secrets/epic_token.json" ]; then
        echo -e "${GREEN}Using existing token from secrets/epic_token.json${NC}"
        # Check if token is expired (simple check - not foolproof)
        TOKEN_EXPIRY=$(jq -r '.expires_at // 0' secrets/epic_token.json 2>/dev/null)
        CURRENT_TIME=$(date +%s)
        
        if [ "$TOKEN_EXPIRY" -gt "$CURRENT_TIME" ]; then
            echo -e "${GREEN}Token is still valid (expires at $(date -r $TOKEN_EXPIRY))${NC}"
        else
            echo -e "${YELLOW}Warning: Token may be expired, but will try to use it anyway${NC}"
        fi
    else
        echo -e "${RED}No existing token found at secrets/epic_token.json${NC}"
        echo "Will continue but API calls may fail"
    fi
else
    echo -e "${GREEN}Token refresh successful${NC}"
fi

# Run the E2E test
echo -e "\n${YELLOW}Step 2: Running E2E test${NC}"

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