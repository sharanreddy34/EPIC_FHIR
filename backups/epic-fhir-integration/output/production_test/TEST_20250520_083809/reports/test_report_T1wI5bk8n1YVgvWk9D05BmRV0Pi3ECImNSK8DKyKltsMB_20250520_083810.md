# Epic FHIR Integration Test Report

## Test Date: 2025-05-20 08:38:10

## Patient ID: T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB

## Test Steps Results

- ✅ Authentication
- ✅ Data Extraction
- ✅ Bronze to Silver Transformation
- ✅ Silver to Gold Transformation
- ✅ Validation

## Resources Retrieved

- Patient: 1 resources
- Observation: 10 resources
- Encounter: 10 resources
- Condition: 3 resources
- MedicationRequest: 1 resources

## Patient Information

- Name: Anna Cadence
- Gender: female
- Birth Date: 1983-09-09

## Validation Results

- Status: SUCCESS
- Success: 1
- Warnings: 0
- Failures: 0
- Skipped: 4

### Validation Checks

- ⏭️ bronze_to_silver_row_parity: Missing bronze or silver count metrics
- ⏭️ silver_to_gold_row_parity: Missing silver or gold count metrics
- ✅ extract_performance: Extract completed in 0.92 seconds (threshold: 300.00s)
- ⏭️ transform_performance: No duration metrics found for transform
- ⏭️ resource_usage: No resource usage metrics found

## Performance Metrics

## Overall Test Result: SUCCESS
