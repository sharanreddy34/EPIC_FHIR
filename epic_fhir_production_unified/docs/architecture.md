# Epic FHIR Pipeline Architecture

This document describes the architecture of the Epic FHIR pipeline, including the data flow, component design, and integration with Palantir Foundry.

## Overview

The Epic FHIR pipeline is designed to extract FHIR resources from Epic's API, transform them into structured formats, and make them available for analytics and reporting. The pipeline follows the medallion architecture pattern, with Bronze, Silver, and Gold layers.

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Epic FHIR   │    │     Bronze     │    │     Silver    │    ┌───────────────┐
│     API       │───►│  Raw JSON Data │───►│  Structured   │───►│     Gold      │
│               │    │               │    │     Data      │    │  Analytics    │
└───────────────┘    └───────────────┘    └───────────────┘    └───────────────┘
       │                     │                    │                    │
       ▼                     ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  JWT Auth &   │    │ Delta Tables  │    │ FHIR Resource │    │  Timelines &  │
│  API Clients  │    │ Raw JSON +    │    │ Tables with   │    │  Patient-     │
│               │    │ Metadata      │    │ Schema        │    │  Centered Data│
└───────────────┘    └───────────────┘    └───────────────┘    └───────────────┘
```

## Key Components

### 1. API Integration Layer

- **JWT Authentication**: Secure communication with Epic's FHIR API using JWT tokens
- **FHIR Client**: Handles API interactions, pagination, error handling, and retries
- **Resource Extraction**: Pulls specific FHIR resource types from the API

### 2. Medallion Architecture

#### Bronze Layer
- **Purpose**: Extract and preserve raw data in its original form
- **Data Format**: Raw JSON stored in Delta tables with metadata
- **Key Features**:
  - Incremental loading with watermarks
  - Audit fields (ingest timestamp, date)
  - Resource type and ID extraction for partitioning

#### Silver Layer
- **Purpose**: Parse and normalize raw data into structured format
- **Data Format**: Structured Spark DataFrames with proper schemas
- **Key Features**:
  - FHIR-specific field extraction
  - Patient-resource linkage
  - Data quality validation
  - Pathling integration for FHIR-aware queries

#### Gold Layer
- **Purpose**: Create analytics-ready, business-oriented datasets
- **Data Format**: Optimized tables for specific use cases
- **Key Features**:
  - Patient timelines
  - Clinical metrics
  - Temporal relationships between events
  - Cohort identification

### 3. Validation & Quality Control

- **FHIR Validation**: Validate resources against FHIR schemas
- **Great Expectations**: Define and enforce data quality expectations
- **Custom Validators**: Domain-specific validation rules

## Technologies & Libraries

| Component | Technology/Library | Purpose |
|-----------|-------------------|---------|
| Core | Python 3.10+ | Main programming language |
| Data Processing | PySpark | Distributed data processing |
| FHIR Handling | fhir.resources | FHIR model validation and parsing |
| FHIR Queries | Pathling | FHIR-specific query engine |
| FHIR Path | fhirpathpy | FHIRPath execution engine |
| Authentication | PyJWT | JWT token handling |
| Data Quality | Great Expectations | Data validation framework |
| Data Storage | Delta Lake | ACID transactions on data lake |
| Orchestration | Foundry Transforms | Workflow management |

## Foundry Integration

### Transforms

The pipeline is implemented as a series of Foundry transforms, each handling a specific layer or resource type:

1. **Bronze Transforms**: One per resource type, extracting data from Epic API
2. **Silver Transforms**: Convert raw JSON to structured tables
3. **Gold Transforms**: Create analytics-ready views

### Secret Management

Sensitive credentials are stored in Foundry's Secret Management:
- Epic client ID
- Private key for JWT authentication
- API endpoints

### Datasets

Data flows through a series of datasets, organized by layer:
- `datasets/bronze/{ResourceType}_Raw_Bronze`
- `datasets/silver/{ResourceType}_Silver`
- `datasets/gold/{AnalyticsView}`

## Resource Flow Example

Here's how a Patient resource flows through the system:

1. **API to Bronze**:
   - JWT authentication with Epic
   - Patient resource extracted via FHIR API
   - Raw JSON saved to `Patient_Raw_Bronze` dataset

2. **Bronze to Silver**:
   - JSON parsed using fhir.resources
   - Patient demographics extracted
   - Structured data saved to `Patient_Silver` dataset

3. **Silver to Gold**:
   - Patient data combined with encounters, conditions, etc.
   - Timeline generated with clinical events
   - Analytics-ready view saved to `Patient_Timeline` dataset

## Deployment & Execution

The pipeline runs on Foundry's distributed computing infrastructure:
- **Scheduling**: Configurable via `foundry.yml`
- **Resource Allocation**: Small/medium/large compute clusters
- **Dependencies**: Managed via conda recipe

## Error Handling & Resilience

The pipeline includes comprehensive error handling:
- **Retries**: Automatic retry for transient errors
- **Circuit Breaking**: Protection against API overloading
- **Failure Isolation**: Resource-specific failures don't affect other resources
- **Logging**: Structured logging for debugging and monitoring

## Extensibility

The architecture is designed for extensibility:
- **New Resource Types**: Easy to add new FHIR resource types
- **Custom Transformations**: Add specialized silver/gold transforms
- **Validators**: Add custom validation rules

## Future Enhancements

Planned enhancements to the architecture:
- **Streaming Ingestion**: Real-time data ingestion for critical resources
- **FHIR Bulk Data API**: Support for bulk data extraction
- **ML Integration**: Feature extraction for machine learning models
- **Terminology Services**: Integration with FHIR terminology services 