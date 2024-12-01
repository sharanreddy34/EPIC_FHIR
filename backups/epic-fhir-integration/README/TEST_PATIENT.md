# Epic FHIR Test Patient Extraction

This guide explains how to use the test scripts to extract FHIR data for a specific test patient.

## Prerequisites

1. Python 3.8+ installed
2. Access to Epic FHIR API
3. Epic credentials (client ID and secret)
4. Required dependencies installed:
   ```
   pip install -r requirements.txt
   ```

## Available Scripts

### 1. Simple Test Patient Extraction

This script extracts specific FHIR resources for a test patient:

```bash
python extract_test_patient.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB
```

Options:
- `--patient-id`: (Required) The patient ID to extract
- `--resources`: Comma-separated list of resources to extract (default: Patient,Encounter,Observation,Condition,MedicationRequest)
- `--token-file`: Path to token file (default: epic_token.json)
- `--output-dir`: Output directory (default: ./patient_data)
- `--config-file`: Path to API config file (default: config/api_config.yaml)

### 2. Full Pipeline Simulation

This script runs the entire Foundry pipeline locally for a test patient:

```bash
python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB
```

Options:
- `--patient-id`: (Required) The patient ID to process
- `--output-dir`: Output directory for pipeline results (default: ./local_output)
- `--steps`: Pipeline steps to run (comma-separated: token,extract,transform,gold,monitoring) (default: all)

## Authentication

For both scripts, you'll need to set up authentication:

1. Set environment variables for credentials:
   ```bash
   export EPIC_CLIENT_ID=3d6d8f7d-9bea-4fe2-b44d-81c7fec75ee5
   export EPIC_CLIENT_SECRET=your-secret-here
   ```

2. Alternatively, you can use a pre-generated token file:
   - Create a file called `epic_token.json` in the project root
   - Add the token in the following format:
     ```json
     {
       "access_token": "your-access-token",
       "token_type": "Bearer",
       "expires_in": 3600
     }
     ```

## Output Structure

### Simple Extraction (`extract_test_patient.py`)

```
patient_data/
└── T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB/
    ├── Patient/
    │   └── 20230501_120000_0.json
    ├── Encounter/
    │   └── 20230501_120001_0.json
    ├── Observation/
    │   └── 20230501_120002_0.json
    ├── Condition/
    │   └── 20230501_120003_0.json
    └── MedicationRequest/
        └── 20230501_120004_0.json
```

### Full Pipeline (`run_local_fhir_pipeline.py`)

```
local_output/
├── bronze/
│   └── fhir_raw/
│       ├── Patient/
│       ├── Encounter/
│       └── ...
├── silver/
│   └── fhir_normalized/
│       ├── patient/
│       ├── encounter/
│       └── ...
├── gold/
│   ├── patient_summary/
│   ├── encounter_summary/
│   └── medication_summary/
├── metrics/
│   └── transform_metrics/
└── monitoring/
    └── pipeline_metrics/
```

## Example Usage

1. Extract data for a test patient:
   ```bash
   python extract_test_patient.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --resources Patient,Encounter,Observation
   ```

2. Run the full pipeline:
   ```bash
   python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --steps token,extract,transform
   ```

3. Run just the extraction and transformation steps:
   ```bash
   python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --steps extract,transform
   ```

## Troubleshooting

1. **Authentication issues**: Make sure your client ID and secret are correctly set and have proper permissions.
2. **API rate limiting**: If you encounter rate limiting, the script will pause and retry.
3. **Missing dependencies**: If you get import errors, make sure all required packages are installed.
4. **Spark issues**: For the full pipeline script, you need to have Java installed for PySpark to work properly. 