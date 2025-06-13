# FHIR Cursors Control Dataset

This dataset tracks the extraction progress for FHIR resources. It contains cursor information used by the extraction pipeline to perform incremental updates.

## Schema

The dataset has the following schema:

| Column | Type | Description |
|--------|------|-------------|
| resource_type | string | The FHIR resource type (e.g., Patient, Observation) |
| last_updated | string | ISO timestamp of the last resource update processed |
| extracted_at | string | ISO timestamp when the extraction was performed |
| record_count | string | Number of records extracted in the last run |

## Usage

This dataset is used by the `02_extract_resources.py` pipeline to track extraction progress. The extraction pipeline updates these cursors after each successful run.

For initial setup, this directory can be empty as the extraction pipeline will create the necessary cursor records.

## Example Record

```json
{
  "resource_type": "Patient",
  "last_updated": "2024-05-19T12:34:56Z",
  "extracted_at": "2024-05-19T13:00:00Z",
  "record_count": "152"
}
``` 