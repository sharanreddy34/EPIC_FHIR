# FHIR Pipeline Testing Framework

This directory contains the comprehensive testing framework for the FHIR pipeline project. The tests are organized into different categories to facilitate targeted testing and validation.

## Test Structure

- **Unit Tests** (`tests/unit/`): Tests for individual components and functions
- **Integration Tests** (`tests/integration/`): Tests for interactions between components
- **Performance Tests** (`tests/perf/`): Tests for performance and load handling
- **Live Tests** (`tests/live/`): Tests that run against live endpoints (requires credentials)
- **Fixtures** (`tests/fixtures/`): Common test fixtures and utilities
- **Data** (`tests/data/`): Sample test data used by tests

## Running Tests

### Using Test Scripts

The project includes convenient scripts for running tests:

#### Unix/Linux/macOS

```bash
# Run all tests
./run_tests.sh

# Run specific test type
./run_tests.sh -t unit
./run_tests.sh -t integration
./run_tests.sh -t auth

# Run with coverage
./run_tests.sh -c

# Run with verbose output
./run_tests.sh -v

# Run with JUnit XML reports
./run_tests.sh -j

# Combine options
./run_tests.sh -t unit -c -v
```

#### Windows

```cmd
# Run all tests
run_tests.bat

# Run specific test type
run_tests.bat -t unit
run_tests.bat -t integration
run_tests.bat -t auth

# Run with coverage
run_tests.bat -c

# Run with verbose output
run_tests.bat -v

# Run with JUnit XML reports
run_tests.bat -j

# Combine options
run_tests.bat -t unit -c -v
```

### Using Make

The project also includes a Makefile with targets for different test scenarios:

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-auth
make test-transform
make test-extract
make test-validation
make test-perf

# Run with coverage
make test-with-coverage

# Run live tests (requires EPIC credentials)
make test-live

# Clean test artifacts
make clean
```

## Generating Code Coverage Reports

To generate detailed code coverage reports:

```bash
# Using script
./gen_coverage.sh

# Or using make
make test-with-coverage
```

This will:
1. Run all tests with coverage tracking
2. Generate HTML and XML coverage reports
3. Open the HTML report in your default browser (if possible)
4. Create a coverage badge in `coverage_report/coverage-badge.json`

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py` and include:

- `spark`: SparkSession configured for testing
- `temp_output_dir`: Temporary directory for test outputs
- `mock_config_env`: Mock environment with config paths
- `sample_patient_bundle`: Sample patient data for testing
- `sample_practitioner_bundle`: Sample practitioner data for testing
- `mock_fhir_client`: Mocked FHIR client for testing

## Adding New Tests

When adding new tests:

1. Use the appropriate directory based on test type
2. Follow the naming convention: `test_*.py` for files and `test_*` for functions
3. Use fixtures from `conftest.py` when possible
4. Add docstrings explaining what the test is validating
5. Consider adding the test to a specific category in the scripts

## Setting Up the Test Environment

```bash
# Create and set up virtual environment
make setup

# Make scripts executable if needed
make permissions
``` 