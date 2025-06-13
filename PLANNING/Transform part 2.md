A-TO-Z MODULAR TRANSFORM BLUEPRINT (v2)
=================================================
Purpose 🔰
-------------------------------------------------
Make the Bronze → Silver step **generic** (works for every FHIR resource)
and **easy** enough that a small LLM can extend it by editing YAML only.
Add a bullet-proof **testing & validation suite** so we can prove nothing
is lost or malformed before data flows to Palantir Foundry Gold & LLM
embeddings.

Legend
-------------------------------------------------
• File & dir names = `monospace`.  • ☐ = task to tick off.  • 🔰 = extra context.

Directory Shape After Refactor
-------------------------------------------------
```
fhir_pipeline/
│
├── transforms/
│   ├── base.py              # generic BaseTransformer (new)
│   ├── yaml_mappers.py      # helper that flattens via YAML spec (new)
│   ├── registry.py          # routing logic (new)
│   └── custom/              # optional overrides per resource
│       └── patient.py       # example bespoke override
│
└── config/
    └── generic_mappings/    # one YAML per resource
        ├── Patient.yaml
        ├── Observation.yaml
        └── Encounter.yaml
```

Step-by-Step Tasks
-------------------------------------------------
1  Create Generic Engine
~~~~~~~~~~~~~~~~~~~~~~~
☐ 1.1 `transforms/base.py`
   Minimal abstract class with hooks `pre_normalise()`,
   `post_normalise()`, and private `_apply_mapping()` that calls
   `yaml_mappers.apply_mapping()`.

☐ 1.2 `transforms/yaml_mappers.py`
   • Accepts Spark `DataFrame` and YAML spec -> returns flattened DF.
   • Use `pyspark.sql.functions.col`, plus tiny helper `_fhir_get(col_path)`
     to support dot-notation & `[index]`.
   • Fallback to `None` when path missing so data is never dropped.

☐ 1.3 `transforms/registry.py`
   Logic:
   1. Look for override `transforms.custom.<resource>.Transformer`.
   2. Else build `Generic(BaseTransformer)` with YAML spec.
   3. Return instantiated transformer.

2  Refactor Pipeline Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~
☐ 2.1 Edit `pipelines/transform_load.py`:
```python
from fhir_pipeline.transforms.registry import get_transformer
…
transformer = get_transformer(spark, res_type)
transformed_df = transformer.transform(resources_df)
```
Nothing else changes.

3  Add Mapping Specs (YAML)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
☐ 3.1 Create `config/generic_mappings/Patient.yaml` (id, name, birth_date …).
☐ 3.2 Create minimal specs for Observation & Encounter.  🔰 You only need
       the columns you care about; you can append later with no code.

4  Optional Overrides
~~~~~~~~~~~~~~~~~~~~~
☐ 4.1 If Patient needs special sentence summarisation, implement
   `transforms/custom/patient.py` with custom `post_normalise()` as demo.

5  Validation Layer
~~~~~~~~~~~~~~~~~~~
☐ 5.1 `fhir_pipeline/validation/core.py`:
   • `ValidationContext(schema_cls, dataframe)` – runs schema validation via
     Pydantic row-by-row **in a Spark UDF** (sample 10 % for speed).
   • Writes JSON Lines report to Foundry dataset `/metrics/validation_results`.
   • Counts `fatal / warning / info` issues → driver transform fails if
     any *fatal* > 0.

☐ 5.2 Hook: call `ValidationContext` inside BaseTransformer `post_normalise()`
     when `self.mapping_spec.get("validate", True)`.

6  Testing Plan 🧪
~~~~~~~~~~~~~~~~~~~
**Folder structure**
```
tests/
  ├─ unit/
  │   ├─ test_yaml_mapper.py
  │   └─ test_registry.py
  ├─ integration/
  │   └─ test_transform_end_to_end.py
  └─ data/
      └─ sample_patient_bundle.json
```

Unit Tests
-----------
☐ 6.1 `test_yaml_mapper.py` – load sample Observation bundle → expect
     columns listed in YAML all present & non-null.

☐ 6.2 `test_registry.py` – call `get_transformer(spark, "Patient")` with
     and without custom override; assert class type.

Integration Tests
------------------
☐ 6.3 Spin local Spark, run full Bronze → Silver on sample bundles with
     `--mock` mode.
     Assertions:
     • row counts equal number of entries in bundle.
     • no duplicate `_hash_id`.
     • all expected columns exist.

Smoke Test in Foundry CI
-------------------------
☐ 6.4 `.foundryci.yaml` runs:
```
pip install -r requirements.txt
pytest -m "unit or integration" --cov=fhir_pipeline --cov-fail-under=85
```

Data-Loss Guardrails
~~~~~~~~~~~~~~~~~~~~
☐ 6.5 During transform, compute `input_count` vs `output_count`.
     Add metric `loss_pct` = (in - out)/in. Fail if >5 %.

7  Production-Readiness Checklist
---------------------------------
☐ 7.1 Logging: `utils/logging.py` – JSON logs include `resource_type`,
     `record_count`, `loss_pct`.
☐ 7.2 Secrets: JWT private key from Foundry secret store.
☐ 7.3 Retention: set Bronze 90d, Silver 1y in dataset manifests.
☐ 7.4 Scalability: spark write .repartition(200) if rows > 10 M.
☐ 7.5 Failure Retry: Foundry transform profile `max_retries: 3`.

8  Palantir Workflow Hook-up
---------------------------
No manifest changes needed! The driver still loops over `resource_type`,
but now **any new YAML under `generic_mappings/` auto-enables a resource**.
For an exotic resource, just add YAML and push code – Foundry detects new
inputs & outputs via dataset names.

9  Final Acceptance Tests
------------------------
☐ 9.1 Run workflow in DEV with 3 resources → ensure Silver tables appear.
☐ 9.2 Add new YAML `DiagnosticReport.yaml`, re-run extract+transform –> new
     dataset `/silver/fhir_normalized/diagnosticreport` appears with >0 rows.
☐ 9.3 Look at `/metrics/validation_results` – no fatal errors.

10  Done 🚀
-------------------------------------------------
When every checkbox is ticked, you can ingest **any** FHIR resource into
Silver by *only* committing a YAML mapping. The transform layer remains
Spark-native, validated, thoroughly tested, and ready for Gold and LLM
embedding steps.

════════════════════════════════════════════════════
11  PRODUCTION-GRADE DEEP-DIVE (add-on) 🏭
════════════════════════════════════════════════════
The previous checklist shows **what** to build; this add-on explains **how**
to reach *enterprise-grade* quality — security, scalability, refs, and
Foundry conventions.

11.1  Generic YAML Mapping ‑ Full Specification
------------------------------------------------
```
# config/generic_mappings/Observation.yaml
resourceType: Observation            # validated against bundle
version: 1                           # bump → triggers schema migration
validate: true                       # ValidationContext ON/OFF
columns:
  # column_name   :   fhirPath | literal | jinja2-template
  observation_id : id
  patient_id     : subject.reference.replace('Patient/','')
  code_code      : code.coding[0].code
  code_system    : code.coding[0].system
  issued_datetime: issued
  value          : valueQuantity.value | valueString | valueCodeableConcept.text
  narrative      : text.div             # XHTML → strip_html in mapper
extras:
  partition_by   : [issued_year]        # spark.write.partitionBy
```
🔰 *fhirPath or Jinja2?*  Simple paths handled by our mini-parser; if you
start with `{{` it becomes a Jinja2 template rendered per row (slow but
flexible).

11.2  `yaml_mappers.apply_mapping()` Pseudocode
----------------------------------------------
```python
from pyspark.sql.functions import col, expr, lit
from fhirpathpy import evaluate as fhir_eval   # new dep

HTML_TAG_RE = re.compile('<.*?>')

def apply_mapping(df, spec):
    for col_name, rule in spec['columns'].items():
        if rule.startswith('{{'):          # Jinja2 template
            df = df.withColumn(col_name, render_template(rule))
        elif '|' in rule:                  # fallback list
            choices = [r.strip() for r in rule.split('|')]
            exprs = [safe_fhir(col('resource'), p) for p in choices]
            df = df.withColumn(col_name, coalesce(*exprs))
        elif rule.startswith('"'):        # literal string
            df = df.withColumn(col_name, lit(rule.strip('"')))
        else:                              # direct FHIRPath
            df = df.withColumn(col_name, safe_fhir(col('resource'), rule))
    return df
```
Performance: resolve FHIRPath once → generate Column expressions via
`fhirpath-spark` or fallback UDF if unsupported; avoid row-level Python.

11.3  Validation Rules Examples
-------------------------------
`config/validation_rules.yaml`
```yaml
Patient:
  - rule: required
    paths: [id, name[0].family, birthDate]
  - rule: regex
    path: gender
    pattern: "^(male|female|other|unknown)$"
Observation:
  - rule: allowed_codes
    path: code.coding[0].system
    codeset: loinc_systems
```
`validation/core.py` loads & applies.

11.4  Dataset Manifests (Foundry)
---------------------------------
For every Silver table we emit a Dynamic Manifest in YAML next to the
transform file:
```yaml
name: fhir_normalized_observation
format: delta
partitionColumns: [issued_year]
retention:
  expiration: 365d
  stage: Silver
schemaEvolution: true
permissions:
  - principal: ROLE_HEALTH_ANALYST
    actions: [READ]
```
The transform writes to `/silver/fhir_normalized/observation`, Foundry
picks up manifest → lineage complete.

11.5  Incremental & Idempotent Writes
-------------------------------------
• Make `_hash_id` (`sha256(resourceType + id)`) the Delta primary key.
• Enable Delta *Merge* mode instead of overwrite: `merge into ... when
matched update set * when not matched insert *`.
• Use `_lastUpdated` cursor from API → only new/changed bundles fetched
(per resource).

11.6  High-Volume Performance Tips
----------------------------------
• Before calling `_apply_mapping`, cache the exploded bundle DF.
• Repartition by `resourceType` and date to avoid skew.
• Use `spark.sql.autoBroadcastJoinThreshold = -1` to avoid unexpected
  huge broadcast when joining links.
• For >1 B rows, enable ODS (Foundry Object Delta Storage) tier.

11.7  Observability Dashboards
------------------------------
Add transform `pipelines/07_metrics_aggregate.py` that rolls up metrics
into
```
/monitoring/pipeline_metrics (dataset)
   - date, resource_type, records_in, records_out, loss_pct
```
Power Foundry *Health Graph* or Tableau dashboard.

11.8  CI / CD Workflow
----------------------
1. Git push → GitHub Actions run unit tests and `foundry ci` dry-run.
2. Merge → Foundry Code Repo auto-build; if `.foundryci.yaml` passes, a
   *Release Candidate* is created.
3. Promote to PROD with change ticket; dataset manifests auto-propagate.

11.9  Security Enhancements
---------------------------
• All temp files stored in `/tmp/epic_<run_id>` and deleted at job end.
• `epic_token.json` never written in PROD; use in-memory Secret.  Local
  dev continues to allow file-based token for convenience.
• Add `utils/pii_redactor.strip_html(text)` to purge HTML tags & protect
  against XSS if narratives displayed in web apps.

11.10  Disaster Recovery Playbook
---------------------------------
• Bronze raw files are immutable → any Silver/Gold corruptions can be
  recreated by re-running transform chain for affected date range.
• Keep Git tag & dataset snapshot mapping in `docs/lineage_manifest.md`.

════════════════════════════════════════════════════
With these additions, the blueprint now covers **code, configuration,
quality, performance, security, and ops**—everything needed to deploy a
modular, any-resource FHIR transform layer confidently into your
`epic-fhir-integration` project and Palantir Foundry.

════════════════════════════════════════════════════
12  REAL-WORLD TESTING & ROBUST LOGGING 🔍
════════════════════════════════════════════════════
The pipeline must be exercised **against the live Epic Sandbox** before PROD cut-over.
This section adds the pieces still missing: on-sandbox integration tests,
traceable structured logs, and debug toggles.

12.1  Live-Sandbox Integration Tests
-----------------------------------
☐ 12.1.1  Create `tests/live/` (excluded from default CI via marker).

*`tests/live/test_epic_sandbox_extract.py`*
```python
import os, pytest, json
from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.io.fhir_client import FHIRClient

SANDBOX_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"  # Epic doc example
pytestmark = pytest.mark.live

@pytest.fixture(scope="module")
def sandbox_client():
    client = FHIRClient(
        base_url=os.environ["EPIC_BASE_URL"],
        token_client=JWTClient(
            client_id=os.environ["EPIC_CLIENT_ID"],
            private_key=os.environ["EPIC_PRIVATE_KEY"],
        ),
    )
    return client

def test_patient_pull(sandbox_client):
    bundle = sandbox_client.get(f"Patient/{SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Patient"
    assert bundle["id"] == SANDBOX_PATIENT_ID
```

🔰  Run with `pytest -m live` **only** when EPIC credentials are present.
Add to `.github/workflows/ci.yml`:
```yaml
- name: Live Sandbox Tests
  if: env.EPIC_CLIENT_ID != ''
  run: pytest -m live
```

12.2  End-to-End Sandbox Smoke
------------------------------
☐ 12.2.1  Script `scripts/run_sandbox_smoke.sh`
```
export EPIC_CLIENT_ID=…
export EPIC_PRIVATE_KEY="$(cat key.pem)"
python run_local_fhir_pipeline.py \
  --patient-id $SANDBOX_PATIENT_ID \
  --steps token,extract,transform,gold --debug
```
Assert exit code 0 + inspect `/local_output/silver/...`.

12.3  Chaos / Resilience Tests
------------------------------
☐ 12.3.1  Kill network mid-extraction (`tc qdisc`) — confirm retry logic.
☐ 12.3.2  Inject 500 errors via `responses` library mock — verify back-off.
Store results under `tests/perf/chaos_report.md`.

12.4  Structured Logging & Debugging
------------------------------------
☐ 12.4.1  `utils/logging.py`
```python
from pythonjsonlogger import jsonlogger
import logging, uuid, os

def get_logger(step: str, level: str = "INFO", **ctx):
    logger = logging.getLogger(step)
    if logger.handlers:  # already configured
        return logger
    handler = logging.StreamHandler()
    fmt = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(level)
    # static context
    logger = logging.LoggerAdapter(logger, {
        "run_id": os.environ.get("RUN_ID", str(uuid.uuid4())[:8]),
        **ctx,
    })
    return logger
```
Every transform obtains a logger at top-level:
```python
logger = get_logger(__name__, resource_type=res_type)
```

☐ 12.4.2  Debug Mode
   • `DEBUG=true` env enables `logger.setLevel("DEBUG")` + stores first
     100 input rows to `/tmp/debug_<step>.json` for inspection.
   • Never enabled in PROD.

12.5  Log & Metric Shipping
---------------------------
☐ 12.5.1  Foundry "Lineage Events" already capture metrics; still, forward
   critical errors to Slack/Jira via `utils/alerting.py` stub (webhook URL
   in secret store).
☐ 12.5.2  Add transform `pipelines/08_log_shipper.py` that reads last run's
   `/monitoring/pipeline_metrics` and pushes summary to Ops channel.

12.6  Compliance Checklist
--------------------------
✓ PHI masked in logs (verify via regex in unit test). 
✓ Audit-ready access token usage — store hashed `jti` only.
✓ All external calls (Epic) timeout in ≤ 60 s; retries max 3.

With **Section 12** in place we now have:
• Live-API tests, smoke scripts, chaos verification. 
• End-to-end debug mode. 
• Structured JSON logs with correlation IDs. 
• Alerting hooks.

That closes the last gaps on reliability, visibility, and validation for a
truly production-ready modular FHIR transform pipeline. 🎯

════════════════════════════════════════════════════
13  SILVER → GOLD + LLM SELF-CHECK LOGIC ✨
════════════════════════════════════════════════════
This final section defines how to turn clean Silver tables into **LLM-ready
Gold datasets** and introduces an automatic *code-self-audit* step where
an LLM validates the produced code artefacts before promotion.

13.1  Gold Transform Objectives
--------------------------------
• **Patient Narrative**: single row per patient summarising demographics,
  conditions, meds, most-recent vitals.
• **Temporal Timeline**: exploded rows (patient_id, event_time, text)
  ordered for RAG chunking.
• **Encounter KPI View**: per encounter length-of-stay, diagnosis count.

13.2  Implementation Files
--------------------------
```
pipelines/gold/
  ├── patient_summary.py
  ├── patient_timeline.py
  └── encounter_kpi.py
pipel ines/gold/patient_summary.yml    (manifest already exists)
pipel ines/gold/patient_timeline.yml   (new)
pipel ines/gold/encounter_kpi.yml      (new)
```

*`patient_summary.py`* (skeleton)
```python
from pyspark.sql import functions as F
from fhir_pipeline.utils.logging import get_logger

def create_patient_summary(spark, inputs, output):
    logger = get_logger(__name__)
    patient  = inputs[0].dataframe()       # /silver/fhir_normalized/patient
    cond     = inputs[1].dataframe()       # condition (optional)
    obs      = inputs[2].dataframe()       # observation (optional)
    meds     = inputs[3].dataframe()       # medicationrequest (optional)

    demo = patient.select("patient_id", "patient_summary_text")
    dx   = (cond.groupBy("patient_id")
                 .agg(F.collect_set("clinical_text").alias("dx_list")))
    vit  = (obs.filter("code_system = 'http://loinc.org'")
                .withColumn("rn", F.row_number().over(
                        Window.partitionBy("patient_id", "code_code")
                              .orderBy(F.col("issued_datetime").desc())))
                .filter("rn = 1"))
    vit_pivot = vit.groupBy("patient_id").pivot("code_code").agg(F.first("value"))

    meds_tbl = (meds.groupBy("patient_id")
                     .agg(F.collect_set("clinical_text").alias("med_list")))

    summary = demo.join(dx, "patient_id", "left") \
                  .join(vit_pivot, "patient_id", "left") \
                  .join(meds_tbl, "patient_id", "left")

    summary.write.format("delta").mode("overwrite").save(output.path)
    logger.info(f"Wrote {summary.count()} patient summaries → {output.path}")
```

*`patient_timeline.py`* (uses Silver & links)
```python
from pyspark.sql import functions as F

def create_patient_timeline(spark, inputs, output):
    obs  = inputs[0].dataframe()
    cond = inputs[1].dataframe()
    enc  = inputs[2].dataframe()

    def _prep(df, ts_col):
        return df.select("patient_id", F.col(ts_col).alias("event_time"),
                         "clinical_text")

    timeline = _prep(obs,  "issued_datetime") \
             .unionByName(_prep(cond, "onset_datetime")) \
             .unionByName(_prep(enc, "start_datetime"))

    timeline = timeline.orderBy("patient_id", "event_time")
    timeline.write.format("delta").mode("overwrite").save(output.path)
```

13.3  Gold YAML Manifests (example timeline)
-------------------------------------------
```yaml
apiVersion: 1.0.0
kind: Transform
name: gold-patient-timeline
file: pipelines/gold/patient_timeline.py
entrypoint: create_patient_timeline
inputs:
  - path: /silver/fhir_normalized/observation
  - path: /silver/fhir_normalized/condition   # optional
  - path: /silver/fhir_normalized/encounter   # optional
outputs:
  - path: /gold/patient_timeline
resources:
  memory: 12Gi
schedule:
  after: gold-patient-summary
```

13.4  Embedding Transform Consumes Gold Timeline
------------------------------------------------
`pipelines/06_embeddings.py` already targets `/gold/patient_timeline` → no
change; just ensure manifest ordering (after this new timeline step).

13.5  LLM Code Self-Audit Step 🤖
--------------------------------
Add final transform `pipelines/09_llm_code_audit.py` that:
1. Reads code files changed in current commit (passed by env var).
2. Uses OpenAI / Palantir AIP model to review diff for
   – syntax errors, – missing imports, – TODO comments.
3. Emits report dataset `/monitoring/code_audit_results` with columns
   `file, risk_level, message`.
If any `risk_level = "high"`, the transform raises Exception → workflow
fails before production publish.

CI Hook in `.foundryci.yaml`:
```yaml
- name: LLM Code Audit
  run: python pipelines/09_llm_code_audit.py --commit $GIT_COMMIT
```

Security: code file content is truncated to 30 kB and masked for secrets
before sending to LLM.

13.6  Acceptance Criteria
-------------------------
✓ `/gold/patient_summary` row-per-patient table exists.  
✓ `/gold/patient_timeline` ≥ 1 row per event.  
✓ `/gold/encounter_kpi` exists (not detailed here but similar).  
✓ Embedding transform runs after timeline and produces vectors.  
✓ LLM Code Audit passes with **no high-risk findings**.  
✓ All tests (unit, integration, live, chaos) green.

════════════════════════════════════════════════════
This append-on completes the journey: data flows **Bronze → Silver → Gold →
Embeddings**, with an automatic LLM sanity-check gate before PROD.

════════════════════════════════════════════════════
14  ROADMAP & FUTURE-PROOFING 🚀
════════════════════════════════════════════════════
This optional section captures *forward-looking* considerations that
won't block MVP but will save months later when Atlas scales to multiple
hospitals, new FHIR versions, or new AI models.

14.1  Multi-Tenant & Multi-Org Design
-------------------------------------
• **Tenant column** – Add `hospital_org_id` to every Bronze → Gold table
  so a single Foundry deployment can host multiple customer orgs while
  preserving row-level isolation.
• Foundry entitlements: entitle on `hospital_org_id=pipeline_context.org`.
• Token exchange: FastAPI uses *audience* claim to pick the correct
  Foundry tenant when running in a shared cluster.

14.2  FHIR Version Evolution (R4 → R5 → US Core)
-----------------------------------------------
• Keep `fhir_version` column (already defined §11.4).  Add view
  `Patient_latest` selecting the *max(version)* per id.
• Write automated schema diff tests (R4 vs R5) so pipeline fails fast
  if the EHR flips versions without notice.
• Maintain mapping YAML `version_overrides.yaml` for breaking enum moves.

14.3  Feature Flags & Canary Releases
-------------------------------------
• Use `utils/feature_flags.py` reading a Foundry Config dataset to toggle
  new resource types or AI models at runtime.
• Gold transforms respect `FF_ENABLE_TIMELINE` before writing timeline
  dataset—helps phased rollout.
• In Kubernetes, deploy **Argo Rollouts** canary; 5 % traffic for new AI
  model before full cut-over.

14.4  Model & Prompt Governance
------------------------------
• Register every model + prompt template in `/config/model_registry.yaml`
  with metadata (base_model, size, PHI_permitted, owner, last_eval).
• Weekly job `pipelines/10_prompt_eval.py` runs test harness (i.e.
  unit → diff match) comparing new model vs prod baseline; writes to
  `/monitoring/model_eval_results`.

14.5  Audit & Explainability
---------------------------
• Store LLM input & output *hashes* (not raw) with pointer to PHI-less
  redacted prompt in Foundry Audit dataset; keeps traceability without
  leaking PHI.
• Add `/explain/{interaction_id}` endpoint returning chain-of-thought or
  retrieval chunks for regulatory audits.

14.6  Disaster-Recovery & Data-Governance
----------------------------------------
• Bronze raw stored in dual-region; Silver/Gold enable Delta **Change
  Data Feed** so we can roll forward/back without re-processing full
  history.
• Quarterly "table restore" fire-drill using CDF to reconstruct a random
  day—automated via `scripts/restore_test.sh`.

14.7  Internationalisation & Locale
-----------------------------------
• Store `locale` column in patient & observation; vital for date formats
  when scaling outside US.
• Prompt templates use ICU DateFormatter so LLM text matches locale.

14.8  Compliance Pipeline for Emerging Regs (e.g., EU AI Act)
-------------------------------------------------------------
• Tag every AI interaction with risk tier; add DPIA docs template in
  `/docs/compliance/dpia_template.md`.
• Maintain inventory of third-party models/APIs with data residency &
  licensing.

14.9  Performance Budget Growth Plan
------------------------------------
| Year | Expected Patients | Bronze Size | Silver Rows | Infra Plan           |
| ---- | ---------------- | ----------- | ----------- | -------------------- |
| 2025 | 1 M              | 4 TB        | 20 B        | Spark 64 workers     |
| 2026 | 10 M             | 40 TB       | 200 B       | Foundry ODS + Hudi   |
| 2027 | 50 M             | 200 TB      | 1 T rows    | Databricks Photon +
                                                  **LLM summarisation
                                                  caching** |

This roadmap ensures the architecture outlives the first release and
scales with new hospitals, FHIR versions, and evolving AI governance
rules.