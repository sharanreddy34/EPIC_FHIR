# A-TO-Z MODULAR TRANSFORM BLUEPRINT - TODO LIST
=================================================

This todo list is organized to match our blueprint structure, with priority indicators:
- 🔴 Critical: Blocking issues that must be fixed for MVP
- 🟠 High: Required for production readiness
- 🟡 Medium: Important for robustness and scalability
- 🟢 Low: Optimization and future-proofing

## 1. Generic Engine
-------------------
- 🔴 **BaseTransformer Implementation**
  - [x] Create `transforms/base.py` with abstract methods and hooks
  - [x] Implement normalizer methods with pre/post hooks
  - [x] Add data loss tracking metrics

- 🔴 **YAML Mapper Engine**
  - [x] Create `transforms/yaml_mappers.py`
  - [x] Implement `apply_mapping()` function for DataFrame transformation
  - [x] Add `_fhir_get()` helper with dot-notation & array index support
  - [x] Support fallback to `None` for missing paths

- 🟠 **Enhanced Path Resolution**
  - [x] Extend path resolution to support FHIR expressions (`[?system='...']`)
  - [x] Add array filtering based on attribute values
  - [x] Create unit tests for path resolution edge cases

- 🔴 **Transform Registry**
  - [x] Create `transforms/registry.py`
  - [x] Implement `get_transformer()` to find custom or build generic
  - [x] Add resource type validation

## 2. Pipeline Driver Refactoring
--------------------------------
- 🔴 **Transform Load Refactoring**
  - [x] Edit `pipelines/transform_load.py` to use registry
  - [x] Implement metrics collection within transform process
  - [x] Add progress tracking and logging

- 🟠 **Incremental & Idempotent Writes**
  - [x] Implement Delta Merge strategy for idempotent writes
  - [x] Add tracking of `_lastUpdated` cursor for incremental loading
  - [x] Add data integrity checks post-write

## 3. YAML Mapping Specs
-----------------------
- 🔴 **Core Resource Mappings**
  - [x] Create `config/generic_mappings/Patient.yaml`
  - [x] Create `config/generic_mappings/Observation.yaml`
  - [x] Create `config/generic_mappings/Encounter.yaml`

- 🟡 **Extended Resource Mappings**
  - [x] Create `config/generic_mappings/DiagnosticReport.yaml`
  - [x] Create `config/generic_mappings/MedicationRequest.yaml`
  - [x] Create `config/generic_mappings/Condition.yaml`

## 4. Optional Overrides
-----------------------
- 🟡 **Custom Transformers**
  - [x] Create `transforms/custom/patient.py` with specialized logic
  - [x] Implement custom `post_normalise()` method as demonstration
  - [x] Add docstrings explaining extension points

## 5. Validation Layer
--------------------
- 🔴 **Core Validation Framework**
  - [x] Create `validation/core.py` with `ValidationContext` class
  - [x] Implement Pydantic row-by-row validation with UDF
  - [x] Add metrics tracking for validation issues

- 🟠 **Validation Rules Config**
  - [x] Create `config/validation_rules.yaml` with resource-specific rules
  - [x] Implement loader in `validation/core.py` to apply these rules
  - [x] Add support for required fields, regex patterns, and code sets

- 🟡 **Validation Integration**
  - [x] Hook validation into BaseTransformer's `post_normalise()`
  - [x] Add toggle via `mapping_spec.get("validate", True)`
  - [x] Create report writing logic to Foundry dataset

## 6. Testing Framework
---------------------
- 🔴 **Unit Tests**
  - [x] Create `tests/unit/test_yaml_mapper.py`
  - [x] Create `tests/unit/test_registry.py`
  - [x] Add tests for path resolution and edge cases

- 🔴 **Integration Tests**
  - [ ] Create `tests/integration/test_transform_end_to_end.py`
  - [ ] Set up local Spark environment for testing
  - [ ] Implement assertions for row counts and column existence

- 🟠 **Test Data & Fixtures**
  - [ ] Create `tests/data/sample_patient_bundle.json`
  - [ ] Create `tests/data/sample_observation_bundle.json`
  - [ ] Add pytest fixtures for reusable components

- 🟡 **Edge Case Tests**
  - [ ] Add tests for empty resources and malformed data
  - [ ] Test handling of unexpected FHIR structures
  - [ ] Add tests for data loss edge cases

## 7. Production Readiness
------------------------
- 🔴 **Logging Framework**
  - [x] Create `utils/logging.py` with JSON structured logging
  - [x] Add resource_type and record_count to log context
  - [x] Implement PII masking in logs

- 🟠 **Secrets Management**
  - [x] Set up JWT private key from Foundry secret store
  - [x] Add validation for retrieved secrets
  - [x] Implement secure temporary storage

- 🟠 **Error Handling Framework**
  - [x] Create `utils/retry.py` with exponential backoff decorator
  - [x] Replace generic exceptions with specific types
  - [x] Add proper error messages and logging

- 🟡 **Performance Optimizations**
  - [ ] Implement UDF caching for templates
  - [ ] Add column pruning to reduce memory usage
  - [ ] Set optimal partition strategy for large datasets

## 8. Palantir Workflow Integration
---------------------------------
- 🟠 **Foundry Dataset Manifests**
  - [ ] Add dynamic manifest generation for Silver tables
  - [ ] Set retention policies (Bronze 90d, Silver 1y)
  - [ ] Configure permissions for health analysts

- 🟡 **Foundry CI Integration**
  - [ ] Create `.foundryci.yaml` with test suite
  - [ ] Set coverage requirements (`--cov-fail-under=85`)
  - [ ] Add automatic dataset detection

## 9. Final Acceptance Tests
-------------------------
- 🟠 **DEV Environment Testing**
  - [ ] Run workflow in DEV with 3 resources
  - [ ] Verify Silver tables creation and row counts
  - [ ] Check validation results for errors

- 🟠 **New Resource Testing**
  - [ ] Add new YAML mapping for DiagnosticReport
  - [ ] Run extract+transform to verify new dataset creation
  - [ ] Validate data quality in new dataset

## 10. Real-World Testing & Logging
---------------------------------
- 🟠 **Live Sandbox Integration Tests**
  - [x] Create `tests/live/test_epic_sandbox_extract.py`
  - [x] Add test for patient resource retrieval
  - [x] Configure for CI environment

- 🟡 **Chaos/Resilience Tests**
  - [x] Create `tests/perf/chaos_test.py` for network failures
  - [x] Implement API error response tests
  - [x] Generate resilience metrics report

- 🟠 **Log Shipping**
  - [x] Create `pipelines/08_log_shipper.py`
  - [x] Implement metrics shipping to monitoring systems
  - [x] Add alerting hooks for critical errors

## 11. Gold Transform Implementation
----------------------------------
- 🔴 **Patient Summary Transform**
  - [x] Create `pipelines/gold/patient_summary.py`
  - [x] Implement demographics, conditions, meds summary logic
  - [x] Add manifest file for Foundry integration

- 🔴 **Patient Timeline Transform**
  - [x] Create `pipelines/gold/patient_timeline.py`
  - [x] Implement temporal event ordering logic
  - [x] Add manifest file for Foundry integration

- 🟡 **Encounter KPI Transform**
  - [x] Create `pipelines/gold/encounter_kpi.py`
  - [x] Implement length-of-stay and diagnosis count calculations
  - [x] Add manifest file for Foundry integration

## 12. LLM Self-Check Logic
-------------------------
- 🟡 **LLM Code Audit**
  - [x] Create `pipelines/09_llm_code_audit.py`
  - [x] Implement integration with OpenAI or Palantir AIP
  - [x] Add report generation for audit findings

- 🟢 **CI Integration for LLM Audit**
  - [ ] Add LLM audit step to CI pipeline
  - [ ] Configure thresholds for warnings and errors
  - [ ] Implement security measures for code submissions

## 13. Future-Proofing
-------------------
- 🟢 **Multi-Tenant Design**
  - [ ] Add `hospital_org_id` column to all tables
  - [ ] Implement row-level security based on organization
  - [ ] Configure Foundry entitlements

- 🟢 **FHIR Version Evolution**
  - [ ] Add `fhir_version` column to all tables
  - [ ] Create versioned views for latest records
  - [ ] Implement schema diff tests for version changes

- 🟢 **Feature Flags**
  - [ ] Create `utils/feature_flags.py` for runtime toggles
  - [ ] Add configuration dataset for flag management
  - [ ] Implement canary release support

## Completion Checklist
---------------------
- [ ] Final blueprint verification against implementation
- [ ] End-to-end testing with all components
- [ ] Documentation update with architecture and examples
- [ ] Performance testing with large datasets
- [ ] Security review and vulnerability assessment
