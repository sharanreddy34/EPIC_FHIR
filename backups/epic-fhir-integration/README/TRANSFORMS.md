# FHIR Pipeline Transformation Framework

This document explains the FHIR data pipeline transformation framework implemented in this repository. The pipeline follows a medallion architecture pattern with Bronze, Silver, and Gold layers.

## Foundational Principles

- **Medallion Architecture**: Each layer has a specific purpose:
  - **Bronze**: Immutable raw JSON bundles exactly as returned by Epic
  - **Silver**: Tabular format where 1 row ≈ 1 FHIR resource, cleaned & flattened; schema is stable
  - **Gold**: Business-ready tables & KPI datasets (aggregations, joins, denormalized views)
- **Transform Properties**: Every transform is idempotent, incremental, well-typed, logged, and unit-tested
- **Dataset Paths**: Treated as contracts; changing them requires explicit migration steps
- **Security**: All credentials live in Foundry Secrets; no plain-text keys in code or logs

## Directory Structure

```
epic-fhir-integration/
│
├─ config/                         ⇦ YAMLs only
│   ├─ api_config.yaml             (FHIR base URL, retry settings …)
│   ├─ resources_config.yaml       (enabled resources, incremental params …)
│   └─ gold_views.yaml             (high-level definitions of Gold views)
│
├─ pipelines/                      ⇦ Spark transforms
│   ├─ 00_fetch_token.py           (Token refresh)
│   ├─ 01_extract_resources.py     (API to Bronze)
│   ├─ 02_transform_load.py        (Bronze to Silver)
│   ├─ 03_gold/                    (Silver to Gold)
│   │   ├─ patient_summary.py
│   │   ├─ encounter_summary.py
│   │   └─ medication_summary.py
│   ├─ 04_workflow.py              (Orchestrator)
│   └─ 05_monitoring.py            (Pipeline metrics)
│
├─ lib/                            ⇦ Pure Python helpers
│   ├─ fhir_client.py              (All HTTP logic)
│   ├─ auth.py                     (Token mgmt helpers)
│   └─ transforms/                 (Resource transformation)
│       ├─ common.py               (Shared utilities)
│       └─ resource_specific/      (Resource mappers)
│           ├─ patient.py
│           ├─ observation.py
│           └─ …
```

## Dataset Path Contracts

| Path | Dataset | Description |
| ---- | ------- | ----------- |
| `/config/` | `api_config`, `resources_config` | Configuration files |
| `/secrets/` | `epic_token` | Authorization tokens (Δ only via 00) |
| `/control/` | `fhir_cursors`, `workflow_status` | Pipeline control data |
| `/bronze/` | `fhir_raw/<ResourceType>/*.json` | Raw FHIR bundles |
| `/silver/` | `fhir_normalized/<lowercase resource type>` | Flattened FHIR resources |
| `/gold/` | `patient_summary`, `encounter_summary`, etc. | Business data marts |
| `/metrics/` | `transform_metrics` | Pipeline performance metrics |
| `/monitoring/` | `pipeline_metrics` | Pipeline health monitoring |

## Pipeline Components

1. **Token Management** (`00_fetch_token.py`):
   - Reads `/config/api_config.yaml`
   - POSTs client credentials to token endpoint
   - Writes single-row Delta to `/secrets/epic_token`
   - Schema: `access_token` (string), `expires_at` (timestamp)

2. **Resource Extraction** (`01_extract_resources.py`):
   - Loops over enabled resources in config
   - Calls `FHIRClient.search_resource()` with incremental params
   - Writes JSON files to `/bronze/fhir_raw/{resource_type}/{timestamp}_{page}.json`
   - Updates `/control/fhir_cursors` with max `_lastUpdated` timestamps

3. **Transformation** (`02_transform_load.py`):
   - Reads JSON files from Bronze layer
   - Flattens with `explode_bundle()` + resource-specific mappers
   - Enforces explicit `StructType` schemas
   - Writes to `/silver/fhir_normalized` in append mode
   - Captures metrics in `/metrics/transform_metrics`

4. **Gold Layer** (`03_gold/*.py`):
   - Aggregates data from multiple Silver datasets
   - Provides business-specific views and KPIs
   - Output: `/gold/{mart_name}`

5. **Orchestration** (`04_workflow.py`):
   - Coordinates execution of pipeline components
   - Tracks pipeline status
   - Output: `/control/workflow_status`

6. **Monitoring** (`05_monitoring.py`):
   - Combines token lifecycle, extraction stats, transform stats
   - Provides a holistic view of pipeline health
   - Output: `/monitoring/pipeline_metrics`

## Function YAMLs

Each transform has a corresponding YAML file (e.g., `pipelines/00_fetch_token.yml`) defining:
- Inputs/outputs and their paths
- Memory and timeout requirements
- Execution schedule
- Required secrets
- Dependencies

## Workflow

The workflow is defined in `workflow_pipeline.yml` and orchestrates:
1. `token_refresh` → Runs first
2. `extract_resources` → After token refresh
3. `transform_resources` → After extraction
4. Gold layer transforms → After Silver transformations
5. `pipeline_monitoring` → After Gold transforms

## Incremental Strategy

- The `/control/fhir_cursors` dataset tracks the last extracted timestamp per resource type
- Extraction transforms use these cursors to only fetch new/updated resources
- Silver transformations process only new Bronze files

## Deployment Checklist

- [ ] Set up Foundry Secrets (`EPIC_CLIENT_ID`, `EPIC_CLIENT_SECRET`)
- [ ] Pre-provision dataset paths with correct access controls
- [ ] Push all code and YAMLs to Foundry's code repository
- [ ] Run workflow with a limited resource subset in the DEV environment
- [ ] Verify all pipeline phases work correctly
- [ ] Enable remaining resources and set up scheduled execution
- [ ] Configure retention policies
  - Bronze: 90 days
  - Silver: 1 year
  - Gold: Forever 