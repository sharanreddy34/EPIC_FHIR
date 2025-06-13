# How to Validate FHIR Data

This document provides instructions on how to validate FHIR data using the tools implemented in this project.

## Table of Contents

1. [FHIR Resource Model Validation](#fhir-resource-model-validation)
2. [FHIR Profile Validation](#fhir-profile-validation)
3. [Data Quality Monitoring with Great Expectations](#data-quality-monitoring-with-great-expectations)

## FHIR Resource Model Validation

Our codebase now provides built-in validation of FHIR resources using the `fhir.resources` library. This validation ensures that resources conform to the base FHIR specification.

### How to Use

```python
from fhir.resources.patient import Patient
from epic_fhir_integration.schemas.fhir_resources import parse_resource, validate_resource

# Validate from a dictionary
patient_dict = {
    "resourceType": "Patient",
    "id": "example",
    "name": [{"family": "Smith", "given": ["John"]}],
    "gender": "male"
}

validation_errors = validate_resource(patient_dict)
if not validation_errors:
    print("Patient is valid!")
else:
    print(f"Validation errors: {validation_errors}")

# Validate a parsed resource model
try:
    patient = parse_resource(patient_dict)
    print("Patient parsed successfully")
except Exception as e:
    print(f"Error parsing patient: {e}")
```

## FHIR Profile Validation

We've integrated the official HL7 FHIR Validator to validate resources against FHIR profiles and implementation guides.

### Setup

1. Run the setup script to download and configure the validator:

```bash
cd epic-fhir-integration
python scripts/setup_fhir_validator.py --dir tools/fhir-validator
```

This will:
- Download the official FHIR Validator JAR
- Set up US Core Implementation Guide
- Create helper scripts for running the validator

### How to Use

#### From the Command Line

```bash
# Validate a FHIR resource against a profile
tools/fhir-validator/run_validator.sh path/to/resource.json -profile http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient
```

#### From Python

```python
from epic_fhir_integration.utils.fhir_validator import FHIRValidator, ValidationReportGenerator
from fhir.resources.patient import Patient

# Initialize validator
validator = FHIRValidator()

# Validate a resource
patient = Patient.model_validate({
    "resourceType": "Patient",
    "id": "example",
    "name": [{"family": "Smith", "given": ["John"]}],
    "gender": "male"
})

result = validator.validate_resource(patient)
print(f"Valid: {result['valid']}")
print(f"Errors: {len(result['errors'])}")

# Generate a validation report
generator = ValidationReportGenerator(validator)
report = generator.generate_report_for_resource(patient)
print(report["summary"]["text"])
```

## Data Quality Monitoring with Great Expectations

We've integrated Great Expectations for data quality monitoring of FHIR data.

### Setup

1. Run the setup script to initialize Great Expectations:

```bash
cd epic-fhir-integration
python scripts/setup_great_expectations.py --install
```

This will:
- Install Great Expectations if needed
- Create a Great Expectations project
- Configure datasources for Bronze, Silver, and Gold data layers
- Create basic expectation suites for FHIR resources

### How to Run Validations

```bash
cd epic-fhir-integration
python scripts/run_data_validation.py --resources Patient Observation Encounter --layer gold
```

This will:
- Validate FHIR data against the expectation suites
- Generate validation reports
- Build data docs with visualizations of validation results

### Viewing Results

After running validations, you can view the results in the generated data docs:

```bash
open epic-fhir-integration/great_expectations/data_docs/local_site/index.html
```

### Custom Expectations

To create custom expectations for your FHIR data:

1. Use the Great Expectations CLI to create a new expectation suite:

```bash
cd epic-fhir-integration
great_expectations suite new
```

2. Or customize the existing suites programmatically:

```python
from great_expectations.data_context import DataContext
from great_expectations.core.expectation_configuration import ExpectationConfiguration

context = DataContext("epic-fhir-integration/great_expectations")
suite = context.get_expectation_suite("patient_suite")

# Add a custom expectation
suite.add_expectation(
    ExpectationConfiguration(
        expectation_type="expect_column_values_to_match_regex",
        kwargs={
            "column": "phone",
            "regex": r"^\+?[1-9]\d{1,14}$"  # E.164 phone number format
        }
    )
)

# Save the updated suite
context.save_expectation_suite(suite)
```

## Continuous Integration

To integrate validation into your CI pipeline, add these steps to your CI workflow:

```yaml
- name: Set up FHIR Validator
  run: python scripts/setup_fhir_validator.py --dir tools/fhir-validator

- name: Set up Great Expectations
  run: python scripts/setup_great_expectations.py 

- name: Validate FHIR data
  run: python scripts/run_data_validation.py --resources Patient Observation Encounter
```

This will ensure that your FHIR data meets quality standards before being deployed or used in production. 