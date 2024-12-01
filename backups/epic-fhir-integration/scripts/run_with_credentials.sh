#!/bin/bash
# Script to run any command with EPIC credentials loaded from key.md

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Running with automatic Epic credentials ===${NC}"

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

# Set the client ID
export EPIC_CLIENT_ID="atlas-client-001"
echo -e "${GREEN}Set EPIC_CLIENT_ID to $EPIC_CLIENT_ID${NC}"

# Set the private key from key.md
export EPIC_PRIVATE_KEY="$(cat "$KEY_FILE")"
echo -e "${GREEN}Loaded EPIC_PRIVATE_KEY from $KEY_FILE${NC}"

# Run the command that was passed as arguments
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}No command specified. Credentials are now set in the environment.${NC}"
    echo "You can now run any script that requires Epic credentials."
    echo "Examples:"
    echo "  python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --strict"
    echo "  ./scripts/test_strict_mode.sh"
else
    echo -e "${YELLOW}Running command with Epic credentials:${NC}"
    echo "$@"
    echo ""
    
    # Execute the command with all arguments
    "$@"
    
    # Capture exit code
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}Command completed successfully${NC}"
    else
        echo -e "\n${RED}Command failed with exit code $EXIT_CODE${NC}"
    fi
    
    exit $EXIT_CODE
fi 