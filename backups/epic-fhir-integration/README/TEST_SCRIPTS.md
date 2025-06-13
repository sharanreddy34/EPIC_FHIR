# TEST SCRIPTS

This document provides an overview of the test scripts available in this project and how to use them to run tests for the FHIR Pipeline.

## Quick Reference

### Unix/Linux/macOS

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test types
./scripts/run_tests.sh -t unit            # Unit tests
./scripts/run_tests.sh -t integration     # Integration tests
./scripts/run_tests.sh -t perf            # Performance tests

# Run tests for specific components
./scripts/run_tests.sh -t auth            # Auth module
./scripts/run_tests.sh -t client          # FHIR client
./scripts/run_tests.sh -t transform       # Transformations
./scripts/run_tests.sh -t extract         # Extract pipeline
./scripts/run_tests.sh -t validation      # Validation module

# Run with options
./scripts/run_tests.sh -c                 # With coverage
./scripts/run_tests.sh -v                 # Verbose output
./scripts/run_tests.sh -j                 # Generate JUnit XML reports

# Generate detailed coverage report
./scripts/gen_coverage.sh
```

### Windows

```cmd
REM Run all tests
scripts\run_tests.bat

REM Run specific test types
scripts\run_tests.bat -t unit
scripts\run_tests.bat -t integration

REM Run with coverage
scripts\run_tests.bat -c
```

### Make Commands

```bash
make test                 # Run all tests
make test-unit            # Run unit tests only
make test-integration     # Run integration tests only
make test-coverage        # Run with coverage

# Component-specific tests
make test-auth            # Auth tests
make test-client          # FHIR client tests
make test-transform       # Transformation tests
make test-extract         # Extract pipeline tests
make test-validation      # Validation tests

make clean                # Clean test artifacts
```

## Detailed Script Descriptions

### `run_tests.sh` / `run_tests.bat`

The main test runner scripts support the following options:

| Option | Description |
|--------|-------------|
| `-t, --type TYPE` | Test type to run (all, unit, integration, etc.) |
| `-v, --verbose` | Show verbose output |
| `-c, --coverage` | Generate coverage report |
| `-j, --junit` | Generate JUnit XML reports |
| `-h, --help` | Show help message |

#### Available Test Types

- `all`: Run all tests
- `unit`: Run unit tests only
- `integration`: Run integration tests only
- `perf`: Run performance tests only
- `auth`: Run auth module tests
- `client`: Run FHIR client tests
- `transform`: Run transformation tests
- `extract`: Run extract pipeline tests
- `validation`: Run validation tests

#### Examples

```bash
# Run all tests with coverage and verbose output
./scripts/run_tests.sh -c -v

# Run auth tests with JUnit reports
./scripts/run_tests.sh -t auth -j

# Run unit tests with coverage
./scripts/run_tests.sh -t unit -c
```

### `gen_coverage.sh`

This script generates a detailed HTML coverage report and opens it in your default browser.

```bash
./scripts/gen_coverage.sh
```

Features:
- Runs all tests with coverage tracking
- Generates HTML and XML coverage reports
- Creates a coverage badge JSON file
- Automatically opens the HTML report in your browser

## Using the Makefile

For users who prefer `make` commands, the project includes a Makefile with several test targets:

```bash
# Run all tests
make test

# Run specific test suites
make test-unit
make test-integration
make test-perf

# Run component-specific tests
make test-auth
make test-client
make test-transform
make test-extract
make test-validation

# Run with coverage
make test-coverage

# Clean up test artifacts
make clean
```

## Setting Up Testing Environment

The test scripts will automatically:

1. Create a Python virtual environment if one doesn't exist
2. Install required dependencies
3. Run the tests with the specified options

## Troubleshooting

If you encounter issues running the scripts:

1. Make sure scripts have execute permissions:
   ```bash
   chmod +x scripts/run_tests.sh scripts/gen_coverage.sh
   ```

2. Verify Python and required dependencies are installed:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov
   ```

3. If you get "Permission denied" in Windows, try:
   ```cmd
   python scripts\run_tests.bat -t unit
   ```

## CI/CD Integration

These scripts can be easily integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Run tests with coverage
      run: ./scripts/run_tests.sh -c -j
``` 