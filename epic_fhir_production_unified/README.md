# Epic FHIR Integration for Palantir Foundry

A production-ready pipeline for extracting, transforming, and analyzing FHIR data from Epic's API in Palantir Foundry.

## Overview

This repository contains a complete solution for working with Epic FHIR data in Palantir Foundry, following the medallion architecture pattern:

- **Bronze Layer**: Raw extraction of FHIR resources from Epic's API
- **Silver Layer**: Structured, normalized data with proper schemas
- **Gold Layer**: Analytics-ready datasets optimized for specific use cases

The pipeline is designed to be:
- **Production-ready**: Fully deployable to Foundry with proper error handling and monitoring
- **Scalable**: Handles large volumes of FHIR data using Spark
- **Extensible**: Easily add new resource types or custom transformations
- **Standards-compliant**: Uses industry-standard FHIR libraries and tools

## Quick Start

### Prerequisites

- Access to a Palantir Foundry instance
- Epic FHIR API credentials (client ID, private key)
- Git and Python 3.10+

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/epic_fhir_production_unified.git
   cd epic_fhir_production_unified
   ```

2. Set up your Epic FHIR API credentials in Foundry's Secret Management:
   - Create a secret scope named `epic-fhir-api`
   - Add secrets for `EPIC_CLIENT_ID`, `EPIC_PRIVATE_KEY`, and `EPIC_BASE_URL`

3. Create the datasets in Foundry (see `docs/SETUP.md` for details)

4. Push to Foundry:
   ```bash
   git remote add foundry https://code.palantirfoundry.com/your-instance/repos/atlas-epic-fhir-foundry
   git push foundry main
   ```

5. Build and deploy the transforms in Foundry

For detailed setup instructions, see [Setup Guide](docs/SETUP.md).

## Architecture

The pipeline follows the medallion architecture pattern:

```
Epic FHIR API → Bronze (Raw) → Silver (Structured) → Gold (Analytics)
```

Key components:
- JWT authentication with Epic's FHIR API
- Incremental extraction with watermarks
- Structured data validation
- Patient-centered timeline generation
- Integration with Pathling for FHIR-specific queries

For architecture details, see [Architecture Documentation](docs/architecture.md).

## Features

- **Multi-resource support**: Extract Patient, Encounter, Condition, Observation, MedicationRequest, and more
- **Incremental loading**: Extract only new or updated resources
- **Data validation**: Validate resources against FHIR schemas and custom rules
- **Patient-centered analytics**: Generate patient timelines and cohorts
- **Resilient operations**: Retry logic, error handling, and circuit breaking
- **Comprehensive logging**: Structured logging for monitoring and debugging

## Project Structure

This project follows a Foundry-centric structure:

- `transforms-python/`: **IMPORTANT** - This is the canonical source of code deployed to Foundry. 
  - The package in `transforms-python/src/epic_fhir_integration` is what gets built and executed in Foundry.
  - All development work should happen here.

- `src/`: **DEPRECATED** - This contains legacy code that is NOT deployed to Foundry. 
  - This directory is kept for reference only and should not be modified.
  - Any useful utilities should be migrated to the transforms-python tree.

- `foundry.yml`: Defines all transforms that run in Foundry, connecting to the code in transforms-python.

- `config/`: Configuration files and templates.

- `docs/`: Documentation and diagrams.

- `tests/`: Unit and integration tests.

## Deployment Prerequisites

Before deploying to Foundry, ensure:

1. Secret scope `epic-fhir-api` is populated with:
   - `EPIC_CLIENT_ID` - Your Epic FHIR API client ID
   - `EPIC_PRIVATE_KEY` - JWT private key for authentication
   - `EPIC_BASE_URL` - Base URL for the Epic FHIR API

2. All tests pass locally:
   ```
   cd transforms-python
   pytest
   ```

## Directory Structure

```
epic_fhir_production_unified/
├── datasets/                  # Foundry dataset manifests
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
├── tests/                     # Test suite
├── transforms-python/         # Python transforms
│   ├── src/                   # Source code
│   │   └── epic_fhir_integration/
│   │       ├── api_clients/   # Epic API clients
│   │       ├── bronze/        # Bronze layer transforms
│   │       ├── silver/        # Silver layer transforms
│   │       ├── gold/          # Gold layer transforms
│   │       ├── validation/    # Data validation
│   │       └── utils/         # Utilities
│   ├── conda_recipe.yml       # Conda dependencies
│   └── setup.py               # Package setup
├── foundry.yml                # Foundry transform definitions
└── README.md                  # This file
```

## Development

For local development:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install the package in development mode:
   ```bash
   cd transforms-python
   pip install -e ".[dev,foundry]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

## Documentation

- [Setup Guide](docs/SETUP.md) - Detailed setup instructions
- [Architecture](docs/architecture.md) - Architecture overview
- [API Reference](docs/api.md) - API documentation
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- FHIR® is the registered trademark of HL7 and is used with the permission of HL7.
- Epic® is a registered trademark of Epic Systems Corporation.
- Palantir Foundry® is a registered trademark of Palantir Technologies Inc. 
## Update (May 22, 2023)

Enhanced EPIC FHIR integration pipeline with improved performance and configuration options.
