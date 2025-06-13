Atlas Tech stack

Layer
What You’re Proposing
Strengths
Gaps / Risks
Fast‑Fix Recommendations
1. Data connectors & staging
Pretend Foundry connectors by loading the open‑source SMART on FHIR sample bundle.
✔ Lets you prototype immediately.✔ Schema identical to “real” Epic/Cerner FHIR endpoints.
• SMART sample is tiny, synthetic, non‑longitudinal – edge cases (e.g. multi‑encounter, device, imagingStudy) absent.• No PHI—great for dev, but production queries (e.g. encounter.date ranges) may break.
▸ Add one or two larger synthetic sets (e.g. Synthea) to stress‑test.▸ Stand up a dummy FHIR server in Foundry’s Live Data Connections so the switch to prod is a 1‑line endpoint change.
2. Ontology design in Foundry
Map each FHIR resource (Patient, Encounter, Observation …) to an Ontology entity, then expose via Object Sets.
✔ Leverages Foundry’s semantic layer—downstream pipelines stay stable even if underlying tables move.
• Over‑mapping can hurt performance; you rarely need all 140+ FHIR resources.• Version drift: R4 → R5 breaks enum values.
▸ Start with the “90 % workflow” (Patient, Encounter, Observation, Condition, MedicationRequest).▸ Keep a version column and a one‑time upgrade script for R5.
3. Transformation & pipelines
Use Foundry Code Workbooks (PySpark/SQL) to flatten FHIR → LLM‑ready JSON chunks.
✔ Scalable & testable; Spark handles big EHR volumes.✔ Foundry’s lineage + scheduling = prod‑ready.
• FHIR is deeply nested; naive flattening explodes row counts → cost.• Need PHI minimization + provenance tags for HIPAA.
▸ Write unit tests for each transformation (pytest + Foundry test runner).▸ Stage “small, medium, large” sample runs to benchmark cost.▸ Embed a redaction step that strips 18 HIPAA identifiers early.
4. Retrieval & LLM injection
Serve flattened records to the IDE for real‑time prompt construction.
✔ Keeps prompt context close to the user workflow.
• Prompt size & token cost can spike (clinician asks for “last 5 yrs”).• Context spill risk if multiple patients open tabs.
▸ Implement a vector or key‑value cache (e.g. Foundry Search/FSQ) so IDE pulls only relevant slices.▸ Enforce single‑patient context via URL scoping & Foundry ACLs.
5. Front‑end IDE (React + GitHub FS)
React app reads/writes files in a GitHub repo, mimicking VS Code.
✔ Zero infra to host; devs know GitHub.
• Latency for every file read → sluggish UX.• GitHub rate limits; offline mode unavailable.• OAuth scopes must not clash with PHI.
▸ Cache files in browser IndexedDB; sync on save.▸ Consider using Foundry Code Repository API instead of GitHub once you move in‑house.
6. Security & compliance
Dev phase uses non‑PHI, so low risk.
✔ Good division of dev vs prod data.
• When you flip to prod, you’ll ingest PHI—requires HIPAA BAA, audit logging, row‑level security, disaster recovery.
▸ Engage compliance now: decide on Foundry’s Data Protection Policy objects & row‑level entitlements.▸ Build an anonymized shadow pipeline for analytics to avoid PHI where not needed.
7. DevOps & CI/CD
Use GitHub Actions for React; Foundry’s internal CI for pipelines.
✔ Clear separation.
• Two CI systems can diverge; version skew.
▸ Add a mono‑repo pattern: infra‑as‑code (Foundry YAML) + React in same repo so a single PR tests both.

Tier	Source	What You Get	Why It’s Valuable	Quick How‑To in Foundry
1 – Large‑scale synthetic generators	Synthea (MITRE) • 100 k + fully longitudinal patients, all major resources (Patient → ImagingStudy) in R4, STU3, DSTU2 • Optional DICOM, genomics, notes	Big enough to surface pagination, partitioning, and rare resources while remaining PHI‑free	- Clone or download from GitHub.- Edit synthea.properties → set exporter.fhir.bulk_data = true to emit NDJSON bulk FHIR.- Run ./run_synthea -p 50000 massachusetts for 50 k MA patients.- Point a Foundry Bulk FHIR ingest pipeline at the NDJSON folder.	
2 – Tutorial‑size bundles	SMART‑on‑FHIR generated‑sample‑data repo • < 30 patients as transaction Bundles, 1 file / patient	Perfect for unit tests, Notebook tutorials, and ontology prototyping	- git clone the repo.- Drag the Bundles into a Foundry DataSet; mark format = json.- Use a schema‑by‑example transform to explode Bundle → resource rows.	
3 – Public test servers	HAPI FHIR R4 demo, HL7 Public Server list	Always‑on endpoints to exercise OAuth, paging, _include, and $export	- Add a Live Data Connection → FHIR Server in Foundry, point to https://hapi.fhir.org/baseR4.- Schedule nightly sync of changed resources; Foundry keeps lineage.	
4 – De‑identified real‑world claims	CMS Blue Button 2.0 sandbox • 64 M Medicare beneficiaries; rich ExplanationOfBenefit, Condition, Medication	Brings real code density (ICD‑10, NDC, CPT) and multi‑year histories	- Register a sandbox app → obtain client‑ID/secret.- Use Foundry’s OAuth Client connector to call /bulk or patient‑level endpoints; export to NDJSON for scale.	
5 – Research clinical EHR exports	MIMIC‑FHIR (requires PhysioNet credential)	ICU & inpatient data mapped to FHIR R4—excellent for LLM clinical reasoning tests	- After approval, download the parquet/JSON bundles.- De‑identify tagging already done; still keep Foundry row‑level ACLs.	(offline dataset—no public URL to cite)
6 – Bulk‑data tooling	Google bulk_fhir_tools or AWS FHIRWorks sample scripts	CLI utilities to pull $export from any server and write NDJSON shards	- Use for scheduled delta exports from Tier 3/4 servers.- Drop NDJSON directly into a Foundry Dataset partitioned by date.	
Step	What to do	Why it matters
a. Land & map the data	Pipeline: Ingest Synthea or live feed → store raw *.ndjson in a Foundry dataset → run a PySpark transform that parses each resource and writes to Ontology object types (Patient, Encounter, Observation …).	Keeps the original JSON for audit, but gives you typed objects the API can page through.
b. Publish an Object Set per resource	Create patient_all, encounter_byPatient, etc. via the Object Set API.	Object sets are first‑class pageable collections.
c. Turn on paging tokens	When you later call POST /ontologies/{ont}/objectSets/loadObjects, include { "pageSize": 250 }. The response body returns nextPageToken.	
d. Harden with param‑driven filters	Accept query params (patientId, dateRange) and build an Object Filter inside the request body so the API only pages over the minimal slice.	

Layer	Chosen Tooling	Key Role	Why This Choice Fits a FHIR‑on‑Foundry IDE
Foundry Backend	Palantir Foundry Ontology + Object‑Set / GraphQL APIs	Stores cleaned FHIR R4 data with row‑level ACL; serves queries to apps.	Native security & lineage; GraphQL connector gives fine‑grained, low‑latency reads.
Python Service Tier	FastAPI (async)with palantir‑platform‑python SDK	Acts as a thin “data proxy” between IDE and Foundry (adds auth, pagination, PHI redaction, NDJSON streaming).	Keeps Foundry creds out of browser; returns FHIR JSON or Pandas on demand.
IDE Runtime (browser)	code‑server (VS Code Web OSS) image+ Cursor extension or Copilot‑chat for AI coding	Gives users familiar VS‑Code UI with inline AI suggestions and slash‑commands (e.g. /fhir Patient 123 labs).	code‑server is open‑source & self‑hostable; Cursor/Copilot provide GPT‑4‑level autocompletion.
AI Model / RAG Layer	• OpenAI o4‑mini‑high (private endpoint)• Vector index in Redis or Foundry Search	Generates code/help text; retrieves patient‑specific snippets to inject into prompts.	Keeps latency < 200 ms; embeddings stay inside VPC to avoid PHI leak.
Front‑End Helpers	React / Monaco WebView Side‑bar	Displays schema explorer, patient context chips, prompt templates.	Reduces “blank canvas” anxiety for clinicians.
Container & Infra	Docker + Kubernetes (Dev & PHI namespaces)Istio mTLS	Runs one IDE pod per user; isolates PHI traffic; auto‑scales.	
CI/CD & DevOps	GitHub Actions (image build) + Foundry CI (pipeline tests) + ArgoCD (K8s deploy)	One PR rebuilds IDE, reruns Spark transforms, and promotes to staging.	

How the Pieces Work Together
	1.	User logs in via SSO → a code‑server pod boots with their Git repo mounted.
	2.	They type /fhir patient 42 meds in the command palette.
	3.	The VS‑Code extension calls the FastAPI proxy, which:
	1.	exchanges the user’s OAuth token for a Foundry JWT;
	2.	queries the Ontology via GraphQL (patient(id:42){medicationRequests{...}});
	3.	streams results back as NDJSON.
	4.	The extension inserts the JSON, or an in‑memory Pandas frame, into the editor; Cursor/Copilot suggest transformation code (df.groupby('genericName')…).
	5.	Saving triggers GitHub Actions → image rebuild → Foundry CI run on Synthea + smoke‑PHI datasets → ArgoCD rollout.

Path	What You Ship	Up‑front Effort	Key Pros	Key Cons / Caveats
A. Re‑package Code ‑ OSS	• Your own Docker image compiled from the MIT‑licensed VS Code source.• Custom icon set, colour theme, and a Healthcare Toolkit extension‑pack (FHIR Intellisense, Foundry helper CLI, SMART‑on‑FHIR auth panel).	⚙️ Medium (need CI job that tracks upstream tags & rebuilds).	• No Microsoft branding or marketplace lock‑in.• Full UI control—can hide menus, add fixed left‑hand “Patient Context” sidebar.• MIT licence lets you redistribute freely.	• You must self‑host a private extension registry; cannot legally auto‑download Microsoft‑published marketplace extensions.
B. Use code‑server as a base	• code‑server (VS Code in the browser) from Coder + your extension‑pack.• Thin React shell that adds healthcare banners, SSO, and telemetry.	⚡ Low (just extend existing container).	• Already battle‑tested for multi‑user K8s; websockets & HTTPS built‑in.• Keeps pace with upstream VS Code automatically.	• Still uses Code‑OSS core, so same marketplace limitation.• UI theming limited to what VS Code APIs expose—deep Electron changes not possible.
Code ‑ OSS” build of VS Code (or the ready‑made code‑server container) in your own healthcare‑themed shell, then add custom extensions and side‑panels.  This gives you 95 % of VS Code’s features plus your own UX, while you avoid the cost and complexity of writing an editor from scratch.

Recommendation

Wrap, don’t rebuild. Fork Code‑OSS or base on code‑server, brand it with a healthcare shell, and enforce HIPAA‑grade controls through:
	1.	Private extension registry (so only vetted healthcare extensions install).
	2.	Server‑side redaction & audit proxy for any AI request.
	3.	Kubernetes namespace isolation for PHI sessions.

This path keeps you focused on clinical features (FHIR autocomplete, Foundry queries, patient context visualisation) instead of editor plumbing, while remaining inside an open‑source, licence‑friendly stack you can harden for healthcare use.

Area	Pitfall	Guardrail
Marketplace	Code‑OSS cannot fetch extensions from Microsoft’s store.	Host your own Azure‑Blob static gallery or use open-vsx.org; bake required VSIX into the image.
Iframe CSP	VS Code uses blob: and web‑workers; strict CSP can break it.	Configure Nginx Content-Security-Policy to allow worker-src blob: and script-src 'self' 'unsafe-eval'.
PostMessage security	Any site can send window.postMessage.	Check event.origin and embed a random session nonce in every payload.
Perf on large JSON	Dropping big FHIR blobs straight into the editor can freeze UI.	Stream preview in Side‑panel, and only insert a small code stub or file link.
Accessibility	Clinicians may use tablets; ensure sidebars are responsive and keyboard‑navigable.	Leverage Chakra UI / MUI for accessible React components; audit with Lighthouse.

Below is an end‑to‑end playbook for wrapping the browser build of Code ‑ OSS in your own React “chrome.”  The result is a single‑page web app that feels like your branded healthcare IDE, yet still delivers the full VS Code experience inside.

Task	Command / Setting	Notes
Clone Synthea	git clone https://github.com/synthetichealth/synthea.git && cd synthea	
Turn on bulk FHIR R4	Edit src/main/resources/synthea.properties → set\nexporter.fhir.bulk_data = true\nexporter.fhir.export = r4\n	Enables NDJSON export in the official Bulk Data format.
Simulate patients	./run_synthea -p 50000 massachusetts	Creates 50 k longitudinal patients—large enough to hit edge cases.
Result	output/fhir_r4/…/*.ndjson	One file per resource type (Patient.ndjson, Encounter.ndjson…).

2  Load the NDJSON into Foundry
	1.	Create a Dataset
Data Catalog → New Dataset → Upload Folder → select output/fhir_r4
(or FoundryCLI upload if you script it).
	2.	Set file type = NDJSON on every resource partition; Foundry will treat each line as a JSON object.
	3.	Add logical partitions
Folder path: /synthea_fhir/Patient/… etc.
This keeps Spark reads efficient (WHERE resourceType = 'Patient').
	4.	Mark the dataset “non‑PHI” so synthetic data remains segregated from future real PHI.


Step	Foundry UI action
Ontology → Add Entities	Patient, Encounter, Observation, Condition, MedicationRequest…
Source mapping	For Patient, map synthea_fhir.Patient.<json> to attributes (id, name[0].given[0], birthDate …).
Add version metadata	New column fhir_version = 'R4' so R5 upgrade is one filter swap.
Publish Object Sets	PatientAll, EncounterAll for downstream GraphQL queries.

Key Takeaway

Treat Synthea as a drop‑in stand‑in for the hospital’s bulk FHIR export.
By structuring your Foundry ingest around R4 NDJSON ➜ Ontology ➜ Object Sets ➜ Tests, the only change when you plug into the real EHR is the connector endpoint and the dataset’s PHI flag—no pipeline rewrite required.

Don’t forget to clean up data 
1. Build a Robust FHIR Ontology
	1.	Go to Ontology Designer in Foundry.
	•	Create new Entities for Patient, Encounter, Observation, Condition, and MedicationRequest.
	•	Map each entity to the cleaned Synthea FHIR data:

1. Build a Robust FHIR Ontology
	1.	Go to Ontology Designer in Foundry.
	•	Create new Entities for Patient, Encounter, Observation, Condition, and MedicationRequest.
	•	Map each entity to the cleaned Synthea FHIR data:

Add Derived Attributes (Computed Columns)
	•	age: Calculate using DATEDIFF(CURRENT_DATE(), birthDate) / 365.
	•	is_synthetic: Pass directly from your preprocessing (true for Synthea).
	4.	Publish Object Sets
	•	PatientAll, EncounterAll, ObservationAll → these will be the entry points for all downstream apps.FHIRcast WebSockets – Receive patient-open or encounter-open events to auto‑refresh your side panel. Why a Hybrid Strategy Beats “Bulk‑only” or “REST‑only”

Volume vs. latency trade‑off – $export streams multi‑GB NDJSON directly to cloud storage without throttling each HTTP call 
FHIR Build
, but it runs asynchronously and may take hours; REST reads are instantaneous but become cost‑prohibitive at scale (millions of requests).
EHR feature parity – Nearly every certified US EHR now exposes Bulk Data per ONC regs 
FHIR Build
, yet many sites still disable it or cap file sizes; individual REST calls remain your fallback.
Foundry ingestion modes – Bulk files land in a dataset partition and feed Spark transforms cheaply 
pmc.ncbi.nlm.nih.gov
, while Live Data Connections can poll REST endpoints so Object Sets stay fresh for interactive notebooks 
Palantir
.
2  Bulk Data $export Path (Baseline + Deltas)

2.1  How it works
Authenticate once using SMART Backend‑Services JWT (no user login) 
FHIR Build
.
Kick off POST /$export with filters such as _type=Patient,Encounter,Observation&_since=2025‑05‑01T00:00:00Z 
FHIR Build
.
Poll Content‑Location until status =complete, then stream each NDJSON file URL into the /raw/fhir/ dataset.
2.2  Cloud shortcuts
GCP Healthcare API can export straight to BigQuery or Cloud Storage 
Google Cloud
.
AWS HealthLake queues async export jobs to S3 
AWS Documentation
.
Azure FHIR Service writes to Data Lake Gen2 via the same $export verb 
Microsoft Learn
.
2.3  Pros / Cons for Foundry
✅	❌
One API call moves terabytes; cheap egress if scheduled off‑peak 
Oracle Docs
Requires async polling + storage for interim NDJSON
Files already “Flat FHIR”; Spark can convert to Parquet fast 
pmc.ncbi.nlm.nih.gov
Not real‑time; typical Epic limit = once per 24 h 
OpenEMR Community
3  Per‑Resource REST Pull (Incremental, Real‑Time)

3.1  When to use
Loading new patients added since last run: GET /Patient?_lastUpdated=ge2025‑05‑16T00:00:00Z.
UI drill‑downs (e.g., “show me vitals for Mr Jones”): GET /Observation?patient={id}&category=vital-signs.
Servers without bulk: Epic sandbox accounts or small community EHRs with daily caps 
Epic on FHIR
.
3.2  Implementation tips
Parallelise: issue each resource class in its own async job; throttle to respect EHR rate limits.
Persist raw JSON in the same dataset tree as bulk (/Patient/2025‑05‑16/), then transform identically.
Topic Subscriptions push changes so Foundry writes deltas automatically (criteria=Observation?code=8867-4) 
Kodjin
.
4  Design Blueprint for Foundry Pipelines

┌──────────┐    Bulk $export (NDJSON)    ┌────────────┐
│ EHR Core │ ───────────────────────────▶│  /raw/fhir │
└──────────┘                             │  dataset   │
         ▲   REST API (Patient, Obs…)    └────────────┘
         │                                         │
         │                             Spark parse │
         ▼                                         ▼
  Live Data Connection                    Ontology Entities
  (incremental JSON)                  (Patient, Encounter…)
Baseline load – Run $export nightly; Spark transform converts NDJSON→Parquet and upserts into stg.patient, stg.observation, …
Real‑time trickle – Poll or subscribe to REST changes every 5 min, landing in a “delta” folder; merge in Spark using MERGE INTO.
Ontology view – Publish Object Sets with row‑level ACL; Foundry’s GraphQL feeds your IDE.
5  Decision Matrix

Question	Choose Bulk if…	Choose REST if…
Need historical back‑fill?	Yes – hours vs. weeks 
FHIR Build
No
Need near real‑time (<5 min)?	Not feasible	Yes, with Subscriptions 
Kodjin
EHR supports Backend‑Services?	Required	Optional
Dev sandbox, <100 patients?	Overkill	Simple & quick
Spark cluster cost a concern?	Lower cost/GB (fewer HTTP round trips)	Higher if polling many endpoints
6  Recommended Roll‑out Order

Smoke‑test REST with a single patient ($everything) for schema validation 
OpenEMR Community
.
Enable Bulk $export after getting Backend‑Services credentials from the hospital.
Set up nightly incremental $export with _since for delta loads 
Oracle Docs
.
Layer Subscriptions for high‑value signals (new labs, admits).
Auto‑generate synthetic Synthea data to unit‑test transforms while waiting for prod access.
TL;DR
Do both. Use Bulk $export for the heavy lift (historical and daily deltas) and REST/Subscriptions for the fresh edge.
Land everything as NDJSON→Parquet in Foundry, then a single Spark pipeline feeds your Ontology.
Cache CapabilityStatement on connect so the IDE smartly hides features not supported by a given EHR instance.
This pattern keeps your AI platform scalable, real‑time‑enough for clinicians, and future‑proof when EHR vendors upgrade their FHIR stacks.



 Land the Data: Hybrid Bulk $export + Incremental REST

Backend‑Services OAuth – Register a system client, publish your JWKS, and request system/*.read scope so Foundry can call the EHR unattended.
docs.smarthealthit.org
FHIR Build
Nightly bulk dump – Kick off POST /$export with _type=Patient,Encounter,Observation and (after day one) _since=<yesterday>; stream each NDJSON URL straight into /raw/fhir/YYYY‑MM‑DD/.
FHIR Build
Palantir
Five‑minute trickle – A Foundry Live Data Connection polls REST deltas like GET /Observation?patient={id}&_lastUpdated=….
Palantir
Palantir
Schema‑by‑example transform – One PySpark transform converts both NDJSON and REST JSON into Parquet tables (stg_patient, stg_encounter, stg_observation).
Palantir
Why hybrid? Bulk is cheapest for large history; REST (or Subscriptions—see §3) keeps the data fresh between dumps.
2  Publish “PatientAll / EncounterAll / ObservationAll” Object‑Sets

Step	Foundry action	Spec hook
a. Create entity types	Ontology Designer → add Patient, Encounter, Observation entities mapped to Parquet columns.	
b. Add version metadata	Computed column fhir_version = 'R4' to ease future R5 upgrade.	
c. Create object‑sets	Call the Object‑Set API to save three sets that simply SELECT * from each entity.
Palantir
Palantir
d. Expose via GraphQL	Enable the GraphQL connector so downstream apps can hit /graphql with queries like:
{ PatientAll (first:100) { id gender birthDate } }.
Palantir
e. Register in Functions	Optional: register each set as a Foundry Function input so pipeline authors can filter (.filter()) in PySpark code.	
These object‑sets become the canonical entry points every downstream notebook, KPI dashboard, or ML feature job uses—one source of truth regardless of how the data arrived.

3  Event‑Driven Auto‑Refresh with FHIRcast + Subscriptions

FHIRcast hub – Deploy (or reuse the hospital’s) WebSocket hub that emits patient-open and encounter-open events.
fhircast.org
FHIR Build
Edge microservice – A lightweight FastAPI service subscribes to the hub, captures the event JSON (Patient.id, Encounter.id), and POSTs a Foundry Webhook that pings your React side‑panel or writes a tiny row into /events/fhircast/.
Palantir
Subscription resource (optional) – If the EHR supports FHIR Subscription, register criteria=Observation?code=8867-4 to push new vitals into the same event dataset.
FHIR Build
FHIR Build
Front‑end listener – Your Foundry “IDE” front‑end (running via the GraphQL connector) listens on a Server‑Sent‑Events endpoint that streams those event rows; when it sees patient-open, it fires a GraphQL refetch against PatientAll and ObservationAll for that ID.
The result: clinicians shift charts in the EHR, and your panel refreshes without manual polling—a seamless, FHIR‑native UX.
4  Glue Code Example (pseudo‑Python)

# bulk_to_foundry.py  ── scheduled nightly
token = get_backend_jwt()
export_job = post(f"{FHIR}/$export", json={"_type": "Patient,Encounter,Observation"}, headers=token)
files = poll_until_complete(export_job)
for f in files:
    stream_to_dataset(f, "/raw/fhir/" + today)

# fhircast_listener.py  ── runs continuously
async for event in websocket.connect(HUB_URL):
    if event["type"] in ("patient-open", "encounter-open"):
        requests.post(foundry_webhook_url, json=event)

# side_panel.tsx  ── React + GraphQL
useEventSource("/events/sse", ev => {
  setPatientId(ev.patient.id)
  refetchPatient({ id: ev.patient.id })
})
5  Security, Ops & CI/CD

OAuth scopes – Live‑data REST pull uses the same Backend‑Services client; WebSocket listener holds only a narrow‑scoped user/*.read token.
Row‑level ACL – Apply Foundry entitlements on Object‑Sets so users only query patients they’re allowed to see.
CI pipeline – GitHub Action spins up a Foundry test workspace, runs Spark transform unit tests against Synthea NDJSON, and triggers ArgoCD deploy of the FastAPI listener.
Palantir
Monitoring – Use Foundry’s Exports app to push pipeline success metrics to your Grafana stack.
Palantir
6  Why This Beats “Bulk‑only” or “REST‑only”

Bulk‑only	REST‑only	Hybrid (design above)
✅ Cheapest for TBs of history,
❌ hours‑old data	✅ Real‑time,
❌ millions of calls = cost	✅ History via Bulk,
✅ Fresh via REST/Subscriptions,
✅ Event‑driven UI
Bulk for cost, REST for recency, FHIRcast/Subscriptions for UX—all surfaced through a single set of PatientAll / EncounterAll / ObservationAll GraphQL entry points. This pattern keeps your Foundry data lake tidy, your ontology stable, and your AI side‑panels instantaneous.


Below is a reproducible **“cookbook”** for wiring a nightly (or on‑demand) **FHIR Bulk Data \$export** feed straight into Palantir Foundry, landing NDJSON shards, converting them to Parquet, and publishing the **PatientAll / EncounterAll / ObservationAll** object‑sets that every downstream notebook, ML job, or React panel can query.  Follow the steps in order; each calls out the exact Foundry UI, API, or Spark transform you need and references the relevant FHIR or cloud documentation.

---

## 1  Prerequisites

| Item                                                                                                              | Why you need it                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Backend‑Services (SMART on FHIR) client** with `system/*.read` scope and a JWKS URL                             | Enables unattended server‑to‑server OAuth for the bulk job ([FHIR Build][1])                                             |
| **FHIR server that supports `$export`** (Epic ≥ Aug 2021, Cerner, GCP Healthcare API, Azure FHIR, AWS HealthLake) | Provides NDJSON output in Flat FHIR format ([Epic on FHIR][2], [FHIR Build][3], [Microsoft Learn][4], [Google Cloud][5]) |
| **Foundry project** with permission to create Datasets, Pipelines, Ontology entities, and Object Sets             | Stores, processes, and serves the data ([Palantir][6])                                                                   |

---

## 2  Kick‑off the Bulk Export Job

1. **Sign a JWT** with your client’s private key (per SMART Backend Services) and exchange it for a token. ([FHIR Build][7])
2. **POST** to the bulk endpoint—system, group, or patient—e.g.:

```http
POST https://ehr.example.com/fhir/$export
Prefer: respond-async
Authorization: Bearer {access_token}
Content-Type: application/fhir+json

{
  "_type": "Patient,Encounter,Observation",
  "_since": "2025-05-15T00:00:00Z"
}
```

*(Epic users: group‑level exports only, and one request per group per 24 h) ([Epic on FHIR][2])*
3\. Capture the **`Content-Location`** header; poll it until the JSON status manifest lists all **NDJSON file URLs**. ([Epic on FHIR][2])

---

## 3  Land Raw NDJSON in Foundry

### Option A – Cloud bucket autoload  *(fastest if using GCP/Azure/AWS)*

* Point `$export` to write directly to a Cloud Storage / S3 / ADLS Gen2 folder ([Google Cloud][8], [Google Cloud][9], [Microsoft Learn][4])
* In Foundry **Data Catalog → “New Dataset → File‑based Sync”**, choose the matching cloud‑bucket connector and schedule it **daily after the export window**. ([Palantir][6])

### Option B – Script upload  *(generic EHRs)*

```bash
# download each NDJSON file then upload with Foundry CLI
for url in $(cat manifest.json | jq -r '.output[].url'); do
  curl -H "Authorization: Bearer $TOKEN" -o $(basename $url) "$url"
  foundry dataset put raw/fhir/$(date +%F)/$(basename $url) $(basename $url)
done
```

---

## 4  Spark Transform: NDJSON ➔ Parquet

1. **Create a Pipeline** with a **Python (Pyspark)** transform.
2. Read every resource folder:

```python
from transforms.python import Transform
from pyspark.sql.functions import input_file_name, lit

class ConvertFhir(Transform):
    def transform(self, ctx):
        src = ctx.dataset("raw/fhir")         # input dataset
        out = ctx.datasets("stg_patient", "stg_encounter", "stg_observation")

        df = spark.read.json(src.path)        # Flat FHIR NDJSON :contentReference[oaicite:8]{index=8}
        (df.filter("resourceType = 'Patient'")
           .withColumn("fhir_version", lit("R4"))
           .write.mode("append").parquet(out["stg_patient"].path))  # defaults to Parquet :contentReference[oaicite:9]{index=9}
        … repeat for Encounter, Observation …
```

3. Schedule the pipeline to run **after** the file‑sync finishes.

---

## 5  Ontology & Object‑Sets

| Step | Foundry UI            | Action                                                                                                   |
| ---- | --------------------- | -------------------------------------------------------------------------------------------------------- |
| a    | **Ontology Designer** | Create entities `Patient`, `Encounter`, `Observation`; map Parquet columns.                              |
| b    | **Add computed col**  | `fhir_version` so R4→R5 upgrades are just a filter swap.                                                 |
| c    | **Object‑Set API**    | `POST /ontology/objectSets` – definitions: `SELECT * FROM Patient` etc. ([Palantir][10], [Palantir][11]) |
| d    | **GraphQL connector** | Enable so downstream apps query `PatientAll { id gender }`. ([bulk-data.smarthealthit.org][12])          |

These **PatientAll / EncounterAll / ObservationAll** sets are now the single entry‑point for every Notebook, dashboard, or AI side‑panel.

---

## 6  Automate Daily Deltas

* Change step 2 request to include **`_since`** = last successful run time ([FHIR Build][3]).
* In Foundry, create a **Schedule**:

  * 01:00 – run `$export` (EHR off‑peak)
  * 02:00 – bucket sync
  * 02:15 – Spark transform merge Parquet
* Use **Foundry Health Checks** to alert on missing partitions ([Palantir][6]).

---

## 7  (Real‑time Edge) Subscriptions + FHIRcast  *(Optional)*

* Register a **`Subscription`** for hot events (e.g., new labs) and post to a Foundry **Webhook** ([Palantir][13]).
* Listen to **FHIRcast** `patient-open` events and refresh your UI via GraphQL—zero polling latency ([Microsoft Learn][4], [FHIR Build][3]).

---

## 8  Test & Monitor

| Check             | Tool                                                                               |
| ----------------- | ---------------------------------------------------------------------------------- |
| Schema conformity | HL7 FHIR validator against NDJSON sample ([FHIR Build][3])                         |
| Row counts        | Spark unit test (`assert patient.count() > 0`)                                     |
| Export success    | Epic/X‑Progress header or GCP Operation API ([Epic on FHIR][2], [Google Cloud][5]) |
| Foundry lineage   | Dataset “View Lineage” to trace NDJSON → Parquet → Ontology.                       |

---

### Key Takeaways

* **Bulk `$export` + backend‑services OAuth** is the fastest, cheapest way to move TB‑scale FHIR into Foundry. ([FHIR Build][3])
* **NDJSON files drop straight into a file‑sync dataset**, then one Spark job converts to Parquet.
* **PatientAll / EncounterAll / ObservationAll Object‑Sets** give every downstream tool a stable contract.
* Add **Subscriptions/FHIRcast** only for truly real‑time UX needs; nightly deltas handle analytics at a fraction of the cost.

[1]: https://build.fhir.org/ig/HL7/bulk-data/authorization.html?utm_source=chatgpt.com "SMART Backend Services Authorization - Bulk Data Access IG v2.0.0"
[2]: https://fhir.epic.com/Documentation "Documentation - Epic on FHIR"
[3]: https://build.fhir.org/ig/HL7/bulk-data/export.html?utm_source=chatgpt.com "Export - Bulk Data Access IG v2.0.0 - FHIR specification"
[4]: https://learn.microsoft.com/en-us/azure/healthcare-apis/fhir/export-data?utm_source=chatgpt.com "Export your FHIR data - Learn Microsoft"
[5]: https://cloud.google.com/healthcare-api/docs/reference/rest/v1beta1/projects.locations.datasets.fhirStores.fhir/bulk-export?utm_source=chatgpt.com "Method: fhir.bulk-export | Cloud Healthcare API"
[6]: https://palantir.com/docs/foundry/data-connection/export-overview// "Data Connection • Exports • Exports • Palantir"
[7]: https://build.fhir.org/ig/HL7/smart-app-launch/backend-services.html?utm_source=chatgpt.com "Backend Services - SMART App Launch v2.2.0 - FHIR specification"
[8]: https://cloud.google.com/healthcare-api/docs/how-tos/fhir-import-export?utm_source=chatgpt.com "Import and export FHIR resources using Cloud Storage"
[9]: https://cloud.google.com/healthcare-api/docs/reference/rest/v1/projects.locations.datasets.fhirStores/export?utm_source=chatgpt.com "Method: fhirStores.export | Cloud Healthcare API - Google Cloud"
[10]: https://palantir.com/docs/foundry/functions/api-object-sets//?utm_source=chatgpt.com "API: Object sets - Functions - Palantir"
[11]: https://palantir.com/docs/foundry/api/ontologies-v2-resources/ontology-object-sets/ontology-object-set-basics//?utm_source=chatgpt.com "Ontology Object Set basics • API Reference - Palantir"
[12]: https://bulk-data.smarthealthit.org/?utm_source=chatgpt.com "SMART Bulk Data Server"
[13]: https://palantir.com/docs/foundry/pipeline-builder/export-pipeline//?utm_source=chatgpt.com "Export pipeline code - Palantir"


Below is a click‑by‑click walkthrough that starts on your GCP VM and ends with a scheduled PatientAll / EncounterAll / ObservationAll object‑set in Foundry. Follow it once end‑to‑end to prove the pipeline works; afterward you can automate the daily run with a shell script + Foundry schedule.

0  High‑level map (what you’ll do)

Create a Cloud Storage bucket that will hold the NDJSON files.
Enable Cloud Healthcare API and spin up a FHIR store (or point to an external Epic/Cerner server).
Give the Healthcare Service Agent permission to write into the bucket.
Kick off $export from your VM with one curl command (async).
Pull the NDJSON file list when the job finishes.
File‑based Sync that folder into a raw/fhir dataset in Foundry.
Spark transform NDJSON → Parquet.
Ontology Designer: map entities, publish PatientAll / EncounterAll / ObservationAll.
Schedule nightly: 01:00 export → 02:00 sync → 02:15 transform.
(Optional) wire a FHIRcast listener so your React side‑panel refreshes instantly when a clinician opens a new chart.
Everything below walks you through the exact console clicks, command lines, and Foundry UI dialogs.

1  GCP setup (once)

1.1 Create a bucket
Console → Storage ▸ Buckets ▸ Create.
Name: fhir-bulk-dumps, Region: same as your VM, Access: Uniform.
Leave Public access blocked, click Create.
1.2 Enable the Healthcare API
Console search‑bar → “Healthcare API” ▸ Enable.
Healthcare API ▸ Datasets ▸ Create Dataset
ID ehr_demo, Location = same region, click Create.
Inside the dataset click Create FHIR store
ID hospital_r4, Version R4, “GCS Notifications” unchecked, Create. 
Google Cloud
(If you’re exporting from an external Epic/Cerner endpoint you can skip the GCP FHIR store; all later steps still apply—just change the base URL.)

1.3 Grant bucket permissions to the Healthcare Service Agent
Console → IAM ▸ IAM.
Find the account ending @gcp-sa-healthcare.iam.gserviceaccount.com.
Click Edit roles ▸ + Add another role ▸ Storage Object Admin. Save. 
Google Cloud
2  Create a Backend‑Services client (once)

IAM ▸ Service Accounts ▸ Create → bulk-fhir-client.
On the details page choose Add Key ▸ JSON, download bulk-fhir-client.json.
Still on the account row click Manage Details ▸ Permissions ▸ + Grant
Role Healthcare FHIR Resource Viewer (lets it read the FHIR store).
Note the service‑account email—call it ${SA_EMAIL} below.
Open Cloud Shell or SSH to your VM and run:
export SA_EMAIL="bulk-fhir-client@$(gcloud config get-value project).iam.gserviceaccount.com"
gcloud iam service-accounts keys create /tmp/key.json --iam-account=$SA_EMAIL
Copy /tmp/key.json to your VM (or point code to it).
Create a JWKS (one‑liner):
python - <<'EOF'
import jwt, json, datetime, uuid, sys, base64, os
from cryptography.hazmat.primitives import serialization
key = serialization.load_pem_private_key(open('/tmp/key.json','rb').read(),password=None)
pub = key.public_key()
jwk = jwt.algorithms.RSAAlgorithm.to_jwk(pub)
with open('jwks.json','w') as f: f.write('{"keys":['+jwk+']}')
print("JWKS written")
EOF
Upload jwks.json to a public URL (GitHub Pages works) and record it; Google needs it to validate the JWT when you request a token. 
HL7 Confluence
3  Kick off your first $export

SSH into the VM and:

FHIR_STORE="projects/$(gcloud config get-value project)/locations/us-central1/datasets/ehr_demo/fhirStores/hospital_r4"
# 3.1 Sign JWT
EXP=$(date -u -d '+5m' +%s)
JWT=$(python - <<EOF
import jwt, json, os, time, uuid
p=json.load(open('/tmp/key.json'))
token=jwt.encode(
 {"iss":p["client_email"],"sub":p["client_email"],
  "aud":"https://oauth2.googleapis.com/token",
  "exp":$EXP,"iat":int(time.time()),
  "scope":"https://www.googleapis.com/auth/cloud-platform"},
 p['private_key'],algorithm="RS256")
print(token)
EOF)

# 3.2 Exchange it for an access token
ACCESS=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer \
  -d assertion=$JWT | jq -r .access_token)

# 3.3 Kick off export (async)
EXPORT=$(curl -s -X POST \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/fhir+json" \
  "https://healthcare.googleapis.com/v1/$FHIR_STORE/fhir/$export?_type=Patient,Encounter,Observation&_since=2025-05-15T00:00:00Z&outputFormat=application/fhir+ndjson&gcsDestination=json:$BUCKET" )
JOB=$(echo $EXPORT | jq -r .name)   # Operation name
*The call returns immediately; Google writes files like Patient.ndjson into gs://fhir-bulk-dumps/YYYY-MM-DD/. * 
Google Cloud

Monitor:

gcloud healthcare operations describe $JOB
When "done": true, list the bucket:

gsutil ls gs://fhir-bulk-dumps/$(date +%F)/
Files appear for each resource. No parsing needed—they’re already NDJSON. 
FHIR Build

4  Sync the bucket into Foundry

4.1 Create the dataset
Foundry browser → Data Catalog ▸ New Dataset.
Name raw/fhir → Create.
4.2 Add a File‑based Sync
In the dataset click + Add Data Source → File‑based Sync.
Connector = Google Cloud Storage.
Auth: select or create a Service Account Key that has Storage Object Viewer on the bucket.
Folder path: gs://fhir-bulk-dumps/*/*.ndjson
Schedule = Every day at 02:00 (after export job). Save. 
Palantir
(Foundry will now pull yesterday’s dump into partition folders—one file per resource.)

5  Transform NDJSON ➔ Parquet (clicks)

New Pipeline → Blank.
Add Dataset: choose raw/fhir.
Add Transform → PySpark
Paste the snippet below.
from transforms.python import Transform
from pyspark.sql.functions import input_file_name, lit

class BulkFhirToParquet(Transform):
    def transform(self, ctx):
        src = ctx.dataset("raw/fhir")
        out = ctx.datasets("stg_patient","stg_encounter","stg_observation")

        df = spark.read.json(src.path)    # Flat FHIR
        (df.filter("resourceType = 'Patient'")
           .withColumn("fhir_version", lit("R4"))
           .write.mode("append").parquet(out["stg_patient"].path))
        (df.filter("resourceType = 'Encounter'")
           .write.mode("append").parquet(out["stg_encounter"].path))
        (df.filter("resourceType = 'Observation'")
           .write.mode("append").parquet(out["stg_observation"].path))
Add three Output Datasets named as above; default storage = Parquet.
Schedule → 02:15 daily.
Run once to back‑fill. 
fhircast.org
6  Ontology & Object‑Sets (clicks)

Ontology Designer → + New Ontology.
Entities
Patient → Source = stg_patient, Primary Key id.
Encounter → Source = stg_encounter.
Observation → Source = stg_observation.
Save & Publish.
Object‑Set API (or UI)
PatientAll → SELECT * FROM Patient.
EncounterAll → SELECT * FROM Encounter.
ObservationAll → SELECT * FROM Observation. 
fhircast.org
Enable GraphQL connector so downstream code hits /graphql. 
SMART Health IT
7  (Extra credit) Real‑time refresh with FHIRcast

Deploy a tiny FastAPI app on the same VM that subscribes to the hospital’s FHIRcast hub.
On patient-open events the app POSTs a Foundry Webhook that writes to /events/fhircast/.
Your React side‑panel uses Foundry’s SSE endpoint to reload PatientAll when a new row arrives.
fhircast.org
fhircast.org
8  Run end‑to‑end

01:00 cron job on VM → runs script above (export.sh).
02:00 Foundry File‑based Sync pulls NDJSON.
02:15 Spark transform appends Parquet.
02:20 Object‑Sets auto‑refresh; GraphQL answers queries.
Any time you can debug a chart with GET /Patient/{id}/$everything from the VM—drop the JSON into a notebook for quick tests. 
Elation Health FHIR API
Troubleshooting tips
Symptom	Fix
403 writing NDJSON	Check bucket role for Healthcare Service Agent.
Google Cloud
Blank data in Foundry	Verify File‑based Sync filters exist /*/*.ndjson.
Operation not done after hours	Bulk export runs on operational DB; export smaller _type list or weekend schedule. 
Epic on FHIR
JWT “invalid_grant”	Exp too far in future or wrong audience; re‑sign within 5 min window. 
SMART Health IT
You’re all set

After these clicks you’ll have a zero‑touch nightly bulk pipeline that feeds Parquet tables, a stable ontology, and GraphQL entry points—ready for Spark notebooks, RAG pipelines, or an AI clinician side‑panel. As you mature, layer incremental Subscriptions for labs or admits without changing the downstream contract.







Sources


