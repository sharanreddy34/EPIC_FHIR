# Epic FHIR Integration

This module provides tools for integrating with Epic's FHIR API and processing FHIR data.

## Features

- FHIR data extraction from Epic APIs
- FHIR data transformation between Bronze, Silver, and Gold layers
- Type-safe FHIR resource handling using `fhir.resources`
- FHIR validation against base specification and profiles
- Data quality monitoring with Great Expectations

## Directory Structure

```
epic_fhir_integration/
├── auth/                # Authentication utilities
├── cli/                 # Command-line interface tools
├── config/              # Configuration management
├── extract/             # Data extraction utilities
├── io/                  # Input/output utilities
├── metrics/             # Metrics collection
├── schemas/             # FHIR schema definitions
├── security/            # Security utilities
├── transform/           # Data transformation logic
└── utils/               # Utility functions
```

## FHIR Resource Models

We use the `fhir.resources` library to provide typed FHIR resource models. This provides several benefits:

- Automatic validation against the FHIR specification
- Type-safe attribute access
- Improved code maintainability

Example usage:

```python
from fhir.resources.patient import Patient
from epic_fhir_integration.schemas.fhir_resources import parse_resource

# Parse a dictionary into a FHIR resource model
patient_dict = {
    "resourceType": "Patient",
    "id": "example",
    "name": [{"family": "Smith", "given": ["John"]}],
    "gender": "male"
}
patient = parse_resource(patient_dict)

# Access attributes in a type-safe way
family_name = patient.name[0].family  # "Smith"
first_name = patient.name[0].given[0]  # "John"
```

## Validation Tools

### 1. Base FHIR Validation

The `fhir.resources` library provides automatic validation against the base FHIR specification:

```python
from epic_fhir_integration.schemas.fhir_resources import validate_resource

errors = validate_resource(patient_dict)
if not errors:
    print("Patient is valid!")
else:
    print(f"Validation errors: {errors}")
```

### 2. FHIR Profile Validation

We provide integration with the official HL7 FHIR Validator to validate resources against FHIR profiles:

```python
from epic_fhir_integration.utils.fhir_validator import FHIRValidator

validator = FHIRValidator()
result = validator.validate_resource(patient, profile="http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient")
print(f"Valid: {result['valid']}")
```

### 3. Data Quality Monitoring

We've integrated Great Expectations for data quality monitoring:

```python
from great_expectations.data_context import DataContext

context = DataContext("great_expectations")
checkpoint = context.get_checkpoint("patient_checkpoint")
result = checkpoint.run()
print(f"Validation success: {result.success}")
```

## Scripts

Several utility scripts are provided to set up validation tools:

- `scripts/setup_fhir_validator.py`: Sets up the official HL7 FHIR Validator
- `scripts/setup_great_expectations.py`: Sets up Great Expectations for data quality monitoring
- `scripts/run_data_validation.py`: Runs data validation against FHIR data

Run these scripts with the `--help` flag to see available options.

## Configuration

Configuration for the FHIR integration is managed in `config/` directory. Key configurations include:

- `api_config.py`: Epic FHIR API configuration
- `validation_config.py`: Validation tool configuration
- `profiles_config.py`: FHIR profile configuration

## ETL Pipeline

The ETL pipeline processes FHIR data through three layers:

1. **Bronze**: Raw FHIR data from the API
2. **Silver**: Normalized and validated FHIR data
3. **Gold**: Analytics-ready tables

Each layer has its own transformation and validation steps.

## Getting Started

1. Set up your environment:

```bash
pip install -r requirements.txt
```

2. Configure the Epic FHIR API credentials:

```bash
# Set environment variables
export EPIC_CLIENT_ID=your_client_id
export EPIC_CLIENT_SECRET=your_client_secret
```

3. Run the end-to-end pipeline:

```bash
python run_local_fhir_pipeline.py
```

## Advanced Usage

See the [documentation](../docs/) for advanced usage scenarios.

- [Data Extraction](../docs/data_extraction.md)
- [Data Transformation](../docs/data_transformation.md)
- [Data Validation](../docs/howto_validation.md)
- [API Integration](../docs/api_integration.md) 