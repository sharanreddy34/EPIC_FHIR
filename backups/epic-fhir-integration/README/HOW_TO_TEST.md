# How to Test Epic FHIR Integration with a Single Patient

This guide explains how to run a production-level test of the Epic FHIR integration pipeline with a single patient.

## Prerequisites

- Python 3.8 or higher
- Access to Epic FHIR API credentials
- RSA private key for authentication

## Quick Start (Automated Setup)

The easiest way to run a test is using the automated setup script, which handles environment variables, authentication, and running the test:

```bash
# Basic usage
python scripts/setup_test_env.py --patient-id PATIENT_ID

# With all options
python scripts/setup_test_env.py \
  --patient-id PATIENT_ID \
  --output-dir output/my_test \
  --debug \
  --keep-tests 5 \
  --min-disk-space 10.0 \
  --monitor-disk \
  --retry-count 3
```

## Manual Setup and Testing

If you prefer to set things up manually:

### 1. Set Environment Variables

Set the following environment variables:

```bash
export FHIR_OUTPUT_DIR="/path/to/output"
export EPIC_API_BASE_URL="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
export EPIC_CLIENT_ID="your-client-id"
export EPIC_PRIVATE_KEY_PATH="/path/to/private.key"
```

### 2. Generate Authentication Token

Generate an Epic authentication token:

```bash
python epic_fhir_integration/auth/custom_auth.py
# Or alternatively
python auth/setup_epic_auth.py
```

### 3. Run the Production Test

```bash
# Basic usage
python scripts/production_test.py --patient-id PATIENT_ID

# With all options
python scripts/production_test.py \
  --patient-id PATIENT_ID \
  --output-dir output/production_test \
  --debug \
  --keep-tests 5 \
  --min-disk-space 10.0 \
  --monitor-disk \
  --retry-count 3
```

## Command Line Options

| Option | Description | Default |
| ------ | ----------- | ------- |
| `--patient-id` | Patient ID to use for testing | *Required* |
| `--output-dir` | Output directory for test artifacts | `output/production_test` |
| `--debug` | Enable debug logging | `False` |
| `--keep-tests` | Number of test directories to keep | `5` |
| `--min-disk-space` | Minimum free disk space in GB | `10.0` |
| `--monitor-disk` | Enable disk space monitoring | `False` |
| `--retry-count` | Maximum number of retries for API calls | `3` |

## Test Process

The test goes through the following steps:

1. **Authentication with Epic FHIR API**
2. **Data Extraction**: Retrieves patient resources from Epic
3. **Bronze to Silver Transformation**: Flattens and normalizes FHIR resources
4. **Silver to Gold Transformation**: Creates summary datasets
5. **Validation**: Checks data quality, consistency, and completeness
6. **Reporting**: Generates a comprehensive test report

## Output Structure

Each test run creates a timestamped directory with the following structure:

```
TEST_YYYYMMDD_HHMMSS/
├── bronze/                # Raw FHIR resources
├── silver/                # Transformed FHIR resources
├── gold/                  # Aggregated summaries
├── logs/                  # Test logs
├── metrics/               # Performance metrics
├── reports/               # Test reports
├── schemas/               # Schema information
├── validation/            # Validation results
└── run_info.json          # Test metadata
```

## Validation

After the test is complete, you can run validation separately:

```bash
python -m epic_fhir_integration.cli.validate_run --run-dir /path/to/TEST_YYYYMMDD_HHMMSS
```

## Troubleshooting

### Common Issues

1. **Authentication Failure**
   - Verify your client ID and private key
   - Check that your key has been registered with Epic
   - Ensure your key is in the correct format

2. **Missing Resources**
   - Verify patient ID exists in Epic system
   - Check API permission scopes
   - Look for errors in logs

3. **Validation Failures**
   - Check validation results in `validation/results.json`
   - Examine metrics in `metrics/performance_metrics.parquet`
   - Review logs for specific errors

### Logs

Detailed logs are available in the test directory:

```bash
cat TEST_YYYYMMDD_HHMMSS/logs/test_*.log
```

## Additional Resources

- [Production Testing Guide](../docs/production_testing_guide.md)
- [High-Impact Improvements](../docs/high_impact_improvements.md)
- [Performance Optimization](../docs/performance_optimization.md) 