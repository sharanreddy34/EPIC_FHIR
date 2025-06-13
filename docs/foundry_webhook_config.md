# Epic FHIR API Integration for Foundry Webhooks

This document explains how to configure a Foundry webhook to connect to Epic's FHIR API using the JWT authentication method.

## Prerequisites

1. Epic FHIR API credentials (client IDs for Production and Non-Production)
2. RSA private key corresponding to the public key registered in Epic
3. Python environment with `PyJWT` and `requests` packages

## Setup Steps

### 1. Install Required Python Packages

Add these packages to your Foundry environment:
- `PyJWT[crypto]` (for JWT generation with RSA support)
- `requests` (for API calls)

### 2. Save Your Private Key

Run `setup_epic_auth.py` to save your private key securely:

```bash
python setup_epic_auth.py
```

This will prompt you to paste your private key and choose between Production and Non-Production environments.

### 3. Configure Foundry Webhook

For a simple webhook, use this configuration:

1. **Python Transformation**:
   
   Create a Python script with these imports and helper functions:

   ```python
   from foundry_epic_auth import get_epic_auth_header, PRIVATE_KEY_FILE
   import requests
   
   # Read private key
   with open(PRIVATE_KEY_FILE, "r") as f:
       private_key = f.read()
   
   # Generate authorization header with fresh token
   auth_header = get_epic_auth_header(private_key, use_prod=False)
   
   # Configure request
   headers = {
       "Authorization": auth_header,
       "Accept": "application/json",
       "Content-Type": "application/json"
   }
   
   # Make API request
   response = requests.get(
       "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/{patientId}",
       headers=headers
   )
   
   # Process response
   if response.ok:
       patient_data = response.json()
       # Process patient data...
   ```

2. **For Production Webhooks**:
   
   Modify the code to use production credentials:
   
   ```python
   # Use production environment
   auth_header = get_epic_auth_header(private_key, use_prod=True)
   ```

### 4. Token Handling in Foundry

The `foundry_epic_auth.py` module handles token lifecycle automatically:

1. Checks if a valid token exists in the cache file
2. If valid, uses the cached token
3. If expired or missing, generates a new token by:
   - Creating a JWT signed with your private key
   - Requesting a new token from Epic's OAuth endpoint
   - Caching the new token for future use

## Troubleshooting

If you receive a `401 Unauthorized` error:

1. **Invalid Token**: The access token has expired or is malformed.
   - Solution: The auth module should handle token refresh automatically. Verify the token format.

2. **Invalid JWT**: Check if your JWT is properly formatted:
   - Verify your private key matches the public key registered with Epic
   - Check that all JWT claims are correct (iss, sub, aud, etc.)
   - Make sure the algorithm is set to RS384

3. **Key Propagation Delay**: New keys require time to propagate in Epic's systems:
   - Sandbox: Wait up to 60 minutes
   - Production: Wait up to 12 hours

4. **Client ID Issues**: Ensure you're using the correct client ID for the environment:
   - Non-Production: `2fe57a4f-cf1f-47cf-945f-230e0770da12`
   - Production: `3d6d8f7d-9bea-4fe2-b44d-81c7fec75ee5`

For persistent issues, run the monitoring script to check when authentication succeeds:

```bash
python monitor_epic_auth.py
```

## Security Best Practices

1. **Protect your private key**:
   - In production, use Foundry's secrets management
   - Never commit private keys to version control

2. **Token handling**:
   - The access token is cached in `epic_token.json`
   - This file should be protected and not shared

3. **Refresh tokens when needed**:
   - The auth module handles token expiration automatically
   - Tokens typically last 3600 seconds (1 hour) 