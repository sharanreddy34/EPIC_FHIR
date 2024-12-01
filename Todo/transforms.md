PRODUCTION-GRADE BRONZE ➜ SILVER ➜ GOLD PLAN
(for the epic-fhir-integration package running in Palantir Foundry)
──────────────────────────
FOUNDATIONAL PRINCIPLES
──────────────────────────
Medallion architecture – each layer has a single purpose:
Bronze: immutable raw JSON bundles exactly as returned by Epic.
Silver: 1 row ≈ 1 FHIR resource, cleaned & flattened; schema is stable.
Gold: business-ready tables & KPI datasets (aggregations, joins, denormalised views).
Every transform is idempotent, incremental, well-typed, logged, unit-tested.
Dataset paths are contracts; changing them requires explicit migration steps.
All credentials live in Foundry Secrets; NO plain‐text keys in code or logs.
──────────────────────────
DIRECTORY & MODULE LAYOUT
──────────────────────────
epic-fhir-integration/
│
├─ config/ ⇦ YAMLs only
│ ├─ api_config.yaml (FHIR base URL, retry settings …)
│ ├─ resources_config.yaml (enabled resources, incremental params …)
│ └─ gold_views.yaml (high-level definitions of Gold views)
│
├─ pipelines/ ⇦ Spark transforms
│ ├─ 00_fetch_token.py
│ ├─ 01_extract_resources.py
│ ├─ 02_transform_load.py
│ ├─ 03_gold/
│ │ ├─ patient_summary.py
│ │ ├─ encounter_summary.py
│ │ └─ … (one file per gold mart)
│ ├─ 04_workflow.py (orchestrator)
│ └─ 05_monitoring.py
│
├─ lib/ ⇦ pure Python helpers
│ ├─ fhir_client.py (all HTTP logic)
│ ├─ auth.py (token mgmt helpers)
│ └─ transforms/
│ ├─ common.py (explode_bundle, json schema utils)
│ └─ resource_specific/
│ ├─ patient.py
│ ├─ observation.py
│ └─ …
│
└─ tests/ ⇦ pytest unit + integration tests
──────────────────────────
DATASET PATH CONTRACTS
──────────────────────────
/config/ api_config resources_config
/secrets/ epic_token (Δ only via 00)
/control/ fhir_cursors workflow_status
/bronze/ fhir_raw/<ResourceType>/.json
/silver/ fhir_normalized/<lowercase resource type>
/gold/ patient_summary encounter_summary …
/metrics/ transform_metrics
/monitoring/ pipeline_metrics
──────────────────────────
PIPELINE STEPS
──────────────────────────
🔹 00_fetch_token.py (Profile: FHIR_TOKEN_REFRESH)
Reads /config/api_config.yaml
POST client-cred to token endpoint
Writes single-row Delta to /secrets/epic_token
Schema: access_token (string), expires_at (timestamp)
🔹 01_extract_resources.py (Profile: FHIR_RESOURCE_EXTRACTION)
Inputs:
/config/api_config.yaml, /config/resources_config.yaml
/secrets/epic_token (for current token)
/control/fhir_cursors (optional) (last updated stamps)
Output: /bronze/fhir_raw
Logic:
Loop over enabled resources in config (or CLI param).
For each, call FHIRClient.search_resource() with incremental params.
For each bundle page write one JSON file ⇒
{resource_type}/{yyyyMMdd_HHmmss}{page}.json
4. Update cursors dataset atomically (resource, max_lastUpdated).
🔹 02_transform_load.py (Profile: FHIR_RESOURCE_TRANSFORM)
Inputs: /bronze/fhir_raw, resources_config.yaml
Outputs:
/silver/fhir_normalized (dataset, partitioned by resource_type)
/metrics/transform_metrics (one row per run|resource)
Logic:
For each resource file glob read JSON with Spark.
Flatten with explode_bundle() + resource_specific/.py mapper.
Enforce explicit StructType → write in append mode, mergeSchema false.
Capture counts + runtime in transform_metrics.
🔹 03_gold/… (multiple transforms, one per business mart)
Example: patient_summary.py (Profile: FHIR_GOLD_PATIENT_SUMMARY)
Inputs: /silver/fhir_normalized/patient plus optional others
Output: /gold/patient_summary
Aggregate metrics (encounter counts, last visit date, diagnoses, etc.)
All joins by patient.id, left joins to keep all patients.
🔹 04_workflow.py (Profile: FHIR_PIPELINE_ORCHESTRATOR)
Inputs: resources_config, api_config, epic_token, cursors, metrics
Output: /control/workflow_status
Determines which resources need refresh; triggers downstream steps when run via Foundry Workflow UI.
Writes status row (JSON string) for observability.
🔹 05_monitoring.py (Profile: FHIR_PIPELINE_MONITORING)
Combines token life-cycle, extraction stats, transform stats, patient counts into one wide table in /monitoring/pipeline_metrics.
──────────────────────────
FUNCTION / TRANSFORM YAMLs
──────────────────────────
Each .py above needs a matching YAML (e.g. pipelines/00_fetch_token.yml).
Skeleton (example for 00_fetch_token):
Apply to .gitignore
4h
Copy this pattern for the other transforms with correct paths, optional inputs, and profiles.
──────────────────────────
WORKFLOW DEFINITION
──────────────────────────
Use Foundry Workflow UI OR a declarative YAML (workflow_pipeline.yml):
refresh-token (00) → always first
extract-resources (01) → after token
transform-resources (02) → after extract
gold-patient-summary (03a) → after transform
gold-<other> (03b …)
monitoring (05) → after gold
orchestrator (04) can run async to produce status but usually triggers others in UI.
──────────────────────────
INCREMENTAL STRATEGY
──────────────────────────
Cursor dataset /control/fhir_cursors (resource_type, last_updated) keeps state.
01_extract_resources reads cursor; sends _lastUpdated=gt<ts> param.
After successful write it upserts new max timestamp.
02_transform_load can filter by input file modification time if needed (fast path).
──────────────────────────
DATA QUALITY & SCHEMA EVOLUTION
──────────────────────────
Each Silver table kept under strict schema control (StructType JSON).
Breaking changes handled by versioned columns not dropping old ones until migration.
Transform writes with mergeSchema = false (fail-fast).
Row-level QA metrics written to /metrics/transform_metrics.
──────────────────────────
LOGGING & ALERTING
──────────────────────────
Use standard logging with context (resource_type, run_id).
05_monitoring aggregates => choose thresholds, attach to Foundry Watchdog alerts.
Token expiry < 12 h → WARNING; < 1 h → CRITICAL alert.
──────────────────────────
TESTING & CI/CD
──────────────────────────
tests/unit/ – pytest covering lib/ modules (mock requests, chispa for DataFrames).
tests/integration/ – run Spark locally with small sample JSON bundles.
GitHub Actions: lint → unit → package build → optional integration.
On merge to main: push to Foundry code repo via Foundry’s Git inbound.
──────────────────────────
ROLLOUT CHECKLIST
──────────────────────────
☐ Secrets (EPIC_CLIENT_ID, EPIC_CLIENT_SECRET) created in Foundry
☐ Datasets paths pre-provisioned with correct ACLs
☐ All YAMLs committed & pushed → Foundry auto-compiles
☐ Run workflow in DEV stack with one resource enabled
☐ Verify Bronze JSON, Silver counts, Gold aggregates, Monitoring rows
☐ Enable remaining resources, schedule nightly full workflow
☐ Set retention policies (Bronze = 90 days, Silver = 1 year, Gold = forever)
──────────────────────────
With this plan, a less-capable LLM (or a junior engineer) can:
Scaffold the transforms exactly as described.
Copy the skeleton YAML, adjust paths & resources.
Rely on existing helper modules in lib/ for HTTP + parsing.
Deploy & iterate safely inside Foundry.