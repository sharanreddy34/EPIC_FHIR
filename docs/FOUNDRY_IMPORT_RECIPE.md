# Epic FHIR Integration → Foundry Import Recipe Book  
_Last updated: 2025-05-22_

This document is the final, **single-source-of-truth** playbook for packaging the Epic FHIR Integration codebase and deploying it into Palantir Foundry with **zero pre-existing Foundry setup**.  
It converts every remaining ⚠ blocker from Reality-Check v4 into a concrete, repeatable step.

---
Table of Contents  
1  Quick Synopsis  
2  Prerequisites (local)  
3  Container Image Pipeline  
4  Python Wheel & Artifacts  
5  Foundry Repository Bootstrapping  
6  Secrets & Config Management  
7  Datasets & Path Abstraction  
8  Testing in Foundry  
9  CI/CD Updates  
10  Clean-up Checklist  

---
## 1  Quick Synopsis
We will deliver **one self-contained OCI image** that embeds:
* the Python package (built from `pyproject.toml`)
* Pathling server (Java 11 / Spark) running on port 8080
* HL7 FHIR Validator CLI (Java 11)

Foundry will run that image as a **Container Function**.  All runtime behaviour (API creds, dataset URIs, feature toggles) is controlled via environment variables → no code changes are required when moving between dev, staging, prod.

---
## 2  Prerequisites (local)
| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| Docker | 24.x | Build & test the image |
| Python | 3.10+ | Build wheel, run scripts |
| GNU Make | 4+ | Convenience targets |

```bash
# Build everything locally
make all          # builds validator + pathling images (layer-cached)
make foundry-img  # new target – see below
```

---
## 3  Container Image Pipeline
Add a new Dockerfile (`ops/foundry/Dockerfile`) that:
1. `FROM eclipse-temurin:11-jre` (lightweight base; Foundry also runs Java 17 so 11 is fine)
2. Installs `python=3.10` + `pip`, copies the wheel built in §4
3. Copies `ops/pathling/` → `/opt/pathling` and `ops/validator/` → `/opt/validator`
4. Exposes TCP 8080 (`Pathling`) and `validator.sh` in `$PATH`
5. Declares `ENTRYPOINT ["/entrypoint.sh"]` – a tiny bash script that
   * starts Pathling in background (`/opt/pathling/bin/pathling serve &`)
   * verifies healthcheck `curl localhost:8080/fhir/metadata`
   * execs whatever CMD Foundry passes (usually the Python CLI)

### Make target
```makefile
foundry-img:
	docker build -t epic-fhir-foundry:latest -f ops/foundry/Dockerfile .
```

### Parameterisation (ENV)
| Variable | Default | Description |
|----------|---------|-------------|
| `EPIC_BASE_URL` | — | Epic FHIR base URL |
| `EPIC_CLIENT_ID` | — | OAuth2 client id |
| `EPIC_CLIENT_SECRET` | — | secret (provided via Foundry secret) |
| `DATA_ROOT` | `/foundry/objects` | Root path for all dataset writes |
| `PATHLING_IMPORT_ENABLED` | `true` | Toggle synthetic data loader |
| `LOG_LEVEL` | `INFO` | Global logging |

---
## 4  Python Wheel & Artifacts
* **Relocate `pyproject.toml` to repo root** so `python -m build` works out-of-the-box.
* Flip heavy deps (Spark, Pandas, Pathling python bindings) into extras to keep core wheel small.

```toml
[project.optional-dependencies]
analytics = ["pyspark", "pathling"]
science   = ["pandas>=1.5.3,<2", "dask"]
```

CI job (see §9) will:
```bash
pip install build
python -m build --wheel --outdir dist/
```
Artifact `dist/epic_fhir_integration-*.whl` is then COPY-ed into the container in §3.

---
## 5  Foundry Repository Bootstrapping
Run once per environment:
```bash
foundry repo create epic-fhir-integration
cd epic-fhir-integration
foundry fs put dist/epic_fhir_integration*.whl
foundry container-image import epic-fhir-foundry:latest --name epic-fhir-tools
```
Create three **Code Functions** (or one CLI wrapper):
1. `epic-fhir-extract`  – runs extraction & writes bronze dataset
2. `epic-fhir-transform` – bronze→silver→gold
3. `epic-fhir-quality`   – runs GE & validator, produces dashboards

Each function YAML uses:
```yaml
runtime:
  kind: container
  image: epic-fhir-tools
  command: [ "epic-fhir-extract", "--output-uri", "$DATA_ROOT/bronze" ]
  env:
    EPIC_BASE_URL: "$EPIC_BASE_URL"
    # secrets mapped below
secrets:
  - name: epic-oauth-secret     # contains client_id + secret
```

---
## 6  Secrets & Config Management
1. **Delete** `epic_token.json` from Git history (git filter-repo / BFG).  
2. Create Foundry secret `epic-oauth-secret` JSON:
```json
{ "client_id": "…", "client_secret": "…" }
```
3. CLI reads via `os.environ["EPIC_CLIENT_ID"]` or fallback to secret JSON.
4. Optional YAML config file can be mounted at `/config/app.yml` (volumeMapping in Foundry).

---
## 7  Datasets & Path Abstraction
Replace all hard-coded local paths with helper:
```python
from pathlib import Path, PurePosixPath

DATA_ROOT = Path(os.getenv("DATA_ROOT", Path.cwd()))
BRONZE    = DATA_ROOT / "bronze"
SILVER    = DATA_ROOT / "silver"
GOLD      = DATA_ROOT / "gold"
```
Foundry will map `/foundry/objects` to the function scratch-space or a specified dataset.

---
## 8  Testing in Foundry
* Add `scripts/run_in_foundry_smoke.sh` which invokes `epic-fhir-extract --limit 1` and asserts no sentinel error.
* In Foundry test workspace, schedule the container once; verify Pathling healthcheck succeeds via logs.

---
## 9  CI/CD Updates (GitHub Actions)
Add job `build-foundry` _after_ unit/E2E tests:
```yaml
jobs:
  build-foundry:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: 3.10 }
      - run: pip install build
      - run: python -m build --wheel --outdir dist/
      - run: docker build -t $IMAGE_NAME -f ops/foundry/Dockerfile .
      - run: docker save $IMAGE_NAME | gzip > epic-fhir-foundry.tar.gz
      - uses: actions/upload-artifact@v3
        with: { name: foundry-image, path: epic-fhir-foundry.tar.gz }
```
Optional: add `foundry-cli` action to push directly to Foundry registry.

---
## 10  Clean-up Checklist
☐ `epic_token.json` removed & secretised  
☐ `pyproject.toml` moved to root; wheel builds  
☐ Optional deps split into extras  
☐ `ops/foundry/Dockerfile` + `entrypoint.sh` created  
☐ Hard-coded local paths replaced by `DATA_ROOT` helper  
☐ GE expectation store path switched to in-memory / S3 in Foundry  
☐ CI publishes wheel + image artefacts  
☐ Foundry repo & container functions created  
☐ README links updated (docs avail in Foundry UI)  

Once every checkbox is ✅, you can `curl` the live Epic FHIR API inside a Foundry container and the full bronze→gold pipeline will run without manual intervention. 