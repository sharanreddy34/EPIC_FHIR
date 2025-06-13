#!/bin/bash
# Run all advanced FHIR tools tests with mock mode enabled

set -e  # Exit on error

# Directory where test outputs will be stored
OUTPUT_DIR="fhir_test_output_$(date +%Y%m%d_%H%M%S)"

echo "Running all FHIR tests with output to $OUTPUT_DIR"

# Set environment variables for mock mode
export PYTHONPATH="$PYTHONPATH:./epic-fhir-integration"
export USE_MOCK_MODE=true

# Run main E2E test with mock mode
echo "----- Running Advanced FHIR Tools E2E Test -----"
python epic-fhir-integration/scripts/advanced_fhir_tools_e2e_test.py --output-dir $OUTPUT_DIR --debug --mock

# Run data quality tests across tiers
echo "----- Running Data Quality Tests -----"
python epic-fhir-integration/scripts/test_data_quality.py --input-dir epic-fhir-integration/test_data --output-dir $OUTPUT_DIR/quality --mock

# Run validation tests
echo "----- Running Validation Tests -----"
python epic-fhir-integration/scripts/test_validation.py --input-dir epic-fhir-integration/test_data --output-dir $OUTPUT_DIR/validation --mock

echo "All tests completed. Results are in $OUTPUT_DIR"

# Run a final summary script to compile all results
echo "----- Generating Summary Report -----"
cat > $OUTPUT_DIR/summary.md << EOF
# FHIR Testing Suite Summary Report

**Generated:** $(date "+%Y-%m-%d %H:%M:%S")

## Test Results

- **Advanced FHIR Tools E2E Test**: $OUTPUT_DIR/advanced_fhir_tools_test_report.md
- **Data Quality Tests**: $OUTPUT_DIR/quality/data_quality_report.md
- **Validation Tests**: $OUTPUT_DIR/validation/validation_report.md

## Next Steps

1. Review validation errors and warnings
2. Improve data quality in lower tiers
3. Ensure conformance to profiles in Gold tier
4. Test with real Epic FHIR API endpoints

## Completed Tasks

- [x] Set up test environment
- [x] Created sample FHIR resources for all tiers
- [x] Implemented mock services for testing
- [x] Executed all test scripts successfully
- [x] Generated comprehensive test reports

## Remaining Tasks

- [ ] Connect to live Epic FHIR API
- [ ] Test with real patient data
- [ ] Implement Bronze-to-Silver-to-Gold transformation pipeline
- [ ] Validate Gold resources against US Core profiles
- [ ] Prepare Gold resources for LLM consumption
EOF

echo "Summary report generated: $OUTPUT_DIR/summary.md"
