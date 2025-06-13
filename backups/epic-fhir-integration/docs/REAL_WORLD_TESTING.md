# Real-World Testing Guide

This guide explains how to set up and run tests against real Epic FHIR API data to validate the advanced FHIR tools implementation.

**For a detailed breakdown of outstanding tasks and a comprehensive testing strategy, please refer to the [Comprehensive Real-World Testing & Data Quality TODO List](./REAL_WORLD_TESTING_TODO.md).**

Patient ID for testing: `T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB` (and others for diversity as outlined in the TODO list)

## Overview

The real-world testing tools enable testing of:
- FHIRPath implementation
- Pathling analytics service
- FHIR-PYrate data science tools
- FHIR Shorthand & validation framework

These tools can be tested either directly against a live Epic FHIR API or using previously captured test data.

## Prerequisites

1.  **Epic FHIR API Access:**
    *   Client ID
    *   Private key for JWT signing
    *   Base URL for the FHIR API
    *   Appropriate scopes/permissions
    *   *Refer to `REAL_WORLD_TESTING_TODO.md` Section I for detailed configuration checks.*

2.  **Software Requirements:**
    *   Python 3.9+
    *   Java 11+ (for Pathling)
    *   Node.js 14+ & `fsh-sushi` globally installed (for FHIR Shorthand validation)
    *   *Verify all versions as per `REAL_WORLD_TESTING_TODO.md` Section I.*

## Setup Instructions

### 1. Configure Epic FHIR API Access

1.  Copy the template configuration file if it doesn't exist:
    ```bash
    cp config/live_epic_auth.json.template config/live_epic_auth.json
    ```

2.  Edit `config/live_epic_auth.json` with your Epic FHIR API credentials.
3.  Ensure your private key (e.g., `secrets/private_key.pem`) is correctly path-referenced and secured.

### 2. Prepare the Environment

1.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  Install the package with dependencies:
    ```bash
    pip install -e .
    ```
    *Resolve any dependency conflicts as noted in `REAL_WORLD_TESTING_TODO.md` Section I.*

## Running the Tests

Refer to `REAL_WORLD_TESTING_TODO.md` Section IX for enhanced test execution strategies.

### Option 1: Using the Test Script

The `run_real_world_tests.sh` script automates the testing process:

```bash
# Run tests with local test data (fetches data if needed)
./scripts/run_real_world_tests.sh --local

# Run tests directly against the Epic FHIR API (ensure configuration is correct)
./scripts/run_real_world_tests.sh --api

# Force refresh of test data from API
./scripts/run_real_world_tests.sh --local --force-fetch

# Run a specific test (example)
./scripts/run_real_world_tests.sh --local --test test_resource_coverage.py

# Run tests with verbose output
./scripts/run_real_world_tests.sh --local --verbose
```

### Option 2: Manual Testing

#### 1. Fetch Test Data

```bash
# Fetch and save test data (ensure script uses access_token for FHIRClient)
./scripts/fetch_test_data.py --config config/live_epic_auth.json --output test_data --deidentify
```
*Expand patient cohort and resource types fetched as per `REAL_WORLD_TESTING_TODO.md` Section II.*

#### 2. Run Individual Tests

```bash
# Example: Test FHIRPath implementation with local data
EPIC_TEST_DATA_PATH=test_data pytest epic_fhir_integration/tests/live/test_fhirpath_live.py -v

# Example: Test directly against API
RUN_LIVE_API_TESTS=true pytest epic_fhir_integration/tests/live/test_fhirpath_live.py -v
```

## Implemented Test Components

*(This section lists existing test files. Refer to `REAL_WORLD_TESTING_TODO.md` Sections VI & VII for planned enhancements to each component and E2E workflows.)*

### 1. FHIR Resource Coverage Tests (`test_resource_coverage.py`)
Tests ability to fetch and verify different FHIR resource types.

### 2. Authentication Tests (`test_auth.py`)
Tests the JWT authentication mechanism. *Ensure `FHIRClient` is used with `access_token` not `auth_header` in live tests.*

### 3. FHIRPath Implementation Tests (`test_fhirpath_live.py`)
Tests the FHIRPath adapter with real FHIR resources.

### 4. Pathling Analytics Tests (`test_pathling_live.py`)
Tests the Pathling analytics service.

### 5. Data Science Tests (`test_datascience_live.py`)
Tests the FHIR-PYrate data science tools (or mock equivalents).

### 6. Validation Tests (`test_validation_live.py`)
Tests the FHIR validation framework.

### 7. Dashboard Tests (`test_dashboard.py`)
Tests the quality and validation dashboard components.

### 8. End-to-End Tests (`test_e2e_live.py`)
Tests complete workflows combining multiple components.

## Data Quality Tier Definitions

*(These definitions are a summary. For detailed criteria and implementation actions, see `REAL_WORLD_TESTING_TODO.md` Section III and the proposed `DATA_QUALITY_STRATEGY.md`.)*

### Bronze Tier
-   Raw data as fetched, conforms to base FHIR R4, minimal transformations.
-   Validated against base FHIR structural requirements.

### Silver Tier
-   Bronze requirements + data cleansing, initial common extensions, improved coding.
-   Validated against an intermediary "silver" profile (to be defined).

### Gold Tier (LLM-Ready)
-   Silver requirements + full target profile conformance (e.g., US Core), comprehensive enrichment, linked data, LLM-optimized narratives, and de-identification as needed.
-   Validated against "gold" profiles.

## Enhanced Validation Testing Strategy

*(This is a summary. For detailed tasks, see `REAL_WORLD_TESTING_TODO.md` Section IV.)*

### Tier-Specific Profile Validation
-   **Bronze**: Structural validity.
-   **Silver**: Domain completeness, key extensions.
-   **Gold**: Full profile conformance (e.g., US Core).

### Cross-Resource Validation
-   Validate references, ensure consistency, test for orphaned resources.

### Terminology Validation
-   Validate coded values against ValueSets, check system URLs.

## Comprehensive Resource Coverage for Tiered Testing

*(See `REAL_WORLD_TESTING_TODO.md` Section II for a full list of target resources.)*
Expand testing to include all core resource types (Patient, Observation, Condition, Encounter, Procedure, MedicationRequest, AllergyIntolerance, Immunization, DiagnosticReport, DocumentReference). Ensure each progresses through Bronze, Silver, and Gold tiers with appropriate validation.

## Test Results and Reporting

*(Refer to `REAL_WORLD_TESTING_TODO.md` Section IX for reporting enhancements.)*

After running tests, comprehensive reports and dashboards can be generated:

```bash
# Generate a Markdown report (example)
./scripts/generate_test_report.py --input-dir test_output --log-dir logs --output test_report.md

# Generate interactive quality dashboard
epic-fhir-dashboard quality --report-path test_output/TEST_YYYYMMDD_HHMMSS/metrics/quality_report.json

# Generate interactive validation dashboard
epic-fhir-dashboard validation --results-path test_output/TEST_YYYYMMDD_HHMMSS/validation/results.json

# Generate both dashboards in static HTML mode (for sharing)
epic-fhir-dashboard combined --quality-report test_output/TEST_YYYYMMDD_HHMMSS/metrics/quality_report.json \
                           --validation-results test_output/TEST_YYYYMMDD_HHMMSS/validation/results.json \
                           --static-only
```

The report and dashboards should include environment details, component status, data quality tier metrics, validation summaries against profiles, and LLM-readiness checks.

## Troubleshooting

### Authentication Failures
-   Verify client ID, JWT issuer, private key, and API endpoint configurations.
-   Check token generation and exchange logic, ensuring `access_token` is used correctly with `FHIRClient`.
-   Ensure your API access and credentials haven't expired.

### Rate Limiting
-   The test script includes rate limiting; adjust delays if 429 errors occur.

### Pathling Java Requirements
-   `java -version` should show Java 11+ for Pathling tests.

### FSH Validation Requirements
-   `node -v` should show Node.js 14+.
-   SUSHI must be installed globally (`npm install -g fsh-sushi`).

## Data Privacy and Security
-   Fetched patient data is stored in `test_data` (or as configured).
-   Always use `--deidentify` or implement robust de-identification for data used outside secure Epic environments or with LLMs.
-   Adhere to all organizational data security and privacy policies.

## Log Files
Test logs are stored in the `logs` directory. Review for detailed results and errors.

## Standalone Testing

For environments where dependency conflicts prevent running the full advanced test suite, we provide a standalone test script that demonstrates core FHIR functionality without external dependencies:

```
python scripts/standalone_fhir_test.py [--output-dir DIR]
```

The standalone test script provides:

1. **FHIRPath Testing**: Demonstrates extraction of data from FHIR resources using FHIRPath expressions
2. **Basic FHIR Validation**: Validates FHIR resources against simplified rules
3. **Mock API Client**: Simulates interactions with a FHIR server

This script generates both JSON and Markdown reports with the results of all tests.

### Running the Standalone Test

```bash
# Run with default output directory (fhir_test_output)
python scripts/standalone_fhir_test.py

# Specify a custom output directory
python scripts/standalone_fhir_test.py --output-dir my_test_results
```

The test generates:
- `test_results.json`: Complete test results in JSON format
- `test_report.md`: Human-readable report with test results

This standalone test can be used to verify core functionality even in environments where the full test suite cannot run due to dependency conflicts.