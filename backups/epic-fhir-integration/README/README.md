# Epic FHIR Integration

A comprehensive toolkit for integrating with Epic's FHIR API, processing FHIR resources, and performing analytics on healthcare data.

## Overview

This project provides a robust framework for:

1. **Authentication** with Epic's FHIR API
2. **Extraction** of FHIR resources
3. **Transformation** of FHIR data
4. **Loading** into various target formats
5. **Analytics** and reporting on healthcare data
6. **Data Science** workflows with FHIR data
7. **Validation** against FHIR profiles

## Features

- **Epic FHIR API Client**: Authenticate and interact with Epic's FHIR API
- **Enhanced FHIRPath**: Powerful querying of FHIR resources using the full FHIRPath specification
- **Population Analytics**: Population-level analytics using Pathling
- **Data Science Tools**: Integration with FHIR-PYrate for data science workflows
- **Validation Framework**: Validate FHIR resources against profiles using FHIR Shorthand
- **CLI Commands**: Comprehensive command-line interface for all functionality
- **ETL Pipeline**: Complete Extract-Transform-Load pipeline for FHIR data
- **Testing Framework**: Comprehensive test suite including unit, integration, and performance tests

## Installation

### Prerequisites

- Python 3.9+
- Java 11+ (for Pathling analytics)
- Node.js 14+ (for FHIR Shorthand compilation)

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/epic-fhir-integration.git
cd epic-fhir-integration

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

### With Optional Dependencies

```bash
# Install with all optional dependencies
pip install -e .[all]

# Or install specific components
pip install -e .[pathling]  # For Pathling analytics
pip install -e .[fhirpy]    # For FHIR-PYrate data science
pip install -e .[validation]  # For FHIR Shorthand & validation
```

## Quick Start

### Authentication

```python
from epic_fhir_integration.auth import EpicAuthClient

# Create auth client
auth_client = EpicAuthClient.from_config("config/epic_auth.json")

# Get access token
token = auth_client.get_token()
```

### Extracting FHIR Resources

```python
from epic_fhir_integration.extract import FHIRClient

# Create FHIR client
client = FHIRClient(base_url="https://fhir.epic.com/api/FHIR/R4", token=token)

# Get patients
patients = client.search("Patient", given="John", family="Smith")

# Get observations for a patient
observations = client.search("Observation", subject=f"Patient/{patient_id}")
```

### Using FHIRPath

```python
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Create FHIRPath adapter
adapter = FHIRPathAdapter()

# Extract values
names = adapter.extract(patient, "name.where(use='official').given")
```

### Analytics with Pathling

```python
from epic_fhir_integration.analytics.pathling_service import PathlingService

# Create Pathling service
service = PathlingService()
service.start()

# Import data
service.import_data("path/to/fhir/data")

# Perform aggregation
result = service.aggregate(
    subject="Patient",
    aggregation="count()",
    grouping="gender"
)

# Create dataset
dataset = service.extract_dataset(
    source="Observation", 
    columns=["subject.reference", "valueQuantity.value"]
)
```

### Data Science with FHIR-PYrate

```python
from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder, CohortBuilder

# Create dataset
builder = FHIRDatasetBuilder()
builder.add_resources("Patient", patients)
builder.add_resources("Observation", observations)

dataset = builder.build_dataset(
    index_by="Patient",
    columns=[
        {"path": "Patient.gender", "name": "gender"},
        {"resource": "Observation", "path": "valueQuantity.value", "code": "8480-6", "name": "bp_value"}
    ]
)

# Create cohort
cohort = CohortBuilder(patients=patients, observations=observations)
    .with_condition(system="http://snomed.info/sct", code="38341003")
    .get_patients()
```

### Validation

```python
from epic_fhir_integration.validation.validator import FHIRValidator

# Create validator
validator = FHIRValidator()

# Validate resource
result = validator.validate(resource)
if not result.is_valid:
    print(f"Validation errors: {result.get_errors()}")
```

## CLI Usage

```bash
# Authentication
python -m epic_fhir_integration.cli auth get-token --config config/epic_auth.json

# Extract FHIR resources
python -m epic_fhir_integration.cli extract get-patients --given John --family Smith

# FHIRPath
python -m epic_fhir_integration.cli fhirpath extract --resource-path patient.json --path "name.given"

# Pathling analytics
python -m epic_fhir_integration.cli pathling aggregate --subject Patient --aggregation "count()" --grouping gender

# Data Science
python -m epic_fhir_integration.cli datascience build-dataset --resources-dir ./data --index Patient --output dataset.csv

# Validation
python -m epic_fhir_integration.cli validate resource --resource-path patient.json
```

## Pipeline Execution

The project includes a full end-to-end FHIR pipeline:

```bash
# Run the full ETL pipeline
python run_local_fhir_pipeline.py --config config/pipeline_config.json
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Getting Started](docs/GETTING_STARTED.md)
- [Authentication Guide](docs/AUTHENTICATION.md)
- [Pipeline Reference](docs/PIPELINE.md)
- [Advanced FHIR Tools](docs/ADVANCED_FHIR_TOOLS.md)
- [API Reference](docs/API.md)
- [CLI Reference](docs/CLI.md)

## Testing

```bash
# Run all tests
python -m pytest

# Run unit tests
python -m pytest epic_fhir_integration/tests/unit/

# Run integration tests
python -m pytest epic_fhir_integration/tests/integration/

# Run performance benchmarks
python -m pytest epic_fhir_integration/tests/perf/
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](docs/CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
