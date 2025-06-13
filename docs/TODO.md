# FHIR Data Pipeline Implementation TODO

## 1. GCP Initial Setup
- [x] Create Cloud Storage bucket
  - Name: fhir-bulk-dumps
  - Region: Match VM region
  - Access: Uniform
  - Block public access
- [x] Enable Healthcare API
  - [x] Create dataset 'ehr_demo'
  - [x] Create FHIR store 'hospital_r4' (R4 version)
- [x] Configure IAM Permissions
  - [x] Grant Storage Object Admin to Healthcare Service Agent

## 2. Backend Services Client Setup
- [ ] Create Service Account
  - [ ] Create bulk-fhir-client
  - [ ] Download JSON key
  - [ ] Grant Healthcare FHIR Resource Viewer role
- [ ] Setup Authentication
  - [ ] Copy key.json to VM
  - [ ] Generate JWKS
  - [ ] Host JWKS file on public URL (e.g., GitHub Pages)

## 3. FHIR Export Implementation
- [ ] Create export script (export.sh)
  - [ ] JWT signing logic
  - [ ] OAuth token exchange
  - [ ] FHIR $export API call
  - [ ] Export monitoring
- [ ] Test first export
  - [ ] Verify NDJSON files in bucket
  - [ ] Check file format and content

## 4. Foundry Integration
- [ ] Create Foundry Dataset
  - [ ] Name: raw/fhir
- [ ] Configure File-based Sync
  - [ ] Setup GCS connector
  - [ ] Configure service account auth
  - [ ] Set path: gs://fhir-bulk-dumps/*/*.ndjson
  - [ ] Schedule daily sync (02:00)

## 5. Data Transformation
- [ ] Create Spark Pipeline
  - [ ] Implement NDJSON to Parquet transformation
  - [ ] Create output datasets
    - [ ] stg_patient
    - [ ] stg_encounter
    - [ ] stg_observation
  - [ ] Schedule transformation (02:15)
  - [ ] Test initial data load

## 6. Ontology and Object-Sets
- [ ] Create Ontology
  - [ ] Define Patient entity
  - [ ] Define Encounter entity
  - [ ] Define Observation entity
- [ ] Create Object-Sets
  - [ ] PatientAll
  - [ ] EncounterAll
  - [ ] ObservationAll
- [ ] Enable GraphQL connector

## 7. (Optional) FHIRcast Integration
- [ ] Deploy FastAPI Application
  - [ ] Implement FHIRcast subscription
  - [ ] Setup Foundry webhook integration
  - [ ] Implement SSE endpoint
- [ ] Test real-time updates

## 8. Production Setup
- [ ] Configure Scheduling
  - [ ] Set up 01:00 cron job for export.sh
  - [ ] Verify Foundry sync (02:00)
  - [ ] Verify transformation job (02:15)
  - [ ] Test end-to-end pipeline
- [ ] Setup Monitoring
  - [ ] Add logging
  - [ ] Create alerts for failures
  - [ ] Document troubleshooting procedures

## Final Verification
- [ ] Test complete pipeline
  - [ ] Verify data flow from export to object-sets
  - [ ] Test GraphQL queries
  - [ ] Validate data quality
- [ ] Document setup and maintenance procedures 