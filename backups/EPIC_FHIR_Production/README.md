# Epic FHIR Integration for Palantir Foundry

This repository contains the Epic FHIR Integration pipeline for Palantir Foundry, which extracts data from Epic's FHIR API and processes it through bronze, silver, and gold layers in Foundry.

## Components

- **Extract**: Pulls FHIR resources from Epic's API
- **Transform Bronze to Silver**: Processes raw FHIR resources into normalized silver data
- **Transform Silver to Gold**: Creates analysis-ready gold datasets
- **Quality**: Validates and reports on data quality

## Deployment

The codebase is packaged as a Docker container that can be deployed to Palantir Foundry as container functions.

### Building the Docker Image

```bash
# Setup and build
make all  # Builds Python wheel and Docker image

# Testing the Docker image
make test-foundry-img

# Exporting for Foundry upload
make export-foundry-img  # Creates epic-fhir-foundry.tar.gz
```

### Deploying to Foundry

1. Create a new Foundry Code Repository
2. Upload the wheel (`dist/*.whl`) and Docker image tarball (`epic-fhir-foundry.tar.gz`)
3. Import the container image: `foundry container-image import epic-fhir-foundry.tar.gz --name epic-fhir-tools`
4. Create the Epic OAuth secret: `foundry secret create epic-oauth-secret --file ./secrets/epic-oauth.json`
5. Deploy the Functions YAMLs from the `functions/` directory

## Function Configuration

The following environment variables can be configured in Foundry:

- `EPIC_BASE_URL`: URL of the Epic FHIR API
- `DATA_ROOT`: Base directory for data (default: `/foundry/objects`)
- `PATHLING_IMPORT_ENABLED`: Whether to enable Pathling (default: `true`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Development

For local development:

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install for development
pip install -e .

# Run the CLI
epic-fhir --help
``` 