# Epic FHIR Integration

Tools for integrating with Epic's FHIR API, including authentication, data fetching, and processing functions.

## Setup

1. Clone this repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .
   ```
4. Copy the private key to the secrets directory:
   ```bash
   mkdir -p epic-fhir-integration/secrets
   cp key.md epic-fhir-integration/secrets/rsa_private.pem
   ```
5. Copy the configuration template:
   ```bash
   cp epic-fhir-integration/config/env.example .env
   ```
6. Edit `.env` with your specific settings if needed

## Authentication Setup

The package includes a robust authentication system for the Epic FHIR API:

1. Configure your authentication settings in `~/.config/epic_fhir/api_config.yaml`:
   ```yaml
   auth:
     client_id: "your-client-id"
     jwt_issuer: "your-client-id"  # Typically the same as client_id
     epic_base_url: "https://fhir.epic.com/interconnect-fhir-oauth"
     private_key_path: "/path/to/your/private_key.pem"
     token_cache_path: "/path/to/store/epic_token.json"
   fhir:
     base_url: "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
     timeout: 30
     retry_attempts: 3
   ```

2. Store your private key in the location specified by `private_key_path`. The system will automatically find it in these locations (in order):
   - The path specified in `private_key_path`
   - `~/ATLAS Palantir/epic_private_key.pem`
   - `~/ATLAS Palantir/key.md`
   - `epic-fhir-integration/secrets/epic_private_key.pem`
   - `epic-fhir-integration/secrets/rsa_private.pem`

3. Test your authentication setup using the provided test script:
   ```bash
   python epic-fhir-integration/scripts/test_epic_auth.py
   ```

The authentication system provides these features:
- Automatic token caching to prevent unnecessary token requests
- Token refresh when approaching expiration
- Retry with exponential backoff for reliability
- Fallback strategies for handling errors
- Clear logging for troubleshooting

## Testing the Configuration

Run the test script to verify that your authentication and API connection is working:

```bash
python epic-fhir-integration/test_epic_connection.py
```

The script will:
1. Test obtaining an access token
2. Test connecting to the FHIR API metadata endpoint
3. Test accessing a specific patient

## Fetching Patient Data

Use the data fetching script to retrieve patient data:

```bash
python epic-fhir-integration/scripts/fetch_patient_data.py --output test_data --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB
```

Optional arguments:
- `--config CONFIG`: Path to Epic FHIR API configuration file (default: config/live_epic_auth.json)
- `--output OUTPUT`: Directory to save fetched FHIR resources (default: test_data)
- `--patient-id PATIENT_ID`: Patient ID to fetch
- `--deidentify`: De-identify patient data before saving
- `--verbose`: Enable verbose logging
- `--skip-existing`: Skip resources that already exist in the output directory

## Advanced FHIR Tools

The package includes several advanced tools for working with FHIR data:

### Running the End-to-End Test Script

The advanced FHIR tools end-to-end test script demonstrates the full capabilities of the integration:

```bash
python epic-fhir-integration/scripts/advanced_fhir_tools_e2e_test.py [--patient-id ID] [--output-dir DIR] [--debug] [--mock] [--tier TIER]
```

This script showcases:
1. Authentication with JWT
2. Patient data extraction
3. FHIRPath implementation
4. Pathling analytics
5. FHIR-PYrate data science
6. FHIR validation
7. Data quality assessment (Bronze, Silver, Gold tiers)
8. Dashboard generation

### Great Expectations Integration

This package integrates with the Great Expectations data validation framework for FHIR resources:

1. Initialize Great Expectations in your project:
   ```bash
   python epic-fhir-integration/scripts/create_gx_expectations.py [--project-dir DIR] [--overwrite]
   ```
   This will create expectation suites for different resource types and data tiers.

2. Use the `GreatExpectationsValidator` to validate resources against these expectations:
   ```python
   from epic_fhir_integration.metrics.great_expectations_validator import GreatExpectationsValidator
   
   validator = GreatExpectationsValidator()
   result = validator.validate_resource(resource, "patient_bronze_expectations")
   ```

### FHIRPath Adapter

The `FHIRPathAdapter` provides a robust implementation for evaluating FHIRPath expressions against FHIR resources:

```python
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Extract a patient's name
patient_name = FHIRPathAdapter.extract_first(patient, "name.where(use='official').given.first()")

# Check if a condition is active
is_active = FHIRPathAdapter.exists(condition, "clinicalStatus.coding.where(code='active').exists()")

# Get multiple values
observation_values = FHIRPathAdapter.extract(observations, "valueQuantity.value")
```

### Pathling Analytics Service

For advanced analytics on FHIR data, the package includes a Pathling service integration:

```python
from epic_fhir_integration.analytics.pathling_service import PathlingService

# Start the service (requires Docker or Java 11+)
service = PathlingService()
service.start()

# Import FHIR data
service.import_data("path/to/fhir/bundles")

# Run analytics queries
patient_count = service.aggregate("Patient", "count()")
bp_readings = service.aggregate("Observation", "count()", 
                               grouping="code.coding.where(system='http://loinc.org').code")

# Extract datasets
dataset = service.extract_dataset("Patient", ["id", "gender", "birthDate"])

# Stop the service when done
service.stop()
```

## Authentication Details

The authentication module (`epic_fhir_integration/auth/get_token.py`) handles obtaining and refreshing access tokens using JWT authentication. It will:

1. Look for an existing cached token
2. If no valid token exists, generate a new JWT token
3. Exchange the JWT for an access token
4. Cache the token for future use

You can use the module directly:

```python
from epic_fhir_integration.auth.get_token import get_access_token, get_auth_headers

# Get a token dictionary with access_token, token_type, expires_in, etc.
token_data = get_access_token(verbose=True)

# Or get authorization headers ready to use in requests
headers = get_auth_headers()
response = requests.get("https://fhir.epic.com/api/FHIR/R4/Patient/123", headers=headers)
```

## File Structure

- `epic-fhir-integration/`: Main package directory
  - `analytics/`: FHIR analytics tools including Pathling integration
  - `auth/`: Authentication modules
  - `config/`: Configuration files
  - `datascience/`: FHIR data science tools
  - `metrics/`: Data quality and validation metrics
  - `scripts/`: Utility scripts
  - `secrets/`: Secret keys (not tracked in version control)
  - `utils/`: Utility functions including FHIRPath implementation
  - `validation/`: FHIR validation tools
- `test_data/`: Default location for fetched FHIR resources
- `great_expectations/`: Great Expectations configuration and expectations

## Configuration

Configuration can be provided through:
1. Environment variables (defined in `.env` file)
2. JSON configuration file (`config/live_epic_auth.json`)
3. Command-line arguments to scripts

## Prerequisites

- Python 3.8 or higher
- For Pathling analytics: Docker or Java 11+
- For Great Expectations: `great_expectations` package (`pip install great_expectations`)
- For FHIRPath: `fhirpathpy` package (`pip install fhirpathpy`)

## Known Issues and Status

### Great Expectations

Great Expectations is now correctly configured to find expectation suites in the proper directory. If you encounter issues:

1. Run the `create_gx_expectations.py` script to generate expectation suites
2. Check the `great_expectations/expectations/` directory for the generated files
3. Use the `--project-dir` argument to specify your project root if needed

### FHIRPath Evaluation

The FHIRPath adapter has been enhanced to properly handle complex expressions like `name.where(use='official').given.first()`. Features include:

- Better error handling and logging
- Improved mock implementation for testing
- Support for both dictionary and model-based FHIR resources

### Pathling Integration

The Pathling service now has:

- Improved Docker detection and error reporting
- Automatic fallback to mock mode when Docker is unavailable
- Better health checking and startup handling
- Enhanced error messages for common Docker issues

If you encounter Docker-related issues:
1. Ensure Docker is installed and running
2. Check if the Docker daemon is accessible to your user
3. Verify you have permissions to use Docker
4. If Docker is unavailable, the service will automatically fall back to mock mode

## Troubleshooting

### Authentication Issues

- Check that your private key is correctly formatted and accessible
- Verify your client ID is correct
- Make sure the JWT issuer matches your client ID
- Remember that key propagation can take up to 60 minutes in sandbox environments

### API Connection Issues

- Check network connectivity to the Epic FHIR endpoint
- Verify the base URL is correct
- Ensure your client has the appropriate scopes

### Data Fetching Issues

- Confirm the patient ID exists and is accessible with your credentials
- Check for rate limiting and adjust request patterns if needed

### Advanced Tools Issues

- **Great Expectations**: If quality metrics show 0%, ensure expectation suites exist in the correct location
- **FHIRPath**: For complex path evaluations, ensure the resource has the expected structure
- **Pathling**: For Docker issues, check Docker daemon status with `docker info` 