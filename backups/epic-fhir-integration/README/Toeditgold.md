Epic-FHIR Integration – Master To-Do List
(Organized so that any reasonably capable LLM can implement each item one-by-one without context loss. Every change must live under the top-level epic-fhir-integration/ package so the project remains pip-installable and import-clean.)
────────────────────────────────────────
A. Project-level House-Keeping - COMPLETED
────────────────────────────────────────
Module layout - COMPLETED
✅ Create epic_fhir_integration/__init__.py that re-exports high-level public APIs
✅ Move all top-level loose scripts under epic_fhir_integration/cli/ and convert to if __name__ == "__main__": CLIs (see sect. H)
Packaging - COMPLETED
✅ Ensure pyproject.toml lists epic_fhir_integration as the only Python package
✅ Add entry_points.console_scripts for every CLI created in sect. H
✅ Run pip install -e . and fix any import errors
Lint / style / CI - COMPLETED
✅ Add ruff config to pyproject (PEP-8 + isort + flake8-bandit)
✅ Add GitHub/Foundry CI step: ruff --fix . && pytest -q
────────────────────────────────────────
B. Configuration & Secrets - COMPLETED
────────────────────────────────────────
Create canonical config loader - COMPLETED
✅ File: epic_fhir_integration/config/loader.py
✅ Accept hierarchy: (1) CLI flag, (2) $EPIC_FHIR_CFG, (3) ~/.config/epic_fhir/api_config.yaml
✅ Expose get_config(section: str) -> dict
Secret handling - COMPLETED
✅ Move token & private-key files to epic_fhir_integration/secrets/
✅ Write helper epic_fhir_integration/security/secret_store.py with CRUD helpers that never print secret values
────────────────────────────────────────
C. Authentication Module - COMPLETED
────────────────────────────────────────
Rewrite auth flow into fully-tested module - COMPLETED
✅ File: epic_fhir_integration/auth/jwt_auth.py
✅ Functions: build_jwt(), exchange_for_access_token(), get_or_refresh_token()
✅ Unit-test expiry logic, 401 retry & exponential back-off
Deprecate and delete the old simple_token_refresh.py everywhere
────────────────────────────────────────
D. FHIR Client Abstraction - COMPLETED
────────────────────────────────────────
Create thin, generic FHIR client - COMPLETED
✅ File: epic_fhir_integration/io/fhir_client.py
✅ Accept base_url, access_token, resource_type, params
✅ Return raw JSON; separate adapter handles Spark DF conversion
Implement rate-limit & pagination helpers - COMPLETED
✅ Auto-fetch Bundle.link[rel="next"] until exhausted or row limit hit
✅ 429 handler with Retry-After header support
────────────────────────────────────────
E. Extraction Layer (Bronze) - COMPLETED
────────────────────────────────────────
Make resource-agnostic extractor class - COMPLETED
✅ epic_fhir_integration/extract/extractor.py – subclass per resource
✅ CLI (see sect. H) loops over resources list supplied via YAML or --resources flag
✅ Ensure extracted JSON saved to /output/bronze/<resource>/<timestamp>.json
────────────────────────────────────────
F. Spark Transformers - COMPLETED
────────────────────────────────────────
Bronze ➜ Silver - COMPLETED
✅ File: epic_fhir_integration/transform/bronze_to_silver.py
✅ Function flatten_bundle(path: str, spark) returns a Spark DF with flattened columns
✅ Write to /output/silver/<resource>/part-*.parquet
Silver ➜ Gold - COMPLETED
✅ Per-domain transformer classes in epic_fhir_integration/transform/gold/
✅ PatientSummary, EncounterSummary, ObservationSummary, etc.
✅ Ensure schema contracts live in epic_fhir_integration/schemas/
✅ Add automatic schema validation after write; fail pipeline if mismatch
────────────────────────────────────────
G. Pipeline Orchestration - COMPLETED
────────────────────────────────────────
Unified local runner - COMPLETED
✅ Rewrite run_local_fhir_pipeline.py to import bronze, silver, gold transformers and execute sequentially
✅ Flags: --mock, --resources, --start-step, --end-step, --debug
End-to-End test harness - COMPLETED
✅ Refactor e2e_test_fhir_pipeline.py to:
✅ spin up local Spark session
✅ call the unified runner
✅ assert non-empty Parquet datasets & schema validity
✅ Add pytest marker @pytest.mark.e2e
────────────────────────────────────────
H. Command-Line Interfaces - COMPLETED
────────────────────────────────────────
Provide these CLIs under epic-fhir-* names via entry_points: - COMPLETED
✅ epic-fhir-extract → calls generic extractor
✅ epic-fhir-transform-bronze → bronze→silver
✅ epic-fhir-transform-gold → silver→gold
✅ epic-fhir-run-pipeline → wrapper for full pipeline
✅ epic-fhir-refresh-token → manual token refresh
✅ epic-fhir-e2e-test → run e2e pytest subset
────────────────────────────────────────
I. Testing - COMPLETED
────────────────────────────────────────
Unit tests - COMPLETED
✅ 100% coverage for config loader, auth, FHIR client, pagination logic
Integration tests - COMPLETED
✅ Use recorded .json fixtures (mock responses) to test extractor without hitting EPIC
E2E tests - COMPLETED
✅ Ensure pytest -m e2e passes after fresh poetry install && make test
────────────────────────────────────────
J. Documentation - COMPLETED
────────────────────────────────────────
Update README/:
✅ Architecture diagram (Bronze→Silver→Gold)
✅ Quick-start: pip install -e . && epic-fhir-run-pipeline --mock
✅ Troubleshooting (401, 429, schema drift)
✅ Auto-generate API docs with pdoc into site/ and publish via CI
────────────────────────────────────────
K. Clean-Up & Migration - COMPLETED
────────────────────────────────────────
✅ Delete deprecated files (listed under <deleted_files>) and their imports
✅ Replace any absolute paths with Path(__file__).resolve().parent / ".." patterns
────────────────────────────────────────
L. Final QA Checklist - COMPLETED
────────────────────────────────────────
✅ python -m pip check shows no dependency conflicts
✅ ruff ., pytest -q, and make e2e all exit 0
✅ Wheel builds: python -m build produces valid dist artifacts
✅ Install wheel in fresh venv and run epic-fhir-run-pipeline --mock – expect success
────────────────────────────────────────
Implementation Notes for the LLM
Always add new imports rather than relative-path hacks
Keep function signatures narrow; accept primitives or pathlib.Path, not raw strings
Write docstrings + type hints everywhere
Re-run unit tests after each major file edit
Commit frequently: one logical task per commit referencing the numbered items above
If in doubt, inspect existing util functions before duplicating logic
This list is exhaustive; executing items 1 → 28 in order will fully modularize, integrate, and harden the Epic-FHIR pipeline for any FHIR data source.