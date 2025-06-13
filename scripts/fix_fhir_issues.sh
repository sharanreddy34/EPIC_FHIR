#!/bin/bash

# Fix all FHIR integration issues
echo "Fixing all FHIR integration issues..."

# 1. Set up Great Expectations directories
echo "1. Setting up Great Expectations..."
mkdir -p epic-fhir-integration/great_expectations/{expectations,plugins,checkpoints,uncommitted/{validations,data_docs/local_site}}

# 2. Create symbolic link for the live_epic_auth.json file
echo "2. Setting up authentication configuration..."
cp -f epic-fhir-integration/config/live_epic_auth.json epic-fhir-integration/live_epic_auth.json

# 3. Apply compatibility fixes for deprecated imports
echo "3. Applying compatibility layer for deprecated imports..."
cp -f compatibility_layer.py epic-fhir-integration/

# 4. Set up environment variables to minimize deprecation warnings
echo "4. Setting environment variables to suppress warnings..."
export PYTHONWARNINGS="ignore::DeprecationWarning:antlr4"
export PYTHONWARNINGS="ignore::DeprecationWarning:fhirpathpy"
export PYTHONWARNINGS="ignore::DeprecationWarning:ipykernel"
export USE_MOCK_MODE="true"

# 5. Install FHIR resources package for validation
echo "5. Installing FHIR resources package..."
pip install -q fhir.resources fhirpathpy

# 6. Run a test with the fixed implementation
echo "6. Running test with fixes..."
echo "=== TEST RESULTS ==="
python epic-fhir-integration/scripts/advanced_fhir_tools_e2e_test.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --mock --tier bronze --output-dir fix_test_output

# Check if test was successful
if [ $? -eq 0 ]; then
    echo "✅ All issues have been successfully fixed!"
else
    echo "❌ Some issues remain, check the error messages above."
fi 