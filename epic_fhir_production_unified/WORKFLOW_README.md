# Epic FHIR Production Unified Workflow

## Overview

This document provides a comprehensive explanation of the Epic FHIR Production Unified workflow for Palantir software developers. This production-ready pipeline extracts, transforms, and analyzes FHIR data from Epic's API within Palantir Foundry, following a medallion architecture pattern.

## Architecture

The workflow follows a three-tiered medallion architecture:

1. **Bronze Layer**: Raw extraction of FHIR resources from Epic's API
2. **Silver Layer**: Structured, normalized data with enforced schemas
3. **Gold Layer**: Analytics-ready datasets optimized for specific use cases

### Architecture Diagram

The system uses a layered approach with clear separation of concerns:

```
Epic FHIR API → JWT Auth → Bronze Layer → Silver Layer → Gold Layer
                                      ↓           ↓           ↓
                              Validation Layer (Runs across all layers)
```

### Key Components

#### Infrastructure Layer
- **FHIR Client**: Handles all communication with Epic's FHIR API
- **JWT Authentication**: Manages OAuth 2.0 authentication with Epic
- **Configuration Management**: Centralizes configuration from environment variables and Foundry settings
- **Structured Logging**: Provides consistent logging throughout the application
- **Retry Utilities**: Implements retry logic for handling transient failures

#### Domain Layer - Bronze (Extract)
- **Resource Extractor**: Core component for extracting FHIR resources
- **Bronze Transform**: Stores raw FHIR resources without transformation
- **Resource-specific Extractors**: Specialized extractors for each FHIR resource type

#### Domain Layer - Silver (Transform)
- **Silver Transform**: Transforms raw resources into normalized data
- **Data Normalizer**: Flattens nested FHIR structures
- **Schema Enforcer**: Ensures data conforms to expected schemas

#### Domain Layer - Gold (Analytics)
- **Patient Timeline**: Creates patient-centric views across all data
- **Encounter Summary**: Aggregates encounter data for reporting
- **FHIR Analytics**: Uses Pathling for FHIR-specific analytics

#### Validation Layer
- **FHIR Validator**: Validates against FHIR specifications
- **Schema Validator**: Ensures schema conformance
- **Data Quality**: Implements data quality checks

## Workflow Process

### 1. Authentication & Connection
- JWT tokens are generated for secure authentication with Epic's API
- The system uses your Epic client ID and private key stored in Foundry's Secret Management

### 2. Bronze Layer (Extract)
- FHIR resources are extracted from Epic's API using resource-specific extractors
- Each resource type (Patient, Encounter, Condition, etc.) has its own extraction transform
- Resources are stored in raw form in Bronze datasets using Delta Lake format
- Watermarks track the last extraction time for incremental loading
- Extraction happens on a scheduled basis (daily, defined in foundry.yml)

### 3. Silver Layer (Transform)
- Raw FHIR resources are processed into normalized, structured formats
- Nested JSON structures are flattened for better query performance
- References between resources are standardized
- Common fields are normalized to consistent formats
- Schema validation ensures data quality
- Delta Lake tables provide versioning and time travel capabilities

### 4. Gold Layer (Analytics)
- Patient-centered analytics views are created
- Timeline generation aggregates events across resource types
- Specialized views for specific analytics use cases
- Integration with Pathling for FHIR-specific querying capabilities
- Optimized for performance and usability

### 5. Validation Process
- Validation runs at each layer to ensure data quality
- FHIR conformance validation against standard profiles
- Schema validation for structural correctness
- Business rule validation for semantic correctness
- Error records are captured and tracked for monitoring

## Implementation Details

### Codebase Organization

The codebase follows a modular structure:

- `transforms-python/src/epic_fhir_integration/` - Main package
  - `api_clients/` - Epic API client code
  - `bronze/` - Bronze layer extraction logic
  - `silver/` - Silver layer transformation logic
  - `gold/` - Gold layer analytics logic
  - `validation/` - Validation components
  - `utils/` - Shared utilities
  - `infrastructure/` - Infrastructure components
  - `domain/` - Domain-specific logic
  - `analytics/` - Analytics components
  - `application/` - Application-level components

### Transform Definitions

All transforms are defined in `foundry.yml`, which specifies:
- Transform names and descriptions
- Entry points into the Python code
- Schedule information (cron expressions)
- Input and output datasets
- Compute cluster configurations
- Configuration parameters

### Scheduling and Orchestration

- Bronze transforms run in sequence (Patient → Encounter → Condition → etc.)
- Silver transforms run after their corresponding Bronze transforms complete
- Gold transforms run after all required Silver transforms complete
- Scheduled via cron expressions in foundry.yml
- Default schedule: Bronze (1-5 AM), Silver (6-7 AM), Gold (8 AM)

### Data Storage

- All data stored in Delta Lake format
- Bronze layer: Raw JSON with minimal processing
- Silver layer: Normalized, flattened structures
- Gold layer: Optimized for analytics use cases
- All layers support:
  - Time travel (historical versions)
  - ACID transactions
  - Schema enforcement
  - Efficient upserts and deletes

### Error Handling

- Retry logic with exponential backoff for transient failures
- Circuit breakers for external dependencies
- Dead-letter datasets for failed records
- Structured logging for observability
- Validation errors are tracked separately for monitoring

## Development Workflow

### Local Development

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

3. Set up environment variables for local testing
4. Run tests with pytest
5. Use foundry-dev-tools to simulate Foundry transforms locally

### Deployment Process

1. Make code changes in the transforms-python directory
2. Test changes locally
3. Push changes to the Foundry repository
4. Build the repository in Foundry
5. Deploy transforms in order: Bronze → Silver → Gold

### Extending the Pipeline

#### Adding a New FHIR Resource Type

1. Create a new resource extractor in the bronze layer
2. Add transformation logic in the silver layer
3. Update gold layer analytics as needed
4. Add new transform definitions to foundry.yml
5. Create corresponding datasets in Foundry
6. Update tests to cover the new resource

#### Modifying an Existing Resource

1. Update the relevant extractor/transformer code
2. Ensure backward compatibility or handle schema evolution
3. Test thoroughly before deployment
4. Consider impacts on downstream gold layer datasets

## Configuration

### Secret Management

The following secrets must be configured in Foundry's Secret Management:

- `EPIC_CLIENT_ID`: Your Epic FHIR API client ID
- `EPIC_PRIVATE_KEY`: JWT private key for authentication
- `EPIC_BASE_URL`: Base URL for the Epic FHIR API

### Transform Configuration

Transforms can be configured via parameters in foundry.yml:
- `max_pages`: Maximum number of pages to extract (default: 100)
- `batch_size`: Number of resources per page (default: 200)
- Resource-specific configurations as needed

## Monitoring and Maintenance

### Key Metrics

- Extraction counts by resource type
- Processing time for each layer
- Error rates and types
- Validation failure rates
- Data freshness (time since last successful extraction)

### Common Issues and Troubleshooting

1. **Authentication Failures**:
   - Verify secrets in Foundry Secret Management
   - Check private key format (must be PEM)
   - Validate client ID is active in Epic

2. **Transform Failures**:
   - Check transform logs in Foundry
   - Verify datasets exist with correct permissions
   - Check for schema evolution issues

3. **Performance Issues**:
   - Review extraction batch sizes
   - Check for inefficient transformations
   - Monitor Spark cluster resource usage

## Performance Considerations

- Extraction is parallelized by resource type
- Silver transforms use efficient Spark operations
- Partitioning is used for large datasets
- Z-ordering optimizes common query patterns
- Incremental extraction reduces API load

## Security Considerations

- JWT authentication with Epic API
- Secrets stored in Foundry Secret Management
- PHI data protected according to Foundry security protocols
- Audit logging for all operations
- Role-based access control for datasets

## Best Practices

1. Always test locally before deploying to Foundry
2. Use incremental loading to minimize API usage
3. Validate data at each layer
4. Monitor transform performance and error rates
5. Document any schema changes
6. Follow Palantir's guidelines for production deployments

## Appendix

### Resource Type Support

The pipeline currently supports these FHIR resources:
- Patient
- Encounter
- Condition
- Observation
- MedicationRequest

### Technology Stack

- Palantir Foundry
- Delta Lake
- Apache Spark
- Python
- FHIR R4 Standard
- Pathling for FHIR Analytics 