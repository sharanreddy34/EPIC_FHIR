# Epic FHIR Integration Pipeline

This project provides a comprehensive pipeline for extracting data from Epic FHIR APIs, transforming it to normalized formats, and loading it into Palantir Foundry for analytics and AI applications.

## Overview

The pipeline consists of three main stages:

1. **Extraction (Bronze)**: Extract raw FHIR resources from Epic APIs
2. **Transformation (Silver)**: Transform raw resources to normalized, queryable format
3. **Analytics (Gold)**: Create analysis-ready datasets for reporting and AI/ML

## Architecture

```
fhir_pipeline/
│
├── auth/              # Authentication with Epic FHIR API
│   └── jwt_auth.py    # JWT token generation for Epic
│
├── io/                # Input/Output operations
│   └── fhir_client.py # Client for connecting to FHIR API
│
├── transforms/        # Data transformation layer
│   ├── base.py        # Generic BaseTransformer
│   ├── yaml_mappers.py # YAML-driven mapping engine
│   ├── registry.py    # Transformer registry
│   └── custom/        # Resource-specific transformers
│       └── patient.py # Example: Patient transformer
│
├── validation/        # Data validation components
│   └── core.py        # Validation framework
│
├── config/            # Configuration
│   └── generic_mappings/ # YAML mappings for resources
│       ├── Patient.yaml
│       ├── Observation.yaml
│       └── Encounter.yaml
│
├── pipelines/         # Spark pipeline implementations
│   ├── transform_load.py  # Bronze → Silver transformation
│   └── gold/          # Silver → Gold transformations
│
├── manifests/         # Foundry dataset manifests
│
└── utils/             # Shared utilities
    ├── logging.py     # Structured logging
    └── secrets.py     # Secret management
```

## Getting Started

### Prerequisites

- Python 3.8+
- Access to Epic FHIR API
- Palantir Foundry (optional)

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-org/epic-fhir-integration.git
   cd epic-fhir-integration
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up Epic API access:
   ```
   ./setup_epic_jwt.sh
   ```

### Running the Pipeline

#### Extract Raw FHIR Resources

```bash
python run_local_fhir_pipeline.py --steps token,extract --resource-types Patient,Observation,Encounter
```

#### Transform to Silver Format

```bash
python run_local_fhir_pipeline.py --steps transform --resource-types Patient,Observation,Encounter
```

#### Create Gold Datasets

```bash
python run_local_fhir_pipeline.py --steps gold
```

## Extending for New Resource Types

One of the key features of this pipeline is the ability to add new FHIR resource types with minimal code:

1. Create a new YAML mapping file in `config/generic_mappings/` (e.g., `DiagnosticReport.yaml`)
2. Add appropriate column mappings
3. Run the pipeline with the new resource type

Example YAML mapping:
```yaml
resourceType: DiagnosticReport
version: 1
columns:
  report_id: id
  patient_id: subject.reference.replace('Patient/','')
  status: status
  category_code: category[0].coding[0].code
  issued_datetime: issued
  result_text: "{{resource.get('text', {}).get('div', '')}}"
```

## Testing

Run the comprehensive test suite:

```bash
./run_tests.sh
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Please see CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests. 