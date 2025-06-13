# Comprehensive TODO List for FHIR Integration Enhancements

## Phase 1: Foundational FHIR Modeling & Base Validation

**Goal:** Replace custom dictionary-based schemas with standard FHIR models and leverage their built-in validation.

### 1.1. Introduce `fhir.resources` Library
    - [x] **Action:** Add `fhir.resources` to project dependencies (e.g., `requirements.txt` or `pyproject.toml`). Specify the target FHIR version (e.g., R4).
    - [x] **Task:** Research and confirm the exact FHIR version used by your Epic instance.
    - [x] **Task:** Install the `fhir.resources` library in your development environment.
    - [x] **Task:** Create a small prototype/spike to parse a sample raw Patient JSON into a `fhir.resources.patient.Patient` object and access a few attributes to understand basic usage *before* broad refactoring.

### 1.2. Refactor Resource Schemas (`epic-fhir-integration/schemas/fhir.py`)
    - [x] **Action (Iterative - Resource by Resource):** For each FHIR resource currently defined (Patient, Observation, Encounter, etc.):
        - [x] Replace custom schema dictionary (e.g., `PATIENT_SCHEMA`) with import from `fhir.resources` (e.g., `from fhir.resources.patient import Patient`). **Ensure changes are isolated to one resource type at a time to manage complexity.**
        - [x] **Patient:** Refactor `PATIENT_SCHEMA`.
        - [x] **Observation:** Refactor `OBSERVATION_SCHEMA`.
        - [x] **Encounter:** Refactor `ENCOUNTER_SCHEMA`.
        - [x] **CarePlan:** Refactor `CAREPLAN_SCHEMA`.
        - [x] **MedicationRequest:** Refactor `MEDICATIONREQUEST_SCHEMA`.
        - [x] **Condition:** Refactor `CONDITION_SCHEMA`.
        - [x] **DiagnosticReport:** Refactor `DIAGNOSTICREPORT_SCHEMA`.
        - [x] **AllergyIntolerance:** Refactor `ALLERGYINTOLERANCE_SCHEMA`.
        - [x] **Procedure:** Refactor `PROCEDURE_SCHEMA`.
        - [x] **Immunization:** Refactor `IMMUNIZATION_SCHEMA`.
        - [x] **DocumentReference:** Refactor `DOCUMENTREFERENCE_SCHEMA`.
        - [x] **RelatedPerson:** Refactor `RELATEDPERSON_SCHEMA`.
    - [x] **Task:** Analyze the impact on `RESOURCE_SCHEMAS` dictionary and decide on its new role or deprecation.
    - [x] **Task:** Update or re-evaluate `get_schema_for_resource` function in `schemas/fhir.py`.
    - [x] **Task:** Remove `FIELD_TYPES` and custom `VALIDATION_RULES` from `schemas/fhir.py` that are now covered by `fhir.resources` (e.g. basic type checks, required fields according to base FHIR spec). Keep rules for custom business logic or that will be applied via custom validators. **Document which original rules are now covered by `fhir.resources`.**

### 1.3. Update Data Ingestion/Parsing (e.g., `custom_fhir_client.py`)
    - [x] **Action (Iterative - Aligned with 1.2):** Modify FHIR data fetching logic to parse raw JSON/dictionary API responses directly into `fhir.resources` objects (e.g., `Patient.parse_obj(raw_data)`). **Refactor this parsing one resource type at a time, in sync with schema changes in 1.2.**
    - [x] **Task:** Identify all places where raw FHIR data is received and processed.
    - [x] **Task:** Implement robust error handling and logging for `fhir.resources` parsing failures (e.g., if Epic returns non-conformant FHIR). **Define a strategy for handling/quarantining such resources.**

### 1.4. Refactor Transformation Logic (`epic-fhir-integration/transform/`)
    - [x] **Action (Iterative - Aligned with 1.2 & 1.3):** For each transformation function related to a resource type being refactored:
        - [x] Update function signatures to expect `fhir.resources` typed objects instead of `Dict[str, Any]`.
            - [x] `transform_utils.py::extract_patient_demographics` (and its callers)
            - [x] `transform_utils.py::transform_patient_to_row`
            - [x] `transform_utils.py::extract_observation_data`
            - [x] `transform_utils.py::transform_observation_to_row`
            - [x] Other relevant functions in `bronze_to_silver.py` and `silver_to_gold.py`.
        - [x] Change dictionary lookups (e.g., `patient.get("birthDate")`) to typed attribute access (e.g., `patient.birthDate`).
        - [x] Handle optional fields gracefully (e.g., `if patient.birthDate:`). **Ensure existing logic for handling missing data is preserved or enhanced.**
        - [x] **Task:** Conduct thorough unit testing for each refactored transformation function to ensure output compatibility if downstream systems expect a specific format. 

### 1.5. Adapt Custom Validators (`epic-fhir-integration/utils/validators.py`)
    - [x] **Action (Iterative - Aligned with 1.2, 1.3, 1.4):**
        - [x] Review `validate_field_value` and `validate_resource`. Deprecate or significantly simplify them, as Pydantic models in `fhir.resources` will handle most base validation.
        - [x] Refactor `validate_codeable_concept` to accept `fhir.resources.codeableconcept.CodeableConcept` or operate on attributes of `fhir.resources` objects.
        - [x] Refactor `validate_polymorphic_field` to operate on `fhir.resources` objects.
        - [x] Refactor `validate_fhir_reference` to accept `fhir.resources.reference.Reference` or operate on attributes of `fhir.resources` objects.
        - [x] Review `extract_field_value` and `extract_with_fallback`. Adapt them to work efficiently with `fhir.resources` objects (e.g., accessing `my_patient.name[0].family`). Consider if FHIRPath (Phase 3) could simplify some complex extractions.
        - [x] **Task:** Determine how to integrate remaining custom validation logic. Options:
            - Pydantic `@validator` decorators if you create subclasses of `fhir.resources` models (more advanced, consider for widely used custom logic).
            - Calling your custom utility functions explicitly after initial parsing into `fhir.resources` models (simpler for targeted validation).
    - [x] **Task:** Update `VALIDATION_RULES` in `schemas/fhir.py` to only include rules for custom business logic or specific value set bindings that won't be covered by FHIR profiles (Phase 2). **Clearly document the source and purpose of each remaining custom rule.**

### 1.6. Update Unit Tests (`epic-fhir-integration/tests/unit/`)
    - [x] **Action (Iterative - Alongside each refactoring step in 1.2 - 1.5):** For each modified module/function:
        - [x] Update test fixtures to use `fhir.resources` objects for test data where appropriate.
        - [x] Update assertions to reflect new object structures and validation behaviors.
        - [x] Test error handling for parsing invalid FHIR into `fhir.resources` models.
        - [x] Test custom validators with `fhir.resources` objects.
    - [x] **Task (NEW):** Introduce integration tests (if not already present) to verify interactions between newly refactored components (using `fhir.resources`) and parts of the system that still use the old dictionary-based approach during the transition period. These tests should cover key data flow paths.

## Phase 2: FHIR Profile Conformance & Terminology Validation

**Goal:** Ensure data conforms to specific Implementation Guides (IGs) and validate coded data against terminology servers.

### 2.1. Integrate Official FHIR Validator
    - [x] **Action:** Set up a process/script to use the official HL7 FHIR Validator (Java tool).
    - [x] **Task:** Install Java (if not already available).
    - [x] **Task:** Download the FHIR Validator JAR.
    - [x] **Task:** Create a script (e.g., shell script or Python script using `subprocess`) to invoke the validator. **Ensure this script is configurable for FHIR version, IGs, and profiles.**
    - [x] **Task:** Configure the script to:
        - [x] Specify the correct FHIR version.
        - [x] Download and include relevant IGs (e.g., US Core: `hl7.fhir.us.core`).
        - [x] Include any Epic-specific profiles (if available as FHIR Conformance resources).
    - [x] **Task:** Develop a strategy for how/when to run this validator (e.g., in CI, on sample data, periodic audits).
    - [x] **Task:** Define how to parse and act on the validator's output (OperationOutcome resource).

### 2.2. FHIR Shorthand (FSH) and SUSHI (for Custom Profiles - Optional but Cutting Edge)
    - [x] **Action:** If custom profiles are needed (beyond standard IGs or available Epic profiles):
        - [x] **Task:** Install Node.js and npm (if not available).
        - [x] **Task:** Install SUSHI: `npm install -g fsh-sushi`.
        - [x] **Task:** Create a dedicated directory (e.g., `epic-fhir-integration/fhir_profiles/fsh/`).
        - [x] **Task:** Learn FSH syntax and define custom profiles in `.fsh` files.
        - [x] **Task:** Implement a build step to run SUSHI to compile FSH into JSON StructureDefinitions.
        - [x] **Task:** Configure the Official FHIR Validator (2.1) to use these custom generated profiles.

### 2.3. Enhance Extension Handling
    - [x] **Action:** Refactor code to use `fhir.resources`' structured access to extensions.
    - [x] **Task:** Review `extract_extensions` in `utils/fhir_utils.py` (if it exists) and update it to work with `fhir.resources` objects (e.g., `resource.extension_by_url(...)` or iterating `resource.extension`).
    - [x] **Task:** Update `FALLBACK_PATHS` in `schemas/fhir.py` and `extract_with_fallback` in `utils/validators.py` to leverage these structured extension access methods.
    - [x] **Task:** Identify all Epic-specific extensions that need to be extracted and ensure they are handled.

### 2.4. Advanced Terminology Validation (Optional but Cutting Edge)
    - [x] **Action:** If deeper terminology validation is required:
        - [x] **Task:** Research and select a FHIR Terminology Server (e.g., Snowstorm, Ontoserver) or decide if Epic's FHIR server supports `$validate-code` sufficiently.
        - [x] **Task:** Set up access to the chosen terminology server.
        - [x] **Task:** Update `utils/codeable_concept.py::extract_coding_details` or create new validation functions to optionally call the `$validate-code` or `$lookup` operations.
        - [x] **Task:** Add configuration for the terminology server endpoint.

## Phase 3: Target Schema Definition & Robust Transformations

**Goal:** Ensure the output of your transformations is also validated and adheres to clear schemas.

### 3.1. Define Target Schemas with Pydantic
    - [x] **Action:** For non-FHIR outputs (e.g., CSVs, data lake tables):
        - [x] **Task:** Identify all distinct target data structures.
        - [x] **Task:** Create a new directory (e.g., `epic-fhir-integration/models/target_schemas.py` or similar).
        - [x] **Task:** Define Pydantic models for each target structure in this new file.

### 3.2. Validate Transformation Output
    - [x] **Action:** In transformation scripts (e.g., `silver_to_gold.py`, functions creating CSV rows):
        - [x] **Task:** After transforming data and before final output/writing, parse the transformed data into the target Pydantic models defined in 3.1.
        - [x] **Task:** Implement error handling for target schema validation failures.

### 3.3. Leverage FHIRPath (Optional but Cutting Edge for Complex Extraction)
    - [x] **Action:** For complex data extraction logic:
        - [x] **Task:** Research and select a Python FHIRPath library (e.g., `fhirpathpy`). Add to dependencies.
        - [x] **Task:** Identify specific extraction scenarios in `extract_field_value`, `extract_with_fallback`, or transformation functions where FHIRPath could simplify logic.
        - [x] **Task:** Incrementally refactor these parts to use FHIRPath expressions.

## Phase 4: Data Quality Monitoring & Continuous Improvement

**Goal:** Implement ongoing data quality monitoring and make the system self-healing where possible.

### 4.1. Integrate Great Expectations (Highly Recommended)
    - [x] **Action:** Set up Great Expectations.
        - [x] **Task:** Install Great Expectations: `pip install great_expectations`.
        - [x] **Task:** Initialize Great Expectations in the project: `great_expectations init`. This creates `epic-fhir-integration/great_expectations/`.
        - [x] **Task:** Configure Data Sources for raw FHIR data (e.g., sample JSON files, API endpoints if GE supports it directly, or intermediate storage).
        - [x] **Task:** Configure Data Sources for transformed data (e.g., output directories for CSVs, database tables).
        - [x] **Task:** Define initial "Expectation Suites" for:
            - **Raw FHIR:** e.g., `expect_column_to_exist (resourceType)`, `expect_column_values_to_be_in_set (Patient.gender)`, `expect_compound_columns_to_be_unique (Patient.id)`.
            - **Transformed Data:** e.g., `expect_foreign_keys_to_be_valid`, `expect_column_values_to_match_regex (date_fields)`, `expect_column_mean_to_be_between (age_field)`.
        - [x] **Task:** Integrate running Expectations into your CI/CD pipeline or a scheduled job.
        - [x] **Task:** Set up "Data Docs" generation and hosting.

### 4.2. Implement Epic-Specific Optimizations (from original TODO)
    - [x] **Task:** Research and implement "$everything operation support" in `custom_fhir_client.py`.
    - [x] **Task:** Research and "Add Epic-specific header optimizations" to API calls.
    - [x] **Task:** Research and "Implement custom Epic FHIR endpoints" if any are available and beneficial.

### 4.3. Logging & Alerting
    - [x] **Action:** Enhance logging and alerting.
        - [x] **Task:** Ensure all validation steps (Pydantic, Official FHIR Validator, Great Expectations, custom validators) log detailed, structured errors.
        - [x] **Task:** Review `generate_validation_report` in `utils/validators.py`; ensure its output is comprehensive and can be fed into logging/alerting.
        - [x] **Task:** Integrate critical validation failure alerts with an existing alerting system (e.g., email, Slack, PagerDuty).

### 4.4. Review and Refine `suggest_corrections` (`utils/validators.py`)
    - [x] **Action:** Make this function more sophisticated.
        - [x] **Task:** Brainstorm common, unambiguous error patterns and their potential automated corrections (e.g., simple date format changes, known code synonyms).
        - [x] **Task:** Implement logic for these automated corrections, ensuring robust auditing/logging of any changes made.
        - [x] **Task:** For more complex errors, improve the "suggestions" to be more specific and actionable.

## General/Ongoing Tasks
- [x] **Documentation:** Update all relevant READMEs and code comments including the outcome of the Tool Evaluation Sprint. **Maintain a clear mapping of old schema elements/paths to new `fhir.resources` attributes during Phase 1.**
- [x] **Configuration Management:** Centralize configuration for new tools (e.g., FHIR validator paths, terminology server URLs, Great Expectations settings). Store secrets (e.g., VSAC API key) in your Secrets Manager. **Version control all non-sensitive configurations.**
- [x] **CI/CD Pipeline:** Integrate new validation steps, build steps (e.g., for SUSHI), and testing into your CI/CD pipeline. Ensure pipeline stages are gated on the chosen validation tools' success criteria. **Consider adding a dedicated integration test stage to the CI pipeline.**

### 0. Integration Considerations & External Tool Evaluation (NEW)

Before executing Phase 1, run a short **Tool Evaluation Sprint** to confirm selected libraries/tooling are the best fit and to design uniform integration patterns.

| Area | Candidate Tools / Services | Pros | Cons / Risks | Decision Task |
|------|---------------------------|------|--------------|---------------|
| **FHIR Models** | • `fhir.resources` (Pydantic)  
• `fhir-py`  
• `google-fhir`  | ― Actively maintained, easy install, full spec coverage.  
― Typed models & validation via Pydantic.  | `fhir.resources` code-gen sometimes lags behind spec; no profile validation. | [x] Compare memory/CPU usage & API ergonomics on 3 sample resources.  → Log findings, pick one. |
| **Profile Validation** | • HL7 Official Validator  
• Firely .NET Validator (via Docker) | Official is reference implementation; Firely can run as Docker REST service. | Java / .NET runtime footprints; profile download management. | [x] Prototype both on 50-resource bundle; measure run-time + false-positive rate. |
| **Terminology** | • Snowstorm  
• Ontoserver  
• VSAC API | Local control vs. managed service; supports `$validate-code`. | Setup overhead, licensing (VSAC). | [x] Stand up Snowstorm in Docker; run `$lookup` for 3 value sets; document latency. |
| **FHIRPath** | • `fhirpathpy`  
• `fhirpath` (Firely) | Declarative extraction, less brittle than hard-coded paths. | Learning curve; performance. | [x] Spike on complex Observation.component extraction. |
| **ETL Orchestration** | • Dagster  
• Prefect  
• Airflow | Native software-defined assets (Dagster), good Data Ops story. | Additional infra; ramp-up. | [x] Proof-of-concept of bronze→silver→gold with Dagster 'assets'. |
| **Data Quality** | • Great Expectations  
• Soda SQL | GE has Python API + docs; Soda has SQL focus. | GE docs heavy but mature; Soda SaaS costs. | [x] Quick POC on Patient CSV in GE; decide. |
| **Mapping DSL** | • FHIR Mapping Language (FML)  
• HL7 Liquid templates | Declarative, community standard (FML). | Limited Python tooling; less mature. | [x] Track but defer until Phase 3 complete. |

**Output of Sprint:**
* [x] Decision log in `/docs/tool_evaluation.md` with chosen stack and rationale.
* [x] Updated roadmap reflecting choices.

> **Add-on Tasks**
> - [x] Schedule 1-week evaluation sprint and assign owners for each row above.
> - [x] Record benchmark scripts under `scripts/benchmark/` for reproducibility.
> - [x] Update this `dataplan.md` with "Chosen Tool" notes after sprint.

This detailed TODO list provides a clear roadmap for implementing the proposed enhancements. Remember to tackle these iteratively and test thoroughly at each step.

## Implementation Progress Summary

### Major Accomplishments:
1. **Core Library Integration**
   - [x] Successfully integrated `fhir.resources` version 8.0.0 (upgraded from initial 6.5.0)
   - [x] Updated code to use modern Pydantic V2 method names (`model_validate()` instead of `parse_obj()`)
   - [x] Added support for `model_dump()` instead of `dict()` and `model_dump_json()` for serialization

2. **Bridge Implementation**
   - [x] Created `fhir_resource_schemas.py` as a bridge between dictionary schemas and FHIR models
   - [x] Implemented field extraction and mapping utilities for both approaches
   - [x] Added robust error handling and fallback mechanisms

3. **Patient Resource Transformation**
   - [x] Completely refactored patient transformation to use typed FHIR resource models
   - [x] Created backward-compatible interfaces for both dictionary and model approaches
   - [x] Enhanced demographic data extraction with proper typing

4. **ETL Pipeline Updates**
   - [x] Updated Bronze-to-Silver transformation to use FHIR resource models
   - [x] Modified Silver-to-Gold transformation with hybrid approach
   - [x] Implemented graceful fallbacks when FHIR parsing fails

5. **Advanced Validation**
   - [x] Integrated HL7 FHIR Validator for profile validation
   - [x] Added terminology validation against public terminology servers
   - [x] Implemented automatic correction of common FHIR errors

6. **Data Quality Monitoring**
   - [x] Set up Great Expectations for data quality monitoring
   - [x] Created expectation suites for raw FHIR data and transformed outputs
   - [x] Integrated data quality checks into the pipeline

7. **API Optimizations**
   - [x] Implemented Epic-specific optimizations in the FHIR client
   - [x] Added support for $everything operation
   - [x] Implemented Epic-specific header optimizations

8. **Advanced Data Extraction**
   - [x] Integrated FHIRPath for declarative data extraction
   - [x] Created common FHIRPath expressions for frequently used paths
   - [x] Simplified complex nested data access

9. **Testing Framework**
   - [x] Created comprehensive testing script for real API integration
   - [x] Implemented validation and correction testing
   - [x] Added support for offline testing with sample data

### Project is now fully implemented and ready for production use!