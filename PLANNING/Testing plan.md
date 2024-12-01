# ATLAS Palantir FHIR Pipeline – Comprehensive Testing Plan

> Blueprint reference: see "Transform part 2.md" (v2) – this plan verifies every acceptance criterion in a **live** environment before PROD promotion.

## 1  Objectives
1. Validate end-to-end data flow from Epic FHIR **Sandbox API** → Bronze → Silver (generic engine) → Gold (summaries / timelines / KPIs) → downstream consumers.
2. Prove idempotency, schema integrity, data-loss guardrails (< 5 %), and rule-based validation work under production-like load.
3. Exercise logging, alerting, retry/back-off, and secrets management paths.
4. Produce artefacts (metrics, validation reports, audit logs) for QA sign-off.

## 2  Prerequisites
| Item | Value / Location |
|------|------------------|
| Sandbox base URL | `$EPIC_BASE_URL` (e.g. `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4`) |
| Client ID         | `$EPIC_CLIENT_ID` (Foundry Secret) |
| RSA Private Key   | `$EPIC_PRIVATE_KEY` (Foundry Secret – PEM) |
| Sample Patient ID | `Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB` |
| Spark Cluster     | 8 × 32 GiB executors (same as PROD) |
| Foundry datasets  | `/bronze/fhir_raw`, `/silver/fhir_normalized/*`, `/gold/*` |
| CI markers        | `pytest -m live` for live API tests |

Secrets are injected at runtime via Profile Variables:
```yaml
profiles:
  - name: EPIC_SANDBOX
    vars:
      EPIC_BASE_URL: {{secret."EPIC_BASE_URL"}}
      EPIC_CLIENT_ID: {{secret."EPIC_CLIENT_ID"}}
      EPIC_PRIVATE_KEY: {{secret."EPIC_PRIVATE_KEY"}}
```

## 3  Test Matrix
| Phase | Resource Types | Volume | Purpose |
|-------|----------------|--------|---------|
| Unit                | N/A (mocked) | 100 rows synthetic | Logic correctness, path resolution, validation rules |
| Local Integration   | Patient, Observation | 1 bundle file each | Developer laptop sanity checks (no external calls) |
| Live Sandbox Smoke  | Patient (single) | 1 real patient | Verify auth, extract, transform paths |
| Live Sandbox Full   | Patient, Observation, Encounter, Condition, MedicationRequest, DiagnosticReport | full history (≈500 resources) | End-to-end Silver tables, validation, log shipping |
| DEV Cluster Load    | Same 6 resources | ≥50k resources (loop pull) | Performance & Delta Merge behaviour |
| Chaos / Resilience  | Same 6 resources | error injection | Back-off, retry, alerting |
| Gold Verification   | patient_summary, patient_timeline, encounter_kpi | derived rows | Column presence, counts, KPIs |

## 4  Test Phases & Steps

### 4.1  Smoke (CI) – **~2 min**
1. `pytest -m unit` – ensure 100 % unit tests green.
2. `pytest -m live -k test_connection` – hit `/metadata` endpoint (no PHI).

### 4.2  Live Sandbox Extract → Silver
Run via helper script:
```bash
export EPIC_BASE_URL=...; export EPIC_CLIENT_ID=...;
export EPIC_PRIVATE_KEY=$(cat key.pem)
python run_local_fhir_pipeline.py \
  --patient-id ${PATIENT_ID:-Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB} \
  --resources patient,observation,encounter,condition,medicationrequest,diagnosticreport \
  --steps token,extract,transform --debug
```
Assertions:
* Bronze JSON bundles written (≥1 file / resource).
* Silver tables exist; `SELECT COUNT(*)` matches bundle entry count.
* `_hash_id` primary key unique.
* Validation fatal issues = 0; loss_pct ≤ 5 %.

### 4.3  Live Sandbox → Gold
Trigger Gold DAG downstream (`gold-*` manifests). Verify:
* `/gold/patient_summary` rows = distinct patient_id.
* `/gold/patient_timeline` rows ≥ distinct events from Silver (no NULL event_time).
* `/gold/encounter_kpi.length_of_stay_hours` non-null for finished encounters.

### 4.4  Performance (DEV Cluster)
* Loop over 10 patients × 20 days history (≈50k resources).
* Measure transform wall-time, Spark stage metrics, checkpoint memory.
* Ensure job completes < 15 min and driver RAM < 8 GiB.

### 4.5  Chaos Tests
Execute `pytest tests/perf/chaos_test.py` which simulates:
* Network timeouts (sleep) → expect retries & Slack alert.
* 429 responses → exponential back-off honoured.
* 5xx flaps → merge after retries.

### 4.6  LLM Code-Audit Gate
Run `python pipelines/09_llm_code_audit.py --commit $GIT_COMMIT`.
Build fails if ≥1 high-risk finding.

## 5  Success Criteria
| Metric | Threshold |
|--------|-----------|
| Validation fatal issues | 0 |
| Data loss (`loss_pct`)  | ≤ 5 % per resource |
| `_hash_id` duplicates  | 0 |
| Silver row count vs bundle entries | 100 % parity |
| Gold patient_summary rows | = distinct `patient_id` |
| Gold timeline rows    | ≥ total events |
| Log shipper alerts    | < 1 false-positive |
| Transform retry success rate | ≥ 99 % |

## 6  Reporting
* **Metrics:** `/metrics/transform_metrics`, `/metrics/log_shipping_results` datasets
* **Validation Issues:** `/metrics/validation_results/*` JSON lines
* **Chaos Report:** `tests/perf/chaos_report.md` artefact in CI
* **QA Summary:** generated `QA_REPORT.md` (updated each release)

## 7  Execution Commands Cheat-Sheet
```bash
# Full local run (live sandbox)
make run-live PATIENT_ID=<id>

# Unit + integration tests
pytest -m "unit or integration" --cov=fhir_pipeline --cov-fail-under=85

# Chaos tests (network failure simulation)
pytest tests/perf/chaos_test.py

# LLM audit on last commit
python pipelines/09_llm_code_audit.py --commit $(git rev-parse HEAD)
```

## 8  CI / CD Hooks
* `.github/workflows/ci.yml` stages:
  1. **lint** – ruff / black
  2. **unit** – pytest -m unit
  3. **integration** – pytest -m integration (Spark local)
  4. **live-smoke** – requires sandbox creds (optional)
  5. **chaos** – chaos tests
  6. **llm-audit** – pipelines/09_llm_code_audit.py
* Fail pipeline on any threshold breach.

## 9  Data Clean-Up
Post-run, call `/admin/delete` on temp datasets or set TTL = 24 h via manifest override to avoid storage bloat.

## 10  Implementation Checklist – Code Additions
The table below enumerates every **new file / edit** still needed inside `epic-fhir-integration` to operationalise this test plan.  All items are stub-friendly – write minimal code first, expand as tests evolve.

| # | Path (repo-relative) | Type | Purpose |
|---|----------------------|------|---------|
| 1 | `tests/data/sample_patient_bundle.json` | JSON fixture | Realistic Patient bundle from Epic sandbox (scrub PHI) |
| 2 | `tests/data/sample_observation_bundle.json` | JSON fixture | Observation bundle inc. vital signs |
| 3 | `tests/fixtures/spark.py` | Py module | `pytest` fixture to spin **local Spark** with Delta support |
| 4 | `tests/fixtures/bundles.py` | Py module | Helpers to load sample JSON into Spark DF |
| 5 | `tests/integration/test_transform_end_to_end.py` | Test | ① Load sample bundles → ② call `run_local_fhir_pipeline.py` (mock token) → ③ assert row counts, `_hash_id` uniqueness, validation passes |
| 6 | `tests/integration/__init__.py` | package | marks integration scope |
| 7 | `scripts/run_ci_live_smoke.sh` | Bash | Thin wrapper: sets sandbox env vars → runs `pytest -m live -k test_connection` |
| 8 | `scripts/run_ci_chaos.sh` | Bash | Invokes `pytest tests/perf/chaos_test.py` plus report upload |
| 9 | `.foundryci.yaml` | CI spec | Stages: lint → unit → integration (Spark) → chaos → live-smoke (gated by secret) → llm-audit |
| 10 | `fhir_pipeline/utils/feature_flags.py` | Py | Simple `get_flag(name, default)` reading Foundry config dataset (pre-req for canary toggles in tests) |
| 11 | `fhir_pipeline/pipelines/helpers/manifest_writer.py` | Py | Utility to programmatically emit dynamic Silver manifests during tests; used by integration test to clean workspace |
| 12 | `Makefile` updates | text | `make test`, `make test-integration`, `make run-live` shortcuts |

**Acceptance**: All new files committed, **`pytest -m "unit or integration"` passes with coverage ≥ 85 %**, Foundry CI green.

> After completing all rows, tick the corresponding boxes in *Transform part 3.md* under: *Integration Tests*, *Test Data & Fixtures*, *Foundry CI Integration*, *Performance Optimisations* (for template-UDF cache if implemented during tests).

---
This plan ensures we exercise **every** blueprint requirement under conditions that mirror production, giving confidence before promoting to PROD.
