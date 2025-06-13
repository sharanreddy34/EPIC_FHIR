# ADR-0001: Use Layered Architecture for FHIR Pipeline

## Status

Accepted

## Date

2023-11-15

## Context

We need to design a robust architecture for processing FHIR data from Epic's API. The system needs to:

1. Extract raw FHIR resources from Epic APIs
2. Transform them into analytics-ready formats
3. Support multiple downstream use cases
4. Maintain data lineage and reproducibility
5. Handle the complex, nested nature of FHIR resources

## Decision

We will implement a layered architecture following the medallion pattern with Bronze, Silver, and Gold layers:

- **Bronze Layer**: Store raw, immutable FHIR resources exactly as received
- **Silver Layer**: Normalize and clean data with standardized schemas
- **Gold Layer**: Create purpose-specific, analytics-ready data models

Additionally, we will create a clear separation between:

- **Infrastructure Layer**: Cross-cutting concerns like API clients, authentication, configuration, and logging
- **Domain Layer**: Business logic specific to FHIR processing
- **Validation Layer**: Data quality checks at each layer

## Consequences

### Positive

- **Separation of Concerns**: Each layer has a specific responsibility
- **Data Lineage**: Clear path from source to consumption
- **Reproducibility**: Raw data is preserved, allowing reprocessing when needed
- **Independent Evolution**: Layers can evolve independently
- **Optimized Access Patterns**: Gold layer can be optimized for specific query patterns
- **Error Isolation**: Failures in one layer don't affect others

### Negative

- **Storage Duplication**: Data is stored multiple times across layers
- **Processing Overhead**: Multiple transformations required to reach final format
- **Increased Complexity**: More moving parts to manage

## Implementation Details

### Package Structure

```
epic_fhir_integration/
├── infrastructure/   # Cross-cutting concerns
│   ├── api_clients/  # FHIR API clients
│   └── config/       # Configuration management
├── domain/           # Core business logic
│   ├── bronze/       # Raw data extraction
│   ├── silver/       # Data normalization
│   ├── gold/         # Analytics-ready models
│   ├── schemas/      # Data schemas
│   └── validation/   # Validation logic
└── utils/            # Shared utilities
```

### Data Flow

1. API Clients extract FHIR resources → Bronze Delta tables
2. Bronze resources are normalized → Silver Delta tables
3. Silver data is aggregated and enriched → Gold Delta tables

## Alternatives Considered

1. **Single-layer Architecture**: Extracting and transforming in one step
   - Rejected due to lack of data lineage and reproducibility

2. **Streaming Architecture**: Real-time processing of FHIR events
   - Deferred to future iterations due to complexity and current batch-oriented needs

3. **Microservice Architecture**: Separate services for each resource type
   - Rejected due to operational complexity and fragmentation of the data pipeline

## References

- [Delta Lake Architecture](https://docs.delta.io/latest/delta-intro.html)
- [Medallion Architecture](https://databricks.com/glossary/medallion-architecture)
- [FHIR Data Processing Best Practices](https://hl7.org/fhir/implementationguide.html) 