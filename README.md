# ATLAS Palantir Foundry Development Guide

This repository contains code for the ATLAS project that runs in Palantir Foundry. It provides rules, templates, and examples for developing code that seamlessly transitions from local development to the Palantir Foundry environment.

## Development Workflow

1. **Local Development**: Code is developed on Mac OS
2. **Version Control**: Code is synced to GitHub
3. **Deployment**: Code is deployed to Palantir Foundry

## Key Files

- **[FOUNDRY_DEVELOPMENT_RULES.md](./FOUNDRY_DEVELOPMENT_RULES.md)**: Essential rules for Foundry-compatible code
- **[foundry_template.py](./foundry_template.py)**: Template Python file with best practices
- **[template_function.yml](./template_function.yml)**: Template YAML configuration for Foundry functions

## Getting Started

1. Clone this repository
2. Review the development rules in `FOUNDRY_DEVELOPMENT_RULES.md`
3. Use the templates as a starting point for new functions
4. Install dependencies: `pip install -r requirements.txt`
5. Test locally before deploying to Foundry

## Local Testing

The template includes a `main()` function that allows for local testing:

```bash
python foundry_template.py
```

This simulates the Foundry environment by creating a local Spark session and sample data.

## Creating New Functions

1. Copy `foundry_template.py` and rename it for your specific function
2. Copy `template_function.yml` and update it with your function's details
3. Implement your business logic in the main function
4. Test locally
5. Deploy to Foundry

## Security Notes

- Never commit secrets or credentials to the repository
- Use environment variables for local testing
- Use Foundry's secret management for production

## Common Issues and Resolutions

- **Memory Errors**: Adjust the memory allocation in the function YAML
- **Timeout Errors**: Increase the timeout setting or optimize your code
- **Dependency Issues**: Ensure all dependencies are specified with exact versions
- **Spark vs. Pandas**: Use Spark operations for large datasets, Pandas for smaller ones

## FHIR Data Processing and Validation

The repository now includes enhanced FHIR processing and validation capabilities:

### FHIR Resource Model Integration

We've integrated the `fhir.resources` library for typed FHIR resource models, which provides:
- Base FHIR specification validation
- Type-safe attribute access
- Improved data quality

### FHIR Validation Tools

1. **FHIR Resource Model Validation**
   - Automatic validation of FHIR resources against the specification
   - Robust extraction utilities for model attributes

2. **FHIR Profile Validation**
   - Integration with official HL7 FHIR Validator
   - Support for US Core and other implementation guides
   - Profile-based validation of FHIR resources

3. **Data Quality Monitoring with Great Expectations**
   - Automated expectation suites for FHIR resources
   - Data quality checks and validation reports
   - Integration with ETL pipeline

### Running Validation Tools

```bash
# Set up the FHIR Validator
python epic-fhir-integration/scripts/setup_fhir_validator.py --dir tools/fhir-validator

# Set up Great Expectations
python epic-fhir-integration/scripts/setup_great_expectations.py --install

# Run data validation
python epic-fhir-integration/scripts/run_data_validation.py --resources Patient Observation Encounter
```

See [docs/howto_validation.md](docs/howto_validation.md) for detailed documentation on validation features.

## Additional Resources

- Review existing code in this repository for real-world examples
- See `function.yml` and `appointment_pipeline.yml` for production configuration examples

## Contributing

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Make your changes following the Foundry development rules
3. Test thoroughly locally
4. Submit a pull request

# End-to-End Test Instructions with Delta Lake Support

This README provides instructions for running end-to-end tests from bronze to gold with Delta Lake support.

## Prerequisites

- Python 3.8+
- PySpark 3.5+
- Delta Lake (`pip install delta-spark`)
- FHIR Resources (`pip install fhir.resources`)
- Great Expectations (optional, for data validation)

## Configuration

1. Ensure Delta Lake is properly installed:
```bash
pip install delta-spark
```

2. Set up the test environment:
```bash
# Create test output directory
mkdir -p e2e_test_output/control/fhir_cursors
```

## Running the E2E Test

To run the full end-to-end test:

```bash
python epic-fhir-integration/e2e_test_fhir_pipeline.py --debug --output-dir e2e_test_output
```

To run with strict mode (no mock fallbacks):

```bash
python epic-fhir-integration/e2e_test_fhir_pipeline.py --debug --strict --output-dir e2e_test_output
```

To run with data validation:

```bash
python epic-fhir-integration/e2e_test_fhir_pipeline.py --debug --validate --output-dir e2e_test_output
```

## Test Output Structure

The test creates the following directory structure:

```
e2e_test_output/
├── bronze/            # Raw FHIR data (input layer)
│   └── fhir_raw/
├── silver/            # Normalized data (transformed layer)
│   └── fhir_normalized/
├── gold/              # Analytics-ready tables
│   ├── patient_summary/
│   ├── encounter_summary/
│   └── medication_summary/ 
├── config/            # Configuration files
├── control/           # Extraction cursors and workflow state
├── metrics/           # Pipeline execution metrics
├── monitoring/        # Runtime metrics
├── validation/        # Data validation reports
└── secrets/           # API tokens and credentials
```

## Troubleshooting

### Delta Lake Issues

If you encounter Delta Lake catalog errors, ensure:

1. The Delta Lake JARs are correctly installed and configured
2. The Spark session includes the correct Delta Lake catalog configuration:
   ```python
   spark = SparkSession.builder \
      .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
      .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
      .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
      .getOrCreate()
   ```

### File Format Issues

The pipeline supports multiple input formats:
- Parquet (preferred) 
- JSON
- Delta Lake tables

If one format doesn't work, try running the extraction step to generate data in Parquet format.

### Validation Issues

If you encounter validation errors:
1. Check that the FHIR Validator is installed correctly
2. Ensure Great Expectations is set up properly
3. Review validation reports in the `validation` directory
4. Consult [docs/howto_validation.md](docs/howto_validation.md) for troubleshooting 