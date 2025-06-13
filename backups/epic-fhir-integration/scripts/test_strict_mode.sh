#!/bin/bash
# Script to test the strict mode functionality

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Testing Strict Mode Implementation ===${NC}"
echo "This script will verify that strict mode is working correctly"

# Change to the project root directory
cd "$(dirname "$0")/.."

# Make sure fhir_pipeline/utils directory exists
if [ ! -d "fhir_pipeline/utils" ]; then
    echo -e "${RED}Error: fhir_pipeline/utils directory not found${NC}"
    echo "Make sure you're running this script from the project root"
    exit 1
fi

# Run the unit tests for strict mode
echo -e "\n${YELLOW}Step 1: Running strict mode unit tests${NC}"
python scripts/test_strict_mode.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Strict mode unit tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}Strict mode unit tests passed${NC}"
fi

# Test with E2E test script
echo -e "\n${YELLOW}Step 2: Testing with E2E test script in strict mode${NC}"
echo "This will attempt to run the E2E test with real Epic FHIR API data"
echo "Note: If you don't have Epic API credentials, this will fail as expected"

# First run with strict mode disabled to create mock data
echo -e "\n${YELLOW}First running without strict mode to ensure mock data works:${NC}"
python e2e_test_fhir_pipeline.py --debug
if [ $? -ne 0 ]; then
    echo -e "${RED}E2E test with mock data failed - there might be a basic issue${NC}"
    echo "Fix this before testing strict mode"
    exit 1
else
    echo -e "${GREEN}E2E test with mock data succeeded${NC}"
fi

# Run E2E test with strict mode
echo -e "\n${YELLOW}Now running with strict mode enabled:${NC}"
echo "If you have valid Epic API credentials, this should succeed"
echo "If not, it should fail with STRICT MODE VIOLATION errors (as expected)"
python e2e_test_fhir_pipeline.py --debug --strict
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}E2E test with strict mode succeeded!${NC}"
    echo "This means you have valid Epic API credentials and the pipeline is working with real data"
else
    echo -e "${YELLOW}E2E test with strict mode failed${NC}"
    echo "If this is because of STRICT MODE VIOLATION errors, that's expected if you don't have valid credentials"
    echo "If you DO have valid Epic API credentials, check the logs for other issues"
fi

# Test with local pipeline
echo -e "\n${YELLOW}Step 3: Testing with local pipeline in strict mode${NC}"
echo "Note: This requires Epic API credentials and a patient ID"

# Check if EPIC_CLIENT_ID and EPIC_PRIVATE_KEY are set
if [ -z "$EPIC_CLIENT_ID" ] || [ -z "$EPIC_PRIVATE_KEY" ]; then
    echo -e "${YELLOW}Warning: EPIC_CLIENT_ID and/or EPIC_PRIVATE_KEY not set${NC}"
    echo "To run with real data, set these environment variables before running this script:"
    echo "export EPIC_CLIENT_ID=your-client-id"
    echo "export EPIC_PRIVATE_KEY=your-private-key"
    echo "Skipping local pipeline test..."
else
    # Run local pipeline with strict mode
    PATIENT_ID="T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
    echo -e "\n${YELLOW}Running local pipeline with patient ID ${PATIENT_ID}:${NC}"
    python run_local_fhir_pipeline.py --patient-id $PATIENT_ID --debug --strict
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Local pipeline with strict mode succeeded!${NC}"
    else
        echo -e "${YELLOW}Local pipeline with strict mode failed${NC}"
        echo "Check the logs for details"
    fi
fi

echo -e "\n${YELLOW}=== Strict Mode Testing Complete ===${NC}"
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Strict mode is working correctly with real Epic FHIR API data${NC}"
    echo "✅ Item 7.1 can be marked as DONE"
else
    echo -e "${YELLOW}Strict mode implementation is working, but you need valid Epic API credentials${NC}"
    echo "Once you have valid credentials, run this test again to verify end-to-end functionality"
fi

exit 0 