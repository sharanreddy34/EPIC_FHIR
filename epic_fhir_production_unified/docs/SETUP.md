# Epic FHIR Pipeline Setup Guide

This document provides instructions for setting up and deploying the Epic FHIR pipeline to Palantir Foundry.

## Prerequisites

Before you begin, you will need:

1. Access to a Palantir Foundry instance
2. Epic FHIR API credentials:
   - Client ID
   - Private key (in PEM format)
   - Epic FHIR API base URL

## Step 1: Clone the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/your-org/epic_fhir_production_unified.git
cd epic_fhir_production_unified
```

## Step 2: Setup Secrets in Foundry

Secrets must be stored securely in Foundry's Secret Management system:

1. Log in to your Foundry instance
2. Navigate to **Code Repositories** → **Secrets**
3. Create a new secret scope named `epic-fhir-api`
4. Add the following secrets:

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `EPIC_CLIENT_ID` | Epic FHIR API client ID | Your client ID |
| `EPIC_PRIVATE_KEY` | Epic FHIR API private key | Your private key (PEM format) |
| `EPIC_BASE_URL` | Epic FHIR API base URL | e.g., `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` |

## Step 3: Configure the Pipeline

Review and customize the following configuration files:

- `foundry.yml` - Contains transform definitions, schedules, and cluster configurations
- `transforms-python/conda_recipe.yml` - Dependencies for the Foundry runtime

## Step 4: Create Datasets in Foundry

Create the following datasets in your Foundry instance:

### Bronze Layer
- `datasets/bronze/Patient_Raw_Bronze`
- `datasets/bronze/Encounter_Raw_Bronze`
- `datasets/bronze/Condition_Raw_Bronze`
- `datasets/bronze/Observation_Raw_Bronze`
- `datasets/bronze/MedicationRequest_Raw_Bronze`

### Silver Layer
- `datasets/silver/Patient_Silver`
- `datasets/silver/Encounter_Silver`
- `datasets/silver/Condition_Silver`
- `datasets/silver/Observation_Silver`
- `datasets/silver/MedicationRequest_Silver`

### Gold Layer
- `datasets/gold/Patient_Timeline`

### Validation
- `datasets/validation/Patient_Validation_Results`

## Step 5: Push to Foundry

Push the repository to Foundry:

```bash
# Assuming you're using Foundry's git interface
git remote add foundry https://code.palantirfoundry.com/your-instance/repos/atlas-epic-fhir-foundry
git push foundry main
```

## Step 6: Build and Deploy

In the Foundry interface:

1. Navigate to your code repository
2. Trigger a build of the repository
3. Once the build completes, navigate to the Transforms section
4. Deploy each transform in order:
   - Bronze layer transforms first
   - Then Silver layer
   - Finally Gold layer

Note: The Gold layer transforms require the Pathling JAR to be available on the Spark classpath. This is configured automatically in the `foundry.yml` file with the `sparkConf.spark.jars.packages` setting.

## Local Development and Testing

For local development and testing:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode:
   ```bash
   cd transforms-python
   pip install -e ".[dev,foundry]"
   ```

3. Set up environment variables for local testing:
   ```bash
   export EPIC_CLIENT_ID="your-client-id"
   export EPIC_PRIVATE_KEY="$(cat /path/to/private-key.pem)"
   export EPIC_BASE_URL="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
   ```

4. Run tests:
   ```bash
   pytest
   ```

5. Simulate a Foundry transform locally:
   ```bash
   # Install foundry-dev-tools if not already installed
   pip install foundry-dev-tools

   # Run a transform locally
   foundry-dev transform invoke \
     --entry-point src/epic_fhir_integration/bronze/fhir_bronze_transform.py::compute \
     --config resource_type=Patient \
     --config max_pages=5
   ```

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Verify that the EPIC_CLIENT_ID and EPIC_PRIVATE_KEY secrets are correctly set in Foundry
   - Check that the private key is in the correct PEM format

2. **Transform Failures**:
   - Check the transform logs in Foundry
   - Verify that the datasets exist and have the correct permissions

3. **Dependency Issues**:
   - Verify that all dependencies are correctly listed in conda_recipe.yml
   - Check that the versions are compatible with Foundry's runtime

### Support

For additional support:
- Check the `docs/` directory for more detailed documentation
- Contact the ATLAS team for assistance

## Maintenance

### Updating Dependencies

To update dependencies:

1. Update the versions in `conda_recipe.yml`
2. Update the corresponding versions in `setup.py` for local development
3. Test thoroughly before deploying to production

### Adding New Resource Types

To add support for a new FHIR resource type:

1. Add a new transform definition in `foundry.yml`
2. Create the corresponding datasets in Foundry
3. Update tests to cover the new resource type 