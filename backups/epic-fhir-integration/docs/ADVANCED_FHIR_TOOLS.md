# Advanced FHIR Tools Documentation

This document provides comprehensive documentation for the advanced FHIR tools integrated into the Epic FHIR Integration codebase.

## Table of Contents

1. [FHIRPath Implementation](#1-fhirpath-implementation)
2. [Pathling Analytics Service](#2-pathling-analytics-service)
3. [FHIR-PYrate Data Science Tools](#3-fhir-pyrate-data-science-tools)
4. [FHIR Shorthand & Validation Framework](#4-fhir-shorthand--validation-framework)
5. [CLI Commands](#5-cli-commands)
6. [Performance Benchmarks](#6-performance-benchmarks)
7. [Integration Testing](#7-integration-testing)

## 1. FHIRPath Implementation

### Overview

The codebase now includes an upgraded FHIRPath implementation which replaces the previous `fhirpathpy` library with the more powerful `fhirpath` library. The implementation uses an adapter pattern to maintain backward compatibility.

### Key Components

#### FHIRPathAdapter

The `FHIRPathAdapter` class in `epic_fhir_integration/utils/fhirpath_adapter.py` provides:

- Full compatibility with the FHIRPath specification
- Improved performance for complex queries
- Caching to optimize repeated queries
- Better error handling

```python
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Create a new adapter
adapter = FHIRPathAdapter()

# Extract data from a FHIR resource
result = adapter.extract(resource, "Patient.name.given")

# Extract the first matching value
first_name = adapter.extract_first(resource, "Patient.name.where(use='official').given.first()")

# Check if an element exists
has_telecom = adapter.exists(resource, "telecom.where(system='phone')")
```

#### Migration Guide

To migrate from the old FHIRPathExtractor to the new FHIRPathAdapter:

1. Import the new adapter:
   ```python
   from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
   ```

2. Create an instance:
   ```python
   adapter = FHIRPathAdapter()
   ```

3. Use the same method names as before:
   ```python
   # Old way
   result = FHIRPathExtractor.extract(resource, path)
   
   # New way
   result = adapter.extract(resource, path)
   ```

The old `FHIRPathExtractor` class still works but now uses the new adapter internally with fallback to the original implementation if needed.

### Advanced Features

- **Complex Expressions**: Support for the full FHIRPath specification including functions like `where()`, `select()`, `aggregate()`, etc.
- **Type Handling**: Better handling of FHIR data types and polymorphic fields
- **Performance Optimization**: Caching mechanism for frequently used paths
- **Error Recovery**: Advanced error handling with detailed error messages

## 2. Pathling Analytics Service

### Overview

The Pathling Analytics Service provides powerful population-level analytics for FHIR data. It enables aggregation, extraction of datasets, and measure evaluation.

### Requirements

- Java 11+ is required for Pathling
- Docker can be used as an alternative deployment option

### Key Components

#### PathlingService

The `PathlingService` class in `epic_fhir_integration/analytics/pathling_service.py` provides:

- Server management (start/stop/status)
- Data import functionality
- Aggregation operations
- Dataset extraction
- Measure evaluation

```python
from epic_fhir_integration.analytics.pathling_service import PathlingService

# Create a service instance
service = PathlingService()

# Start the server (if not already running)
service.start()

# Import FHIR data
service.import_data("/path/to/fhir/data")

# Perform aggregation
result = service.aggregate(
    subject="Patient",
    aggregation="count()",
    grouping="gender"
)

# Extract a dataset
dataset = service.extract_dataset(
    source="Observation",
    columns=["subject.reference", "valueQuantity.value", "code.coding.code"]
)

# Evaluate a measure
measure_result = service.evaluate_measure(
    numerator="Patient.where(gender='female')",
    denominator="Patient"
)

# Stop the server when done
service.stop()
```

### Docker Support

The Pathling service can be run in a Docker container for consistent deployment:

```python
# Start Pathling in Docker
service = PathlingService(use_docker=True)
service.start()

# Use as normal
service.import_data("/path/to/fhir/data")
```

### Analytics Capabilities

- **Aggregation**: Count, sum, average, statistics on any FHIR element
- **Grouping**: Group results by any FHIR element
- **Filtering**: Apply complex filters to include specific resources
- **Dataset Extraction**: Create tabular datasets from FHIR resources
- **Measures**: Calculate ratios and percentages for clinical measures

## 3. FHIR-PYrate Data Science Tools

### Overview

The FHIR-PYrate integration provides tools for data science workflows, making it easier to create datasets from FHIR resources and define patient cohorts.

### Key Components

#### FHIRDatasetBuilder

The `FHIRDatasetBuilder` class in `epic_fhir_integration/datascience/fhir_dataset.py` enables:

- Building datasets from FHIR resources
- Extracting specific elements as columns
- Handling relationships between resources
- Converting to pandas DataFrames

```python
from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder

# Create a dataset builder
builder = FHIRDatasetBuilder()

# Add resources
builder.add_resources("Patient", patient_resources)
builder.add_resources("Observation", observation_resources)

# Build a dataset with Patient demographics
dataset = builder.build_dataset(
    index_by="Patient",
    columns=[
        {"path": "Patient.gender", "name": "gender"},
        {"path": "Patient.birthDate", "name": "birth_date"}
    ]
)

# Include data from related resources
bp_dataset = builder.build_dataset(
    index_by="Patient",
    columns=[
        {"path": "Patient.gender", "name": "gender"},
        {"resource": "Observation", "path": "valueQuantity.value", "code": "8480-6", "name": "bp_value"}
    ]
)

# Get a pandas DataFrame
df = dataset.to_pandas()
```

#### CohortBuilder

The `CohortBuilder` class enables definition of patient cohorts based on clinical criteria:

```python
from epic_fhir_integration.datascience.fhir_dataset import CohortBuilder

# Create a cohort builder
cohort_builder = CohortBuilder(
    patients=patient_resources,
    observations=observation_resources,
    conditions=condition_resources
)

# Build a cohort of patients with hypertension
hypertension_cohort = cohort_builder.with_condition(
    system="http://snomed.info/sct",
    code="38341003"  # Hypertension
)

# Add criteria for blood pressure observations
high_bp_cohort = hypertension_cohort.with_observation(
    system="http://loinc.org",
    code="8480-6",  # Blood Pressure
    value_comparison=lambda v: v > 140
)

# Get patient IDs in the cohort
patient_ids = high_bp_cohort.get_patient_ids()

# Or get the actual patient resources
patients = high_bp_cohort.get_patients()
```

### Advanced Data Science Features

- **Temporal Analysis**: Support for point-in-time analysis
- **Feature Engineering**: Derive features from complex FHIR structures
- **ML Dataset Preparation**: Prepare datasets ready for machine learning
- **Cohort Comparison**: Compare different patient cohorts
- **Outcome Analysis**: Analyze outcomes for specific cohorts

## 4. FHIR Shorthand & Validation Framework

### Overview

The FHIR Shorthand (FSH) and Validation Framework enables definition of FHIR profiles using the concise FSH syntax and validation of FHIR resources against these profiles.

### Key Components

#### FHIR Profiles

The `epic_fhir_integration/profiles/` directory contains FSH definitions for common resource types:

- `epic/Patient.fsh`: Profile for Epic patient resources
- `epic/Observation.fsh`: Profile for Epic observation resources
- `sushi-config.yaml`: Configuration for the SUSHI compiler

#### FHIRValidator

The `FHIRValidator` class in `epic_fhir_integration/validation/validator.py` provides:

- Validation of FHIR resources against standard and custom profiles
- Compilation of FSH files into implementation guides
- Batch validation for multiple resources
- Detailed validation results

```python
from epic_fhir_integration.validation.validator import FHIRValidator

# Create a validator instance
validator = FHIRValidator()

# Validate a single resource
result = validator.validate(fhir_resource)
if result.is_valid:
    print("Resource is valid")
else:
    print(f"Validation errors: {result.get_errors()}")

# Validate multiple resources
results = validator.validate_batch([resource1, resource2, resource3])

# Compile FSH profiles to an IG package
validator.compile_fsh(
    fsh_directory="path/to/fsh",
    output_directory="path/to/output"
)

# Compile and validate in one step
results = validator.compile_and_validate(
    fsh_directory="path/to/fsh",
    resources=[resource1, resource2]
)
```

### Validation Capabilities

- **Standard Validation**: Validate against the base FHIR specification
- **Profile Validation**: Validate against custom profiles
- **Implementation Guides**: Support for standard and custom IGs
- **Error Reporting**: Detailed error messages and warnings
- **Custom Profiles**: Define and validate against organization-specific profiles

## 5. CLI Commands

The integration includes a comprehensive set of CLI commands for all new functionality.

### FHIRPath Commands

```bash
# Extract data using FHIRPath
python -m epic_fhir_integration.cli fhirpath extract --resource-path /path/to/resource.json --path "Patient.name.given"

# Check if a path exists
python -m epic_fhir_integration.cli fhirpath exists --resource-path /path/to/resource.json --path "telecom.where(system='phone')"
```

### Pathling Analytics Commands

```bash
# Start the Pathling server
python -m epic_fhir_integration.cli pathling start

# Import FHIR data
python -m epic_fhir_integration.cli pathling import --input-dir /path/to/fhir/data

# Perform aggregation
python -m epic_fhir_integration.cli pathling aggregate --subject Patient --aggregation "count()" --grouping gender

# Extract a dataset
python -m epic_fhir_integration.cli pathling extract --source Patient --columns id,gender,birthDate --output patient_data.csv

# Stop the Pathling server
python -m epic_fhir_integration.cli pathling stop
```

### Data Science Commands

```bash
# Create a dataset from FHIR resources
python -m epic_fhir_integration.cli datascience build-dataset --resources-dir /path/to/resources --index Patient --output dataset.csv

# Define a cohort
python -m epic_fhir_integration.cli datascience build-cohort --resources-dir /path/to/resources --condition-code 38341003 --output cohort.json
```

### Validation Commands

```bash
# Validate a FHIR resource
python -m epic_fhir_integration.cli validate resource --resource-path /path/to/resource.json

# Compile FSH profiles
python -m epic_fhir_integration.cli validate compile-fsh --fsh-dir /path/to/fsh --output-dir /path/to/output

# Validate against custom profiles
python -m epic_fhir_integration.cli validate batch --resources-dir /path/to/resources --profile-path /path/to/profiles
```

## 6. Performance Benchmarks

Performance benchmarks have been implemented to measure the improvements from the new implementations:

### FHIRPath Performance

The FHIRPath performance tests in `epic_fhir_integration/tests/perf/test_fhirpath_performance.py` benchmark:

- Simple path extraction
- Filter expressions
- Complex expressions
- Batch processing with different sizes

Run the benchmarks:

```bash
python -m pytest epic_fhir_integration/tests/perf/test_fhirpath_performance.py -v
```

### Pathling Performance

The Pathling performance tests in `epic_fhir_integration/tests/perf/test_pathling_performance.py` benchmark:

- Aggregation operations
- Dataset extraction
- Measure evaluation

Run the benchmarks:

```bash
python -m pytest epic_fhir_integration/tests/perf/test_pathling_performance.py -v
```

## 7. Integration Testing

Integration tests have been implemented to verify the functionality of all components working together:

### FHIRPath Integration Tests

The FHIRPath integration tests verify:

- Compatibility between old and new implementations
- Handling of complex queries
- Error handling
- Performance improvements

### Pathling Integration Tests

The Pathling integration tests verify:

- Server startup and shutdown
- Data import capabilities
- Aggregation functionality
- Dataset extraction
- Measure evaluation

### Data Science Integration Tests

The Data Science integration tests verify:

- Dataset creation from FHIR resources
- Feature extraction from resources
- Cohort building functionality
- Integration with pandas

### Validation Integration Tests

The Validation integration tests verify:

- Validation against FHIR base specification
- Compilation of FSH profiles
- Validation against custom profiles
- Error reporting

Run all integration tests:

```bash
python -m pytest epic_fhir_integration/tests/integration/
```

## Summary

The integration of these advanced FHIR tools has significantly enhanced the capabilities of the Epic FHIR Integration codebase:

1. **Improved FHIRPath Implementation**: Better performance, full specification support, and backward compatibility
2. **Powerful Analytics**: Population-level analytics with Pathling
3. **Data Science Workflows**: Simplified dataset creation and cohort management with FHIR-PYrate
4. **Profile Management**: FHIR Shorthand for profile definition and validation

These tools work together to provide a comprehensive platform for FHIR data processing, analysis, and validation. 