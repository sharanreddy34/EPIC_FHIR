# FHIR Pipeline: Complete Step-by-Step Guide

This guide provides the exact commands to set up and run the entire FHIR data pipeline from start to finish.

## 1. Environment Setup

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required dependencies
pip install requests==2.31.0 aiohttp==3.9.1 PyYAML==6.0.1 pydantic==2.4.2 backoff==2.2.1 python-json-logger==2.0.7 PyJWT cryptography

# Install the package in development mode
pip install -e .
```

## 2. Authentication Setup

```bash
# Create directory for keys
mkdir -p auth/keys

# Generate RSA key pair for JWT authentication
openssl genrsa -out auth/keys/rsa_private.pem 2048
openssl rsa -in auth/keys/rsa_private.pem -pubout -out auth/keys/rsa_public.pem

# Set environment variables
export EPIC_CLIENT_ID="your_epic_client_id"
export EPIC_ENVIRONMENT="non-production"
export EPIC_PRIVATE_KEY_PATH="auth/keys/rsa_private.pem"

# Create JWT token
python create_private_key.py
```

## 3. Configuration Setup

```bash
# Create config directory
mkdir -p config

# Create API configuration file
cat > config/api_config.yaml << EOL
base_url: https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
token_url: https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
timeout: 60
verify_ssl: true
environment: non-production
client_id: ${EPIC_CLIENT_ID}
EOL

# Create resources configuration file
cat > config/resources_config.yaml << EOL
resources:
  Patient:
    search_params:
      _id: \${patient_id}
    page_size: 100
  Encounter:
    search_params:
      patient: \${patient_id}
    page_size: 100
  Observation:
    search_params:
      patient: \${patient_id}
    page_size: 100
  Condition:
    search_params:
      patient: \${patient_id}
    page_size: 100
  MedicationRequest:
    search_params:
      patient: \${patient_id}
    page_size: 100
  Procedure:
    search_params:
      patient: \${patient_id}
    page_size: 100
  Immunization:
    search_params:
      patient: \${patient_id}
    page_size: 100
  AllergyIntolerance:
    search_params:
      patient: \${patient_id}
    page_size: 100
EOL
```

## 4. Directory Structure Setup

```bash
# Create main output directories
mkdir -p patient_data
mkdir -p local_output/bronze/fhir_raw
mkdir -p local_output/silver/fhir_normalized
mkdir -p local_output/gold
mkdir -p local_output/control
mkdir -p local_output/metrics

# Create silver layer subdirectories
mkdir -p local_output/silver/fhir_normalized/patient
mkdir -p local_output/silver/fhir_normalized/encounter
mkdir -p local_output/silver/fhir_normalized/observation
mkdir -p local_output/silver/fhir_normalized/condition
mkdir -p local_output/silver/fhir_normalized/medicationrequest
mkdir -p local_output/silver/fhir_normalized/procedure
mkdir -p local_output/silver/fhir_normalized/immunization
mkdir -p local_output/silver/fhir_normalized/allergyintolerance
mkdir -p local_output/silver/fhir_normalized/practitioner

# Create gold layer subdirectories
mkdir -p local_output/gold/patient_summary
mkdir -p local_output/gold/encounter_summary
mkdir -p local_output/gold/medication_summary
```

## 5. Authentication Token Generation

```bash
# Run JWT authentication token generation
./setup_epic_jwt.sh

# Or manually generate token
python - << EOL
import os
import json
import time
import jwt

def create_token():
    client_id = os.environ.get("EPIC_CLIENT_ID")
    private_key_path = os.environ.get("EPIC_PRIVATE_KEY_PATH", "auth/keys/rsa_private.pem")
    
    with open(private_key_path, "r") as f:
        private_key = f.read()
    
    # Create the JWT token
    now = int(time.time())
    expiration = now + 3600  # 1 hour expiration
    
    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
        "jti": f"jwt-{now}",
        "exp": expiration,
        "iat": now
    }
    
    token = jwt.encode(payload, private_key, algorithm="RS384")
    
    # Save token to file
    token_data = {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "system/*.*",
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiration))
    }
    
    with open("epic_token.json", "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"Token created and saved to epic_token.json. Expires at {token_data['expires_at']}")

create_token()
EOL
```

## 6. Running the Bronze Layer (Data Extraction)

```bash
# Extract data for a specific patient
python -m fhir_pipeline.cli extract \
  --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB \
  --resources "Patient,Encounter,Observation,Condition,MedicationRequest,Procedure,Immunization,AllergyIntolerance" \
  --debug

# Or use the script with predefined patient
./run_with_patient.sh

# Alternatively, use the test extraction script
python extract_test_patient.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug
```

## 7. Running the Silver Layer (Data Normalization)

```bash
# Run each transformation script for the normalized resources

# Patient normalization
python - << EOL
import logging
from fhir_pipeline.transforms.normalize_patient import transform_to_silver

logging.basicConfig(level=logging.DEBUG)
result = transform_to_silver()
print(f"Patient transformation result: {result}")
EOL

# Encounter normalization
python - << EOL
import logging
from fhir_pipeline.transforms.normalize_encounter import transform_to_silver

logging.basicConfig(level=logging.DEBUG)
result = transform_to_silver()
print(f"Encounter transformation result: {result}")
EOL

# Observation normalization
python - << EOL
import logging
from fhir_pipeline.transforms.normalize_observation import transform_to_silver

logging.basicConfig(level=logging.DEBUG)
result = transform_to_silver()
print(f"Observation transformation result: {result}")
EOL

# Condition normalization
python - << EOL
import logging
from fhir_pipeline.transforms.normalize_condition import transform_to_silver

logging.basicConfig(level=logging.DEBUG)
result = transform_to_silver()
print(f"Condition transformation result: {result}")
EOL

# Medication request normalization
python - << EOL
import logging
from fhir_pipeline.transforms.normalize_medicationrequest import transform_to_silver

logging.basicConfig(level=logging.DEBUG)
result = transform_to_silver()
print(f"MedicationRequest transformation result: {result}")
EOL
```

## 8. Running the Gold Layer (Insights Generation)

```bash
# Patient summary
python - << EOL
import logging
from fhir_pipeline.transforms.create_patient_summary import transform_to_gold

logging.basicConfig(level=logging.DEBUG)
result = transform_to_gold()
print(f"Patient summary result: {result}")
EOL

# Encounter summary
python - << EOL
import logging
from fhir_pipeline.transforms.create_encounter_summary import transform_to_gold

logging.basicConfig(level=logging.DEBUG)
result = transform_to_gold()
print(f"Encounter summary result: {result}")
EOL

# Medication summary
python - << EOL
import logging
from fhir_pipeline.transforms.create_medication_summary import transform_to_gold

logging.basicConfig(level=logging.DEBUG)
result = transform_to_gold()
print(f"Medication summary result: {result}")
EOL
```

## 9. Running the Complete Pipeline

```bash
# Run complete pipeline with local execution
python run_local_fhir_pipeline.py \
  --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB \
  --steps "extract,transform,gold" \
  --debug
```

## 10. Verifying Results and Troubleshooting

```bash
# Check extraction summary
cat patient_data/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB/extraction_summary.json

# Count extracted resources
find patient_data/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB -type f | grep -v extraction_summary.json | wc -l

# Verify token validity
python - << EOL
import json
import time
import jwt

with open("epic_token.json", "r") as f:
    token_data = json.load(f)

token = token_data.get("access_token")
if not token:
    print("No token found")
    exit(1)

decoded = jwt.decode(token, options={"verify_signature": False})
now = int(time.time())

if decoded["exp"] < now:
    print(f"Token expired at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(decoded['exp']))}")
    print(f"Current time is {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}")
    print("Token has expired - regenerate it")
else:
    print(f"Token is valid until {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(decoded['exp']))}")
    print(f"Token will expire in {decoded['exp'] - now} seconds")
EOL

# Check debug logs
cat debug_pipeline.log | tail -50

# Test API connectivity
python - << EOL
import requests
import json

with open("epic_token.json", "r") as f:
    token_data = json.load(f)

token = token_data.get("access_token")
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

try:
    response = requests.get(
        "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/metadata",
        headers=headers,
        timeout=10
    )
    print(f"Connection test result: {response.status_code}")
    if response.status_code == 200:
        print("Connection successful")
    else:
        print(f"Connection failed: {response.text}")
except Exception as e:
    print(f"Connection error: {str(e)}")
EOL
``` 