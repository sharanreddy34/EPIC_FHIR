# Epic FHIR Integration Troubleshooting Guide

This document provides guidance for diagnosing and resolving common issues when working with the Epic FHIR Integration pipeline.

## Common Issues

### Authentication Failures

#### Symptoms
- JWT token generation fails
- 401 Unauthorized responses from Epic API
- "Invalid client_assertion" errors

#### Solutions
1. Verify that your `EPIC_CLIENT_ID` and `EPIC_PRIVATE_KEY` secrets are correctly set in Foundry
2. Check that the private key is in the correct PEM format (begins with `-----BEGIN PRIVATE KEY-----`)
3. Ensure the `EPIC_BASE_URL` is correctly set and points to the right Epic environment
4. Check Epic system status if authentication suddenly stops working

### Transform Failures

#### Symptoms
- Transforms fail with "Output dataset not found" errors
- Spark jobs fail with memory errors
- Resource extraction times out

#### Solutions
1. Verify that all required datasets exist in Foundry with the correct paths
2. Check transform logs for specific error messages
3. For memory errors, increase the compute cluster size in `foundry.yml`
4. For timeouts, reduce batch sizes or page limits

### Missing Dependencies

#### Symptoms
- ImportError when running transforms
- "ClassNotFound" errors in Spark

#### Solutions
1. Verify all dependencies are correctly listed in `conda_recipe.yml`
2. Check that version constraints don't conflict
3. For Pathling errors, ensure the JAR is available via `spark.jars.packages`

## Debugging Techniques

### Checking Transform Logs

1. Navigate to the transform in Foundry
2. Click on the failed run
3. View the logs tab
4. Look for ERROR or WARNING level messages

### Testing Locally

Run transforms locally to debug issues:

```bash
# Install foundry-dev-tools
pip install foundry-dev-tools

# Run a transform locally
foundry-dev transform invoke \
  --entry-point src/epic_fhir_integration/bronze/patient_bronze_wrapper.py::compute
```

### Validating Epic API Access

Test API connectivity directly:

```bash
# Get a token
export TOKEN=$(epic-fhir-get-token)

# Test a simple request
curl -H "Authorization: Bearer $TOKEN" \
     "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient?_count=1"
```

## Getting Help

If you're still experiencing issues:

1. Check the `docs/` directory for more detailed documentation
2. Review the GitHub repository for recent updates or known issues
3. Contact the ATLAS team for assistance 