Implementation Plan for FHIR Transformation Enhancements

**Phase 1: Core Validation, Enhanced Data Ingestion & Initial Quality Framework (Days 1-10)**
*   **High Priority**
    *   Update `validation/validator.py` to fully utilize HAPI FHIR validator.
    *   Add support for profile-based validation (using HAPI FHIR).
    *   Implement batch validation methods (HAPI FHIR).
    *   Ensure R4 base validation works properly (HAPI FHIR).
    *   Create `metrics/great_expectations_validator.py`: Implement validation adapters for FHIR data using Great Expectations.
    *   Add core expectations for common resource types (e.g., Patient, Observation) in `metrics/expectations/`.
    *   Enhance `scripts/fetch_patient_data.py`:
        *   Implement support for bulk FHIR API operations (e.g., `_count`, bundle pagination).
        *   Allow configurable FHIR server endpoints, authentication methods, and request parameters.
        *   Add a robust validation step after data fetching, utilizing both HAPI FHIR and Great Expectations.
        *   Include comprehensive validation results and summaries in the output metadata.
    *   Create `schemas/validation_config.py`: Define a schema for configuring validation (e.g., profiles to use, specific rulesets, Great Expectations suite parameters).
    *   `metrics/data_quality.py` (Initial Setup):
        *   Define the structure for a `DataQualityAssessor` class.
        *   Implement initial methods to calculate basic quality metrics derived from HAPI FHIR and Great Expectations validation outputs (e.g., conformance rates, missing field counts).
*   **Medium Priority**
    *   Create profile registry in `profiles/registry.py` to manage FHIR profiles.
    *   Map resource types to appropriate profiles, supporting tier-specific profiles (Bronze/Silver/Gold).
    *   Create validation utilities for Bronze data: `validate_bronze_resources(resources, output_dir)` function.
    *   Add validation summary reporting in `metrics/validation_metrics.py` (can be consumed by `DataQualityAssessor`).
*   **Low Priority**
    *   Create CLI command for on-demand validation in `cli/validation_commands.py` (for validating existing data directories).

**Phase 2: Pathling Analytics & Integrated Quality Checks (Days 11-18)**
*   **High Priority**
    *   Enhance `analytics/pathling_service.py` implementation:
        *   Add extraction methods for transformations.
        *   Implement resource loading from files/directories.
    *   Create `transform/pathling_transformer.py`:
        *   Add methods to transform resources using Pathling.
        *   Support bulk transformations.
    *   Update `transform/bronze_to_silver.py`:
        *   Replace custom FHIRPath with Pathling queries.
        *   Add standardized coding extraction.
        *   Integrate validation checkpoints using HAPI FHIR and Great Expectations before and after Pathling transformations.
    *   Enhance `metrics/data_quality.py`:
        *   Implement methods for quality dimensions relevant to Bronze-to-Silver transformations (e.g., terminology conformance, data type validation post-transformation).
        *   Integrate `DataQualityAssessor` into `scripts/transform_bronze_to_silver.py` for automated quality reporting.
*   **Medium Priority**
    *   Add extraction patterns for common resource types in `analytics/extraction_patterns.py` (e.g., Patient, Observation, Condition).
    *   Implement caching mechanism in `analytics/pathling_service.py` for repeated transformations (support disk-based caching).
*   **Low Priority**
    *   Create benchmarking tools in `tests/perf/pathling_benchmark.py` to compare Pathling performance with existing implementation.

**Phase 3: FHIR-PYrate & Comprehensive Quality Reporting System (Days 19-28)**
*   **High Priority**
    *   Enhance `datascience/fhir_dataset.py` implementation:
        *   Add dataset building capabilities.
        *   Support feature extraction from FHIR resources.
    *   Create cohort building utilities in `datascience/cohort_builder.py`:
        *   Add methods to define patient cohorts.
        *   Support temporal cohort definitions.
    *   Update `transform/silver_to_gold.py`:
        *   Replace custom PySpark transformations with FHIR-PYrate.
        *   Implement standardized feature extraction.
        *   Integrate validation checkpoints using Great Expectations suites tailored for Gold data.
    *   Comprehensive `metrics/data_quality.py` and Reporting:
        *   Implement methods for all planned quality dimensions, including consistency, uniqueness, and longitudinal integrity.
        *   Create JSON schema for quality reports in `schemas/quality_report.py`, defining a comprehensive report structure.
        *   Implement full quality reporting in `scripts/transform_silver_to_gold.py`.
    *   Create detailed expectation suites for each data tier (Bronze, Silver, Gold) in `metrics/expectations/` (e.g., `bronze_suite.json`, `silver_suite.json`, `gold_suite.json`).
*   **Medium Priority**
    *   Add dataset utilities for common analytics in `datascience/dataset_utilities.py` (e.g., dataset normalization).
    *   Implement dataset export functions in `io/dataset_io.py` (Support CSV, Parquet, Delta formats).
    *   Implement validation data stores in `metrics/validation_store.py` to track Great Expectations validation results over time.
*   **Low Priority**
    *   Create example notebooks in `examples/notebooks/` for data science workflows, including common analysis patterns.

**Phase 4: Advanced Customization, Alerting & Dashboards (Days 29-35)**
*   **High Priority**
    *   Implement a system for parameterizing transformations: Allow customization of Pathling queries, FHIR-PYrate feature extraction logic, and other transformation parameters via configuration files.
    *   Implement alerts for quality degradation in `metrics/quality_alerts.py`: Add threshold-based alerting based on tracked quality metrics.
*   **Medium Priority**
    *   Design and begin implementation of a pluggable architecture to allow for custom transformers and validators to be easily integrated.
    *   Add historical tracking of quality metrics in `metrics/quality_tracker.py`: Support comparison with previous runs.
*   **Low Priority**
    *   Create validation dashboard utilities in `metrics/dashboard/` to support visualization of validation results.
    *   Create quality dashboard generator in `metrics/dashboard/quality_dashboard.py` for interactive quality reports.

**Integration Strategy Notes**
*   Minimize code changes: Use adapter pattern to maintain backward compatibility where possible.
*   Incremental testing: Test each component and integration point thoroughly.
*   Documentation first: Update or create documentation alongside development.
*   **Configuration driven**: Emphasize external configuration for FHIR endpoints, validation profiles, transformation parameters, and tool selection.
*   Fallback mechanisms: Provide fallbacks for external tool integrations where feasible.

**First Week Priority Tasks (Revised)**
1.  Set up HAPI FHIR validator within the `validation` module and test R4 base validation.
2.  Set up the Great Expectations framework: install, initialize, create `metrics/great_expectations_validator.py`, and define initial expectations for Patient and Observation resources.
3.  Enhance `scripts/fetch_patient_data.py` for bulk data retrieval (paging) and basic configurability (endpoint).
4.  Integrate an initial validation step (HAPI + GE) into `fetch_patient_data.py`.
5.  Define the initial `DataQualityAssessor` class structure and basic metric calculations in `metrics/data_quality.py`.
6.  Begin implementation of `analytics/pathling_service.py`.

This implementation plan provides a structured approach to enhance the FHIR transformation pipeline while preserving compatibility with the existing codebaf.