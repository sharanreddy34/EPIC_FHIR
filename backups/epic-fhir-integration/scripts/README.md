# Test Scripts

This directory contains test scripts for the Epic FHIR Integration package.

## Available Scripts

### 1. Advanced FHIR Tools End-to-End Test (`advanced_fhir_tools_e2e_test.py`)

This comprehensive test script demonstrates all advanced FHIR tools with real Epic API calls:

```bash
python scripts/advanced_fhir_tools_e2e_test.py [--patient-id ID] [--output-dir DIR] [--debug] [--mock] [--tier TIER]
```

**Features:**
- Authentication with JWT
- Patient data extraction
- FHIRPath implementation
- Pathling analytics
- FHIR-PYrate data science
- FHIR validation
- Data quality assessment (Bronze, Silver, Gold tiers)
- Dashboard generation

**Requirements:**
- Requires all package dependencies (see `requirements.txt`)
- Fully configured environment with all API keys (if not using `--mock`)

### 2. Standalone FHIR Test (`standalone_fhir_test.py`)

A simplified test script that demonstrates core FHIR functionality without external dependencies:

```bash
python scripts/standalone_fhir_test.py [--output-dir DIR]
```

**Features:**
- FHIRPath extraction from FHIR resources
- Basic FHIR validation
- Mock FHIR API client for simulated interactions
- Generates detailed test reports in JSON and Markdown formats

**Advantages:**
- No external dependencies (all functionality is self-contained)
- Can run in environments where dependency conflicts prevent the full suite from running
- Provides a quick verification of core functionality

## Usage Tips

### Selecting the Right Test Script

- **For Production Testing:** Use `advanced_fhir_tools_e2e_test.py` with real API connections
- **For Dependency Testing:** Use `standalone_fhir_test.py` to verify core functionality
- **For Mock Testing:** Add the `--mock` flag to test without real API connections

### Output Directories

All test scripts save results to output directories:
- The default is typically a timestamped directory in the current folder
- You can specify a custom directory with `--output-dir`

### Debugging

For detailed logs, add the `--debug` flag to tests that support it.

## More Information

For detailed documentation on testing procedures, see:
- [Real World Testing Guide](../docs/REAL_WORLD_TESTING.md)
- [FHIR Tools Documentation](../docs/ADVANCED_FHIR_TOOLS.md)

## Adding New Scripts

When adding new scripts to this directory:

1. Make sure to add appropriate help text and documentation
2. Make shell scripts executable with `chmod +x script_name.sh`
3. Update this README with information about the new script 