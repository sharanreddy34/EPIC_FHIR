# Comprehensive Real-World Testing & Data Quality TODO List

This document outlines the tasks required to thoroughly test the advanced FHIR tools against real Epic FHIR API endpoints, focusing on data validation, quality, and preparation of "gold" tier outputs for LLM consumption.

**Patient ID for testing:** `T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB` (and others for diversity)

## I. Core Infrastructure & Configuration
-   [ ] **Verify API Credentials & Configuration:**
    -   [ ] Confirm `config/live_epic_auth.json` is accurate for the target Epic environment (sandbox/production).
    -   [ ] Ensure `secrets/private_key.pem` is the correct, secured key for JWT signing.
    -   [ ] Validate `epic_fhir_integration/config/settings.py` for correct base URLs, client IDs, and JWT issuers.
-   [ ] **Environment Sanity Checks:**
    -   [ ] Confirm network connectivity to all required Epic FHIR API endpoints.
    -   [ ] Verify versions and availability: Python 3.9+, Java 11+ (for Pathling), Node.js 14+ & Sushi (for FSH).
-   [ ] **Ethical & Compliance Approvals:**
    -   [ ] Re-confirm IRB approval status and scope for using real patient data.
    -   [ ] Review and ensure adherence to HIPAA compliance and data use agreements.
-   [ ] **Python Package & Dependencies:**
    -   [ ] Ensure `epic-fhir-integration` package is installed correctly (`pip install -e .`).
    -   [ ] Resolve any dependency conflicts (e.g., pandas, pydantic versions) noted during previous runs.
    -   [ ] Update `pyproject.toml` and `requirements.txt` if dependency changes are needed.

## II. Data Acquisition & Preparation for Testing
-   [ ] **Expand Test Patient Cohort:**
    -   [ ] Identify and document criteria for selecting a diverse set of test patients beyond the default ID (e.g., different ages, conditions, data completeness).
    -   [ ] Securely document test patient IDs.
-   [ ] **Enhance Data Fetching Scripts (e.g., `scripts/fetch_test_data.py`):**
    -   [ ] Ensure scripts can fetch a comprehensive set of FHIR resources for each test patient: Patient, Encounter, Observation (vitals, labs, social history), Condition, MedicationRequest, MedicationStatement, Procedure, AllergyIntolerance, Immunization, DiagnosticReport, DocumentReference.
    -   [ ] Implement robust error handling and retry mechanisms in fetching scripts.
    -   [ ] Ensure correct usage of `FHIRClient` (with `access_token`) in all data fetching scripts.
-   [ ] **Test Data Management:**
    -   [ ] Create versioned snapshots of fetched real-world test data for repeatable testing.
    -   [ ] Document the source, date, and scope of each data snapshot.
    -   [ ] Implement and verify de-identification procedures if using sensitive data for broader testing, ensuring LLM-ready outputs are appropriately de-identified. Store de-identified versions separately.

## III. Tiered Data Quality Strategy (Bronze, Silver, Gold)
-   [ ] **Define Clear Tier Criteria:**
    -   [ ] **Bronze:**
        -   [ ] Raw data as fetched from the source.
        -   [ ] Basic structural validation (FHIR R4 conformity).
        -   [ ] Minimal transformations, primarily for initial parsing and storage.
        -   [ ] Action: Ensure `patient.json` and other resources in `bronze/` reflect this.
    -   [ ] **Silver:**
        -   [ ] Bronze requirements +
        -   [ ] Data cleansing (e.g., handling missing values consistently, standardizing units where appropriate).
        -   [ ] Enrichment with initial, commonly required extensions (e.g., basic US Core extensions if applicable, but not full conformance).
        -   [ ] Improved coding: Ensure primary codes have recognized systems.
        -   [ ] Validation against an intermediary "silver" profile (to be defined).
        -   [ ] Action: Ensure `patient.json` in `silver/` reflects these enhancements.
    -   [ ] **Gold (LLM-Ready):**
        -   [ ] Silver requirements +
        -   [ ] Full conformance to specified target profiles (e.g., US Core, other IGs).
        -   [ ] Comprehensive data enrichment: All relevant extensions populated, terminology mapped to standard codesets.
        -   [ ] Data linked and referentially intact.
        -   [ ] Narrative generation reviewed/enhanced for human readability and LLM contextual understanding.
        -   [ ] De-identification verified if necessary for LLM use.
        -   [ ] Final validation against "gold" profiles.
        -   [ ] Action: Ensure `patient.json` in `gold/` is a pristine example for LLM input.
-   [ ] **Standardize Tier Representation:**
    -   [ ] Remove custom `_tier` attribute from FHIR resources.
    -   [ ] Use a standard FHIR extension (e.g., `http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier`) to denote Bronze, Silver, Gold. Update sample files.
-   [ ] **Implement Transformation Logic:**
    -   [ ] Develop/refine scripts for Bronze-to-Silver and Silver-to-Gold transformations.
    -   [ ] Ensure transformations are idempotent where possible.

## IV. Enhanced Validation Framework
-   [ ] **Develop Tier-Specific FHIR Profiles:**
    -   [ ] Create/obtain FSH or JSON profiles for Bronze (basic structure), Silver (enriched), and Gold (e.g., US Core compliant) tiers.
    -   [ ] Store these profiles in `epic_fhir_integration/profiles/`.
-   [ ] **Improve `FHIRValidator`:**
    -   [ ] Ensure it can load and validate against different profiles dynamically based on the tier.
    -   [ ] Enhance error reporting to be more specific and actionable.
    -   [ ] Verify `validator_cli.jar` downloading and path resolution.
-   [ ] **Implement Comprehensive Validation Tests (`test_validation_live.py` and new tests):**
    -   [ ] **Structural Validation:** Against base FHIR R4 for all tiers.
    -   [ ] **Profile Conformance:** Validate each tier against its respective profile (Bronze, Silver, Gold).
    -   [ ] **Terminology Validation:**
        -   [ ] Validate coded elements against specified ValueSets (e.g., using `$validate-code` or within the validator).
        -   [ ] Check for correct `system` URLs in `coding` elements.
    -   [ ] **Referential Integrity:**
        -   [ ] Check that resource references (e.g., `patient.reference`) resolve to existing resources within the test dataset.
        -   [ ] Test for orphaned resources.
    -   [ ] **Cardinality Checks:** Ensure min/max occurrences of elements are met per profiles.
    -   [ ] **Data Type Validation:** Stricter checking of data types (e.g., date, dateTime, boolean formats).
    -   [ ] **Business Rule Validation (Advanced):**
        -   [ ] Implement checks for logical consistency (e.g., birth date before encounter date).
        -   [ ] This might require custom validation logic or integrating FHIRPath assertions within profiles.
-   [ ] **Address Existing Validation Failures:**
    -   [ ] Investigate why Gold tier sample `patient.json` fails US Core Race Extension validation and correct the sample or validation logic.
    -   [ ] Ensure sample data for Observations, Conditions, Encounters in the Gold tier can pass their respective profile validations (e.g., by adding performers, categories, participants).

## V. Code Quality & Testability Refinements
-   [ ] **FHIRPathAdapter (`fhirpath_adapter.py`):**
    -   [ ] Fix `FHIRPath.__init__() missing 1 required positional argument: '_obj'` error. The current mock `MockFHIRPath` doesn't fully replicate the `fhirpath.FHIRPath()` instantiation or behavior. Investigate if the actual `fhirpath` library is being correctly invoked or if the mock needs refinement for test scenarios that don't use the real library.
    -   [ ] Ensure the adapter correctly uses the *actual* `fhirpath` library when available and falls back to a *robust* mock only when necessary for specific unit tests. The current mock is very basic.
-   [ ] **PathlingService (`pathling_service.py`):**
    -   [ ] Refine mock mode: Ensure `start()` method correctly sets `base_url` and allows mock operations even if Docker/Java components fail to initialize, preventing "Pathling server not configured" errors in test/mock modes.
    -   [ ] Ensure `import_data`, `aggregate`, `extract_dataset` mock implementations return data in the *exact format* expected by the calling test script (e.g., `patient_dataset.to_dict()` in `advanced_fhir_tools_e2e_test.py` implies `extract_dataset` should return an object with a `to_dict` method, possibly a pandas DataFrame).
-   [ ] **DataScience Tools (`fhir_dataset.py`):**
    -   [ ] Verify `FHIRDataset.to_pandas()` method is correctly implemented and used.
    -   [ ] Ensure `FHIRDatasetBuilder` and `CohortBuilder` mock implementations are sufficient for tests and clearly marked as stubs if `fhir-pyrate` is not a hard dependency for all test runs. If it *is* a dependency, ensure it's installed.
-   [ ] **Authentication Adapters (`advanced_fhir_tools_e2e_test.py`):**
    -   [ ] Review `get_auth_token` and `create_auth_header` adapter functions. Ensure they are robust and correctly handle various token formats or errors from underlying auth functions.
-   [ ] **Review All Test Scripts for Mocking Strategy:**
    -   [ ] Ensure tests that *should* hit the live API are configured to do so (`RUN_LIVE_API_TESTS=true`).
    -   [ ] Ensure tests that use mocks have comprehensive and accurate mocks.
    -   [ ] Minimize "false positives" where tests pass due to overly simplistic mocks.

## VI. Individual Component Testing (Enhancements)
-   [ ] **Authentication (`test_auth.py`, `jwt_auth.py`, `custom_auth.py`):**
    -   [ ] Test with expired tokens and ensure refresh logic works as expected.
    -   [ ] Test scenarios with invalid client ID, incorrect private key, or wrong JWT issuer.
    -   [ ] Verify `FHIRClient` instantiation is correct (using `access_token`) in any live auth tests.
-   [ ] **FHIRPath (`test_fhirpath_live.py`, `advanced_fhir_tools_e2e_test.py`):**
    -   [ ] Expand test cases to cover a wider range of FHIRPath functions and operators (aggregations, type casting, date functions, etc.) on real, diverse data.
    -   [ ] Test performance on large, multi-resource bundles.
-   [ ] **Pathling Analytics (`test_pathling_live.py`, `advanced_fhir_tools_e2e_test.py`):**
    -   [ ] Ensure tests use the *real* Pathling service (Docker or direct Java) for live tests, not just mocks.
    -   [ ] Test with more complex aggregation, grouping, and filtering expressions.
    -   [ ] Validate the structure and content of Pathling's output (DataFrames, JSON results).
-   [ ] **Data Science (`test_datascience_live.py`, `advanced_fhir_tools_e2e_test.py`):**
    -   [ ] Test with more complex cohort definitions and feature extractions using real data.
    -   [ ] Verify the output DataFrame schemas and content.
-   [ ] **FHIR Validation (`test_validation_live.py`, `advanced_fhir_tools_e2e_test.py`):**
    -   [ ] Test compilation of project-specific FSH files (`epic_fhir_integration/profiles/epic/*.fsh`).
    -   [ ] Validate real fetched data against these compiled custom profiles.
    -   [ ] Test validation against external IGs (e.g., US Core) by specifying them.

## VII. End-to-End Workflow Testing (Enhancements)
-   [ ] **Expand `test_e2e_live.py` or create new E2E tests for:**
    -   [ ] Bronze -> Silver -> Gold data transformation and validation pipeline for a set of diverse patients.
    -   [ ] Workflow: Fetch real data -> Transform to Gold -> Validate Gold -> Prepare for LLM (e.g., specific JSON structure, narrative summary).
    -   [ ] Test scenarios where intermediate steps fail and ensure the pipeline handles errors gracefully.

## VIII. LLM-Ready Gold Output Preparation & Validation
-   [ ] **Define LLM Input Schema for Gold Data:**
    -   [ ] Specify the exact JSON structure, key fields, and narrative components required by the target LLM.
    -   [ ] Consider if linked resources should be bundled or provided separately.
-   [ ] **Develop Transformation to LLM Schema:**
    -   [ ] Create scripts or refine Gold tier transformations to produce this LLM-specific output.
-   [ ] **Content Completeness for LLM Context:**
    -   [ ] Identify key data elements across linked resources that provide essential context for the LLM (e.g., patient history, problem list, recent procedures, medications for a given encounter).
    -   [ ] Ensure these are present and accurate in the Gold output.
-   [ ] **Narrative Quality:**
    -   [ ] If using FHIR resource narratives, ensure they are well-generated, human-readable, and provide good summaries.
    -   [ ] Consider generating custom summaries tailored for LLM consumption if default narratives are insufficient.
-   [ ] **De-identification and Privacy for LLM:**
    -   [ ] Implement/verify robust de-identification for Gold outputs intended for LLMs, especially if not in a secure, private LLM environment.
-   [ ] **Validation for LLM Readiness:**
    -   [ ] Create validation rules (e.g., JSON schema, custom checks) to ensure Gold outputs meet the LLM input requirements.
    -   [ ] Test with a sample LLM interaction if possible.

## IX. Test Execution, Reporting, & Automation
-   [ ] **Refine `run_real_world_tests.sh`:**
    -   [ ] Ensure it can selectively run tests against different tiers of data (Bronze, Silver, Gold).
    -   [ ] Add options to run validation against specific profiles.
-   [ ] **Enhance `generate_test_report.py`:**
    -   [ ] Include detailed data quality metrics per tier in the report.
    -   [ ] Summarize validation pass/fail rates against specific profiles (Base FHIR, Silver, Gold, US Core).
    -   [ ] Report on LLM-readiness checks.
-   [x] **Dashboard Generation:**
    -   [x] Add automatic generation of quality and validation dashboards from test results.
    -   [x] Generate interactive web-based visualizations of data quality metrics.
    -   [x] Create visual representations of validation results and issues.
-   [ ] **CI/CD Integration:**
    -   [ ] Plan for integrating these tests (especially non-live, snapshot-based ones) into a CI/CD pipeline.
    -   [ ] Automate report generation, dashboard creation, and alerting for regressions.

## X. Documentation
-   [ ] **Update `ADVANCED_FHIR_TOOLS.md`:** Reflect actual capabilities and fixed mocks.
-   [ ] **Update `REAL_WORLD_TESTING.md`:** Point to this new TODO list and incorporate finalized tier definitions and validation strategies.
-   [ ] **Create/Update `DATA_QUALITY_STRATEGY.md`:** Detail the Bronze/Silver/Gold tier definitions, transformation rules, and validation criteria.
-   [ ] **Create/Update `LLM_INPUT_PREPARATION.md`:** Document the schema and preparation steps for making Gold data LLM-ready.
-   [x] **Update `CODEBASE_REVIEW.md`:** Include the dashboard implementation documentation for both quality and validation components.
-   [x] **Document Dashboard Usage:** Add dashboard generation and usage instructions to testing guides.

This list will be used to track progress towards a robust, real-world testing environment for the FHIR integration project.