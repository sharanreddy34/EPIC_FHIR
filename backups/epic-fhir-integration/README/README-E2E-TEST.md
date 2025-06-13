# FHIR Pipeline End-to-End Test

This document explains how to use the end-to-end test script for the EPIC FHIR integration pipeline.

## Overview

The `e2e_test_fhir_pipeline.py` script provides an end-to-end test of the FHIR data pipeline with a specific patient ID. It connects to the EPIC FHIR API, extracts data, transforms it to the appropriate format, and provides a summary of the results.

## Requirements

- Python 3.8+
- Required Python packages (installed with the main project)
  - `PyJWT` for JWT token generation
  - `requests` for API calls
- Java (for Spark functionality, but the script will fall back to mock mode if Java is not available)
- EPIC FHIR API credentials (optional - the script will use mock data if real credentials are not available)

## Usage

Run the script from the command line:

```bash
python e2e_test_fhir_pipeline.py [--debug] [--output-dir OUTPUT_DIR]
```

### Options

- `--debug`: Enable debug logging for more detailed output
- `--output-dir`: Specify an output directory for the test results (default: `./e2e_test_output`)

## Authentication

The script uses JWT-based authentication to obtain access tokens from the EPIC FHIR API.

### Improved Authentication Approach

The script now implements a proven authentication approach that directly creates properly formatted JWT tokens and exchanges them for access tokens. This approach:

1. **Directly Creates JWTs**: Uses PyJWT to create tokens with the exact headers and claims required by Epic
2. **Eliminates Middleware**: Removes dependency on additional JWT client classes
3. **Handles Access Tokens**: Properly manages access tokens, including saving them for later use
4. **Provides Better Error Handling**: Includes detailed error logging for authentication issues
5. **Has Fallback Mechanisms**: Can fall back to using a cached token if generation fails

This implementation has been tested and confirmed to work with the EPIC FHIR API, making the authentication process more reliable and robust than the previous JWT client implementation.

### JWKS Requirements

Epic requires that your public key be available at a JWKS (JSON Web Key Set) URL. For this project, we use:
```
https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json
```

### Environment Variables

To use real API credentials, set the following environment variables:

```bash
export EPIC_CLIENT_ID="your-client-id"
export EPIC_PRIVATE_KEY="your-private-key"
```

**Important Notes on Authentication:**
- The private key must be a valid RSA key in PEM format
- The JWT is signed using the RS384 algorithm (required by EPIC)
- The script includes special headers required by Epic:
  - `alg`: "RS384"
  - `kid`: "atlas-key-001" 
  - `jku`: The JWKS URL
  - `typ`: "JWT"
- If direct token generation fails, the script will try to use a pre-generated token from `epic_token.json` if available

### Manual Token Generation

You can pre-generate a token by running:

```bash
python ../auth/setup_epic_auth.py
```

This will:
1. Create a JWT with the required format
2. Exchange it for an access token
3. Save the token to `epic_token.json`

## Test Patient

The script is configured to use the following test patient ID:

```
T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB@fhir_pipeline
```

## Output

The script creates the following directory structure in the output directory:

- **bronze/fhir_raw**: Raw FHIR resources extracted from the API
- **silver/fhir_normalized**: Normalized FHIR resources
- **gold**: Gold layer datasets derived from the silver layer

At the end of the test, a summary of the results is displayed, showing the count of resources at each layer.

## Modes of Operation

The script can operate in two modes:

1. **Full Mode**: Uses Spark and real API credentials
2. **Mock Mode**: Uses mock data and transformation when either Spark or API credentials are not available

The script automatically determines which mode to use based on available resources.

## Error Handling

The script includes comprehensive error handling:

- If Spark is not available, it will fall back to using direct API calls and mock transformation
- If API credentials are not available, it will use mock data
- If JWT authentication fails, it attempts to use a pre-generated token from epic_token.json
- Any errors during extraction or transformation are logged and handled

## Logging

Logs are printed to the console. Use the `--debug` flag for more detailed logs.

## Example Output

```
2025-05-19 17:53:50,680 - __main__ - INFO - Bronze directory contents:
...
2025-05-19 17:53:50,680 - __main__ - INFO - [dir] Patient
...
2025-05-19 17:53:50,680 - __main__ - INFO - Silver directory contents:
...

================================================================================
SUMMARY OF FHIR PIPELINE RESULTS FOR PATIENT T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB
================================================================================

Bronze Layer: 16 files
  - Encounter: 2 files
  - Immunization: 2 files
  ...

Processing Complete!
================================================================================
```

## Troubleshooting

### Common Authentication Issues

1. **Invalid Client Error**:
   - Ensure client ID is correct
   - Verify that the JWKS URL is publicly accessible
   - Remember that key propagation can take up to 60 minutes for sandbox or 12 hours for production

2. **Invalid Token Error**:
   - JWT might be expired (they are valid for only 5 minutes)
   - Headers and claims must match exactly what Epic expects
   - The RS384 algorithm must be used 