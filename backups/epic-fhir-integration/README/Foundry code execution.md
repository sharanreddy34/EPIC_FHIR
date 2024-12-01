# Foundry Code Execution Guide for EPIC FHIR Integration

This document provides the exact commands needed to run the EPIC FHIR integration pipeline on Palantir Foundry.

## 1. Git Repository Setup

```bash
# Navigate to your Foundry code repository directory
cd /path/to/your/foundry/repo

# Set up remotes to connect GitHub code with Foundry
git remote add github https://github.com/gsiegel14/ATLAS-EPIC.git
git fetch github

# If you get "refusing to merge unrelated histories" error:
git pull github master --allow-unrelated-histories

# Commit merged changes
git add .
git commit -m "Merge GitHub FHIR code with Foundry repo"

# Push to Foundry
git push origin master
```

## 2. Authentication Setup

```bash
# Generate private key for JWT authentication (if not already done)
mkdir -p auth/keys
openssl genrsa -out auth/keys/rsa_private.pem 2048
openssl rsa -in auth/keys/rsa_private.pem -pubout -out auth/keys/rsa_public.pem

# Set environment variables in Foundry transformation
# Add these to your Foundry transformation settings:
EPIC_CLIENT_ID=your_epic_client_id
EPIC_ENVIRONMENT=non-production
EPIC_PRIVATE_KEY_PATH=auth/keys/rsa_private.pem

# Create a token manually (execute in Foundry transformation)
python -c '
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
'
```

## 3. Dataset Structure Creation

In Foundry, create the following datasets:

```
config/api_config
config/resources_config
secrets/epic_token
control/fhir_cursors
control/workflow_status
bronze/fhir_raw
```

For silver layer, create:
```
silver/fhir_normalized/patient
silver/fhir_normalized/encounter
silver/fhir_normalized/observation
silver/fhir_normalized/condition
silver/fhir_normalized/medicationrequest
silver/fhir_normalized/procedure
silver/fhir_normalized/immunization
silver/fhir_normalized/allergyintolerance
silver/fhir_normalized/practitioner
```

For gold layer, create:
```
gold/patient_summary
gold/encounter_summary
gold/medication_summary
```

## 4. Configuration Files Upload

Create and upload the following configuration files:

**config/api_config.yaml**:
```yaml
base_url: https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
token_url: https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
timeout: 60
verify_ssl: true
environment: non-production
client_id: ${EPIC_CLIENT_ID}
```

**config/resources_config.yaml**:
```yaml
resources:
  Patient:
    search_params:
      _id: ${patient_id}
    page_size: 100
  Encounter:
    search_params:
      patient: ${patient_id}
    page_size: 100
  Observation:
    search_params:
      patient: ${patient_id}
    page_size: 100
  Condition:
    search_params:
      patient: ${patient_id}
    page_size: 100
  MedicationRequest:
    search_params:
      patient: ${patient_id}
    page_size: 100
  Procedure:
    search_params:
      patient: ${patient_id}
    page_size: 100
  Immunization:
    search_params:
      patient: ${patient_id}
    page_size: 100
  AllergyIntolerance:
    search_params:
      patient: ${patient_id}
    page_size: 100
```

## 5. Complete FHIR Pipeline Execution

Create a Foundry transformation with the following code:

```python
#!/usr/bin/env python3
"""
Complete FHIR Pipeline Execution Script for Foundry
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fhir_pipeline")

# Patient ID to extract
PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

# Step 1: Generate token if needed
def generate_token(client_id, private_key_path, token_output_path):
    """Generate JWT token for Epic FHIR API"""
    import jwt
    
    logger.info(f"Generating JWT token using client ID: {client_id}")
    
    with open(private_key_path, "r") as f:
        private_key = f.read()
    
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
    
    token_data = {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "system/*.*",
        "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiration))
    }
    
    with open(token_output_path, "w") as f:
        json.dump(token_data, f, indent=2)
    
    logger.info(f"Token created and saved to {token_output_path}. Expires at {token_data['expires_at']}")
    return token_data

# Step 2: Extract patient resources
def extract_patient_resources():
    """Extract patient resources from FHIR API"""
    logger.info(f"Extracting data for patient: {PATIENT_ID}")
    
    # Import the necessary modules
    from fhir_pipeline.config import load_settings
    from fhir_pipeline.cli import extract_patient_data
    
    # Load settings
    settings = load_settings(debug=True)
    
    # Extract resources
    resource_types = ["Patient", "Encounter", "Observation", "Condition", 
                     "MedicationRequest", "Procedure", "Immunization",
                     "AllergyIntolerance"]
    
    result = extract_patient_data(PATIENT_ID, resource_types, settings)
    
    if result.get("success", False):
        logger.info(f"Successfully extracted {result.get('resources_extracted', 0)} resources")
    else:
        logger.error(f"Extraction failed: {result.get('error', 'Unknown error')}")
    
    return result

# Step 3: Transform resources to silver layer
def transform_resources():
    """Transform extracted resources to normalized format"""
    logger.info("Transforming resources to silver layer")
    
    resource_types = ["patient", "encounter", "observation", "condition", 
                     "medicationrequest", "procedure", "immunization",
                     "allergyintolerance"]
    
    results = {}
    
    for resource_type in resource_types:
        logger.info(f"Normalizing {resource_type} resources")
        
        try:
            # Import the transformation module dynamically
            module_name = f"fhir_pipeline.transforms.normalize_{resource_type}"
            transform_module = __import__(module_name, fromlist=["transform_to_silver"])
            transform_func = getattr(transform_module, "transform_to_silver")
            
            # Execute transformation
            result = transform_func()
            results[resource_type] = result
            
            logger.info(f"Successfully transformed {resource_type} resources")
        except Exception as e:
            logger.error(f"Error transforming {resource_type}: {str(e)}")
            results[resource_type] = {"success": False, "error": str(e)}
    
    return results

# Step 4: Create gold layer datasets
def create_gold_datasets():
    """Create gold layer datasets from silver data"""
    logger.info("Creating gold layer datasets")
    
    gold_transformations = [
        "create_patient_summary", 
        "create_encounter_summary", 
        "create_medication_summary"
    ]
    
    results = {}
    
    for transform_name in gold_transformations:
        logger.info(f"Running gold transformation: {transform_name}")
        
        try:
            # Import the transformation module dynamically
            module_name = f"fhir_pipeline.transforms.{transform_name}"
            transform_module = __import__(module_name, fromlist=["transform_to_gold"])
            transform_func = getattr(transform_module, "transform_to_gold")
            
            # Execute transformation
            result = transform_func()
            results[transform_name] = result
            
            logger.info(f"Successfully executed {transform_name}")
        except Exception as e:
            logger.error(f"Error in {transform_name}: {str(e)}")
            results[transform_name] = {"success": False, "error": str(e)}
    
    return results

# Main execution flow
def main():
    start_time = time.time()
    logger.info("Starting FHIR pipeline execution")
    
    # Get credentials from environment
    client_id = os.environ.get("EPIC_CLIENT_ID")
    private_key_path = os.environ.get("EPIC_PRIVATE_KEY_PATH", "auth/keys/rsa_private.pem")
    
    if not client_id:
        logger.error("EPIC_CLIENT_ID environment variable not set")
        return 1
    
    # Step 1: Generate token
    token_data = generate_token(client_id, private_key_path, "epic_token.json")
    
    # Step 2: Extract resources
    extraction_result = extract_patient_resources()
    
    # Step 3: Transform to silver layer
    if extraction_result.get("success", False):
        transform_results = transform_resources()
    else:
        logger.error("Skipping transformation due to extraction failure")
        transform_results = {"skipped": True}
    
    # Step 4: Create gold datasets
    gold_results = create_gold_datasets()
    
    # Summarize execution
    execution_time = time.time() - start_time
    logger.info(f"Pipeline execution completed in {execution_time:.2f} seconds")
    
    pipeline_result = {
        "patient_id": PATIENT_ID,
        "execution_time": execution_time,
        "extraction": extraction_result,
        "transformation": transform_results,
        "gold": gold_results
    }
    
    # Save result summary
    with open("pipeline_execution_summary.json", "w") as f:
        json.dump(pipeline_result, f, indent=2)
    
    logger.info("Pipeline execution summary saved to pipeline_execution_summary.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## 6. Running Individual Steps

If you prefer to run steps individually:

### Extract Patient Data:

```python
import os
import logging
from fhir_pipeline.config import load_settings
from fhir_pipeline.cli import extract_patient_data

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Load settings
settings = load_settings(debug=True)

# Extract Patient Data
patient_id = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
resource_types = ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest"]

result = extract_patient_data(
    patient_id,
    resource_types,
    settings
)

print(f"Extraction result: {result}")
```

### Transform Patient Data:

```python
import sys
import logging
from fhir_pipeline.transforms.normalize_patient import transform_to_silver

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Run transformation
result = transform_to_silver()
print(f"Transformation result: {result}")
```

### Create Gold Dataset:

```python
import sys
import logging
from fhir_pipeline.transforms.create_patient_summary import transform_to_gold

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Run gold transformation
result = transform_to_gold()
print(f"Gold transformation result: {result}")
```

## 7. Monitoring Execution

Add this code to your transformation for progress tracking:

```python
def track_progress(step, total, description):
    """Track progress of a step"""
    percentage = int((step / total) * 100)
    logger.info(f"Progress: {percentage}% - {description} ({step}/{total})")
    
    # For Foundry UI progress updates
    if hasattr(sys.stdout, "update_progress"):
        sys.stdout.update_progress(percentage / 100)
```

Use this function in your pipeline steps to show progress in the Foundry UI.

## 8. Required Dependencies

Ensure these dependencies are available in your Foundry environment:

```
requests==2.31.0
aiohttp==3.9.1
PyYAML==6.0.1
pydantic==2.4.2
backoff==2.2.1
python-json-logger==2.0.7
PyJWT
cryptography
```

## 9. Troubleshooting Common Errors

### JWT Authentication Failure

If you see "401 Unauthorized" errors:

```python
# Verify your JWT token is valid
import jwt
import time

with open("epic_token.json", "r") as f:
    token_data = json.load(f)

token = token_data["access_token"]
decoded = jwt.decode(token, options={"verify_signature": False})

now = int(time.time())
if decoded["exp"] < now:
    print(f"Token expired at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(decoded['exp']))}")
    print(f"Current time is {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}")
    print("Token has expired - regenerate it")
else:
    print(f"Token is valid until {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(decoded['exp']))}")
``` 