# FHIR Pipeline - Verified Run Guide

This guide explains how to run the complete FHIR pipeline using only real FHIR data from Epic, with no mock data fallbacks. The pipeline will fail fast if any step encounters an error, ensuring data integrity throughout the process.

## Prerequisites

1. **Authentication Setup**
   - Ensure the Epic private key is correctly configured
   - Test that token authentication works (`python auth/setup_epic_auth.py --test`)

2. **Required Files**
   - Confirm `resources_config.yaml` exists with proper API parameters
   - Verify that resource mapping files exist for all required resources

## Running the Complete Pipeline

Use the `run_complete_pipeline.py` script, which has been updated to prevent mock data fallbacks:

```bash
python run_complete_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug
```

### Key Parameters

- `--patient-id`: The Epic FHIR patient ID to process (required)
- `--output-dir`: Output directory (default: "output")
- `--debug`: Enable detailed logging
- `--strict`: Enable strict validation (recommended)
- `--steps`: Pipeline steps to run, comma-separated (default: "extract,transform,gold,verify")

## Ensuring Real Data

The updated pipeline includes several safeguards to ensure only real FHIR data is used:

1. **Authentication Validation**
   - Token refresh is required before extraction
   - Pipeline fails immediately if token is invalid

2. **Observation Resource Handling**
   - All Observation API calls include the required `category=laboratory` parameter
   - This prevents 401 errors when querying lab observations

3. **Bronze Layer Validation**
   - Extract step requires successful API data fetching
   - No fallback to existing data if extraction fails

4. **Silver Layer Transformation**
   - Requires valid bronze data - no mock data generation
   - Verifies that transformed data exists in silver layer

5. **Gold Layer Creation**
   - Requires valid silver data before proceeding
   - Validates gold output after transformation

## Verifying Results

After running the pipeline, the verification step will check:

1. Directory structure integrity
2. Resource type availability
3. File existence and sizing
4. Data validation metrics

The summary output will look like this:

```
OUTPUT VERIFICATION RESULTS
================================================================================
Total checks: 15
PASS: 12
WARN: 2
FAIL: 1
--------------------------------------------------------------------------------
✅ bronze/fhir_raw exists and has content - Raw FHIR resources
✅ silver/fhir_normalized exists and has content - Normalized FHIR resources
✅ gold exists and has content - Gold layer datasets
✅ Bronze layer contains Patient with 1 files
...
```

## Troubleshooting

If the pipeline fails, check the logs directory for detailed error information. Common issues include:

1. **Authentication Problems**
   - Check `logs/pipeline_[timestamp].log` for token-related errors
   - Verify private key location and JWT configuration

2. **Missing Resource Types**
   - Ensure all required resources are accessible for the patient
   - Check if resource mapping files exist in the correct location

3. **Schema Validation Errors**
   - Review validation results in metrics output
   - Check if resource structure matches expected schema

4. **Delta/Spark Configuration Issues**
   - Confirm Delta Lake JARs are correctly installed
   - Verify Spark session configuration

## Next Steps

After confirming the pipeline runs successfully with real data:

1. Update any remaining TO DO items from the checklist
2. Set up monitoring and metrics collection
3. Configure automated refreshes for authentication tokens 