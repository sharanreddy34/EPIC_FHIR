# Epic FHIR Integration Debugging Guide

This guide explains the debugging features available in the Epic FHIR integration scripts.

## Overview

The codebase includes comprehensive logging and debugging capabilities to help diagnose issues with the FHIR integration. These features include:

- Detailed logging at multiple levels (INFO, DEBUG, WARNING, ERROR)
- Performance timing for API calls and processing steps
- Response content inspection
- Error tracing with stack traces
- Diagnostic file output
- Mock mode for testing without real API access

## Enabling Debug Mode

All scripts support a `--debug` flag that enables verbose logging:

```bash
# Extract test patient data with debug output
python extract_test_patient.py --patient-id PATIENT_ID --debug

# Run the full pipeline with debug output
python run_local_fhir_pipeline.py --patient-id PATIENT_ID --debug

# Test patient extraction with debug output
python test_patient_extraction.py --patient-id PATIENT_ID --debug
```

## Debug Log Files

When debug mode is enabled, the scripts will create log files in addition to console output:

- `debug_extract.log` - Debug output from extract_test_patient.py
- `debug_pipeline.log` - Debug output from run_local_fhir_pipeline.py
- `debug_test.log` - Debug output from test_patient_extraction.py

## Mock Mode

All scripts support a `--mock` flag to generate mock data instead of making real API calls:

```bash
# Extract test patient data using mock mode
python extract_test_patient.py --patient-id PATIENT_ID --mock

# Run the full pipeline using mock mode
python run_local_fhir_pipeline.py --patient-id PATIENT_ID --mock

# Test patient extraction using mock mode
python test_patient_extraction.py --patient-id PATIENT_ID --mock --check-only
```

## Execution Reports

The pipeline script generates an execution report in JSON format after completion:

```json
{
  "execution_time": 45.23,
  "patient_id": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
  "steps": {
    "token": {
      "success": true,
      "duration_seconds": 2.45
    },
    "extract": {
      "success": true,
      "duration_seconds": 15.67
    },
    ...
  },
  "overall_success": true,
  "timestamp": "2023-06-15T08:45:32.123456",
  "command_line_args": {
    "patient_id": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
    "output_dir": "./local_output",
    "steps": "all",
    "debug": true,
    "mock": false
  }
}
```

## Diagnostic Information Available

The following diagnostic information is available in debug mode:

1. **Authentication**
   - Token request/response details
   - Token expiration and validity
   - Authentication errors

2. **API Calls**
   - Request URLs and parameters
   - Response status codes and headers
   - Response body content (for errors)
   - Response timing
   - Rate limiting information

3. **Pipeline Steps**
   - Execution time for each step
   - Success/failure status
   - Input/output file counts
   - Data statistics

4. **Error Handling**
   - Detailed error messages
   - Stack traces
   - Response details for API errors

## Debugging Common Issues

### Authentication Failures

If you encounter authentication issues:

1. Check the debug logs for token request/response details
2. Verify that your client ID and secret are correct
3. Examine the token response for error messages
4. Use mock mode to test the pipeline without authentication

### API Call Failures

If API calls are failing:

1. Check the debug logs for request/response details
2. Verify that the API URL is correct
3. Check for rate limiting issues (429 responses)
4. Examine response bodies for error messages

### Pipeline Failures

If the pipeline is failing:

1. Run with `--debug` to get detailed logs
2. Check the execution report for step-specific failures
3. Look for error messages in the logs
4. Try running with individual steps (e.g., `--steps token,extract`)

## Contact

For additional help, please contact the ATLAS Palantir team. 