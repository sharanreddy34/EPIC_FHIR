# Strict Mode Implementation

## Overview
Strict mode is a new feature that prevents the pipeline from falling back to mock data when real API calls fail. This ensures that only real data is processed through the pipeline and that errors are properly surfaced, rather than being hidden by mock data fallbacks.

## Problems Solved
1. **Mock Data Fallbacks**: Previously, the code would silently fall back to using mock data when real API calls failed
2. **Error Masking**: Real API issues were masked by mock data generation
3. **Mixed Data**: Pipeline might process a mix of real and mock data, making results unreliable

## Implementation Details

### Command-Line Flags
Two new command-line flags have been added:

1. `--strict`: For both scripts
   ```bash
   # In e2e_test_fhir_pipeline.py
   python e2e_test_fhir_pipeline.py --strict
   
   # In run_local_fhir_pipeline.py
   python run_local_fhir_pipeline.py --patient-id <id> --strict
   ```

2. Conflicts with `--mock` flag
   ```bash
   # This will fail with an error
   python run_local_fhir_pipeline.py --patient-id <id> --mock --strict
   ```

### Behavior Changes
When strict mode is enabled:

1. **API Errors**: Fail immediately with clear error messages rather than falling back to mock data
2. **Extraction Failures**: No mock data generation when real API calls fail
3. **Transformation Failures**: No mock silver data generation when transformations fail
4. **Incompatible Files**: Fail on incompatible file formats rather than attempting to process them

### Files Modified

1. **e2e_test_fhir_pipeline.py**
   - Added strict_mode parameter to E2ETest class
   - Updated run_test to check strict_mode before creating mock data
   - Updated transform_resources to respect strict_mode
   - Added --strict command-line flag

2. **scripts/run_local_fhir_pipeline.py**
   - Added strict_mode parameter to run_extract_resources and run_transform_resources
   - Updated fallback behavior to check strict_mode before using mock data
   - Added --strict command-line flag
   - Added validation to prevent using --strict and --mock together

## Sample Error Messages

### In Strict Mode
```
ERROR: Error during extraction phase: [specific error message]
ERROR: Running in strict mode - aborting test due to extraction failure
ERROR: Set --strict=false to allow mock data fallbacks for testing
```

### In Regular Mode
```
ERROR: Error during extraction phase: [specific error message]
WARNING: Will proceed with mock extraction for demonstration purposes
WARNING: Use --strict flag to disable mock fallbacks
INFO: Creating mock resources for demonstration purposes only
WARNING: MOCK DATA WARNING: These are not real patient resources!
```

## Usage Recommendations

1. **Development/Testing**: Use normal mode (no --strict flag) for development and initial testing
2. **Production/QA**: Use strict mode (--strict flag) for production or quality assurance testing
3. **Data Validation**: Always use strict mode when validating real data through the pipeline
4. **Debugging**: Use normal mode with --debug flag when debugging to see where issues occur

## Future Enhancements

1. Add partial strict mode options (e.g., strict for extraction but allow mock transformations)
2. Add validation checks for data quality when running in strict mode
3. Implement automatic retry logic for API failures before failing in strict mode
4. Add more detailed diagnostics for strict mode failures 