# FHIR Transformation Data Quality Assessment Plan

This document outlines the strategy and plan for assessing the quality of FHIR data transformations through Bronze, Silver, and Gold tiers within the Epic FHIR Integration project.

## 1. Overall Goal

To systematically evaluate and ensure the accuracy, completeness, conformance, and utility of FHIR data as it is processed, with a particular focus on preparing "Gold" tier data suitable for Large Language Model (LLM) consumption.

## 2. Quality Tiers and Dimensions

This plan aligns with the tiered data strategy (Bronze, Silver, Gold) defined in `REAL_WORLD_TESTING_TODO.md`.

### 2.1. Bronze Tier (Raw Data as Fetched)

*   **Description:** Data as it is extracted from the source Epic FHIR API with minimal changes (e.g., basic parsing).
*   **Quality Dimensions & Metrics:**
    *   **Source Completeness:**
        *   *Metric:* All specified resource types (Patient, Encounter, Observation, Condition, etc.) are fetched for a given query/patient.
        *   *Check:* Count of fetched resources vs. expected; presence of all designated resource types.
    *   **Structural Validity (FHIR R4 Base):**
        *   *Metric:* Data conforms to base FHIR R4 specifications (correct resource types, required elements, basic data types).
        *   *Check:* Validation against base FHIR R4 schema using the HL7 FHIR Validator.
    *   **Source Fidelity:**
        *   *Metric:* Bronze data accurately reflects the source system data at the time of fetch.
        *   *Check:* Spot checks against source (if possible); consistency checks across repeated fetches.
    *   **Timeliness:**
        *   *Metric:* Data is recent and relevant.
        *   *Check:* Review of fetch timestamps in metadata.

### 2.2. Silver Tier (Cleansed, Standardized, Basic Enrichment)

*   **Description:** Bronze data that has undergone cleansing, standardization of values (units, codes), and initial, commonly required enrichments.
*   **Quality Dimensions & Metrics (includes Bronze +):**
    *   **Cleansing Effectiveness:**
        *   *Metric:* Consistent handling of missing/erroneous values; standardized data types (e.g., `dateTime` formats); standardized units of measure (e.g., vital signs, lab units).
        *   *Check:* Automated scripts to verify unit conversions, date format consistency; counts of null/defaulted values.
    *   **Coding Quality & Standardization:**
        *   *Metric:* Key coded elements (diagnoses, labs, procedures) use recognized code systems (SNOMED CT, LOINC, RxNorm) with valid URIs. `display` elements are consistent with codes.
        *   *Check:* Validation against ValueSets (where defined for Silver); scripts to check `system` URIs; checks for `code`-`display` mismatches.
    *   **Basic Enrichment Quality:**
        *   *Metric:* Accuracy and appropriate population of basic extensions (e.g., initial US Core extensions if targeted).
        *   *Check:* Scripts to verify presence and valid content of these extensions.
    *   **Internal Consistency:**
        *   *Metric:* Logical relationships within resources are sound (e.g., `Encounter.period.end` >= `Encounter.period.start`).
        *   *Check:* FHIRPath assertions or custom script-based rules.
    *   **Conformance (Silver Profile):**
        *   *Metric:* Data validates against a defined "Silver" FHIR profile.
        *   *Check:* Validation using HL7 FHIR Validator against the Silver tier `StructureDefinition`s.

### 2.3. Gold Tier (LLM-Ready, Target Profile Conformance)

*   **Description:** Silver data that is fully conformant to specified target profiles (e.g., US Core), comprehensively enriched, referentially intact, and optimized for LLM consumption.
*   **Quality Dimensions & Metrics (includes Silver +):**
    *   **Target Profile Conformance:**
        *   *Metric:* Full conformance to target FHIR Implementation Guides (e.g., US Core, project-specific IGs), including cardinality, value set bindings, mandatory elements, slicing, and complex extensions.
        *   *Check:* Validation using HL7 FHIR Validator against Gold tier/target IG `StructureDefinition`s.
    *   **Terminology Mapping Accuracy:**
        *   *Metric:* Source codes are correctly mapped to standard terminologies required by target profiles.
        *   *Check:* Automated checks for mapping presence; SME review for mapping accuracy.
    *   **Referential Integrity:**
        *   *Metric:* All internal resource references (e.g., `Observation.subject` -> `Patient`) are resolvable and valid. No orphaned resources.
        *   *Check:* Automated scripts using FHIRPath or resource graph traversal to validate references.
    *   **Semantic Completeness (for LLM):**
        *   *Metric:* All data elements critical for the LLM's intended task are present, accurate, and well-structured.
        *   *Check:* SME review; specific checks based on LLM input requirements.
    *   **Narrative Quality & Utility:**
        *   *Metric:* FHIR resource narratives are human-readable, accurate, and provide useful summaries for LLM context. Custom summaries are of high quality.
        *   *Check:* SME review of narratives; automated checks for presence and basic structure of narratives.
    *   **De-identification Efficacy (if applicable):**
        *   *Metric:* De-identification processes are robust and verified, effectively removing PHI while retaining utility.
        *   *Check:* Automated checks for presence of PHI patterns; manual review of de-identified samples.
    *   **LLM Input Schema Adherence:**
        *   *Metric:* The final output structure (e.g., bundled JSON, specific fields) meets the LLM's precise input requirements.
        *   *Check:* Validation against a JSON schema representing the LLM input; test ingest by the LLM.

## 3. Assessment Activities & Tools

### 3.1. Develop/Refine Tier-Specific FHIR Profiles
*   **Activity:** Define and maintain `StructureDefinition` resources for Silver and Gold tiers. These profiles will formally specify expected structure, content, terminology bindings, and invariants for each tier. Bronze tier will typically be validated against base FHIR R4.
*   **Tools:**
    *   **FHIR Shorthand (FSH) & Sushi:** Use FSH for human-readable profile definitions and Sushi to compile them into `StructureDefinition` JSON files. Store these in `epic_fhir_integration/profiles/`.
    *   **IDE Plugins for FSH:** For syntax highlighting and basic validation.
    *   **Simplifier.net / Firely Terminal:** For visualizing, validating, and managing profiles during development.

### 3.2. Implement Automated Validation
*   **Activity:** Create and maintain scripts and test cases that use a FHIR validator.
*   **Tools & Approach:**
    *   **HL7 FHIR Validator (Java CLI):** Integrate calls to the official validator via `epic_fhir_integration/validation/validator.py`.
        *   Ensure `FHIRValidator` can dynamically accept profile URLs/paths.
        *   Validate data against appropriate profiles at each stage (Bronze -> R4, Silver -> Silver Profile, Gold -> Gold/Target IG Profile).
    *   **FHIRPath Assertions:**
        *   Embed FHIRPath expressions as invariants within `StructureDefinition`s.
        *   Use Python libraries (`fhirpathpy`, Pathling's engine) in custom scripts (`test_validation_live.py`, new QA scripts) to execute FHIRPath checks for business rules, complex consistency, and referential integrity not covered by profiles.

### 3.3. Develop Custom Quality Check Scripts
*   **Activity:** Write Python scripts for checks not covered by standard FHIR validation.
*   **Tools & Approach:**
    *   **Python:** Utilize `fhir.resources` for parsing and navigating FHIR data, `pandas` for potential tabular analysis.
    *   **Examples:**
        *   Verify specific transformation logic (e.g., unit conversions, date transformations).
        *   Check for correct population of custom extensions.
        *   Statistical analysis (e.g., % of Observations with standard codes).
        *   Differential checks: Compare data outputs before and after a transformation stage to verify expected changes.
        *   Completeness checks for LLM-critical fields.

### 3.4. Implement Data Lineage and Transformation Logging
*   **Activity:** Ensure transformations are logged to trace data provenance.
*   **Tools & Approach:**
    *   Enhance application logging within transformation scripts.
    *   Consider using a standard FHIR extension for data quality tier and transformation traceability if needed, as mentioned in `REAL_WORLD_TESTING_TODO.md`.

### 3.5. Establish Manual Review Process
*   **Activity:** Define a structured process for Subject Matter Experts (SMEs: clinicians, FHIR experts, LLM engineers) to review samples of Gold-tier data.
*   **Focus:** Clinical plausibility, mapping accuracy, narrative quality, fitness for LLM tasks.
*   **Tools:** Checklists, review guidelines, data viewing tools (e.g., rendering FHIR resources as HTML).

### 3.6. Integration into Testing Workflow & Reporting
*   **Activity:** Incorporate quality assessment steps into the existing testing framework.
*   **Tools & Approach:**
    *   Modify `run_real_world_tests.sh` to include options for running specific quality checks.
    *   Extend `test_validation_live.py` and create new test files dedicated to data quality for different tiers/transformations.
    *   Enhance `generate_test_report.py` to:
        *   Include detailed data quality metrics per tier.
        *   Summarize validation pass/fail rates against specific profiles.
        *   Report on coverage of terminology mappings.
        *   Incorporate summaries of LLM-readiness checks and manual review findings.

## 4. Key External Tools to Leverage

*   **HL7 FHIR Validator (Java CLI):** Primary tool for schema and profile conformance.
*   **Sushi (CLI):** For compiling FSH into FHIR `StructureDefinition`s.
*   **FHIRPath Engines (Python libraries like `fhirpathpy`, or Pathling):** For data querying and assertions.
*   **Terminology Services/Browsers (e.g., LOINC, SNOMED CT official sites, VSAC, or a FHIR Terminology Server):** For validating codes and understanding value sets during profile development and SME review.
*   **(Potentially) Inferno:** For rigorous testing against US Core if it's a primary target IG for the Gold tier.
*   **(Potentially) Great Expectations:** For a more formal, general-purpose data quality framework if custom Python scripts become too unwieldy for statistical checks or certain types of validation.

## 5. Implementation Steps

1.  **Formalize Profiles:** Complete the FSH definitions for Silver and Gold tier profiles, including relevant invariants. Store compiled JSON in `epic_fhir_integration/profiles/`.
2.  **Enhance Validator:** Ensure `FHIRValidator` in `epic_fhir_integration/validation/validator.py` can robustly use local or remote profiles.
3.  **Expand Validation Tests:** Add `pytest` cases in `test_validation_live.py` (or new dedicated files) to validate sample real-world data against these profiles.
4.  **Develop Custom QA Scripts:** Incrementally create Python scripts for checks identified in section 3.3.
5.  **Integrate Reporting:** Update `generate_test_report.py` to consume and present results from these new QA checks.
6.  **Pilot Manual Review:** Develop a checklist and conduct an initial round of manual review for Gold-tier data.
7.  **Iterate:** Continuously refine profiles, validation rules, and scripts based on findings. 