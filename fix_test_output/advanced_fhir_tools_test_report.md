# Advanced FHIR Tools Test Report

**Test Date:** 2025-05-21 01:16:12

**Patient ID:** T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB

**Data Tier:** BRONZE

**Overall Status:** FAILURE

## Test Steps Summary

| Step | Status | Duration |
|------|--------|----------|
| Authentication | ✅ PASS | 0.00s |
| Fetch_Data | ✅ PASS | 0.00s |
| Fhirpath | ❌ FAIL | 0.01s |
| Pathling | ✅ PASS | 0.00s |
| Datascience | ✅ PASS | 0.00s |
| Validation | ✅ PASS | 0.00s |
| Dashboards | ✅ PASS | 0.37s |

## Detailed Results

### Authentication

### Fetch_Data

**Resource Counts:**

- Patient: 1
- Observation: 5
- Condition: 1
- Encounter: 1
**Results File:** fix_test_output/bronze/raw_resources.json

### Fhirpath

**Error:** Object of type date is not JSON serializable

### Pathling

**Results File:** fix_test_output/results/pathling_results.json

### Datascience

**Results File:** fix_test_output/results/datascience_results.json

### Validation

**Validation Statistics:**

- Total resources: 8
- Valid resources: 1 (12.5%)
- Invalid resources: 7
**Results File:** fix_test_output/bronze/validation_results.json

### Dashboards

**Dashboard Output:**

- Dashboard files: fix_test_output/dashboard
- Available dashboards: Quality, Validation, Combined

## Tier-Specific Information

This test was run against the **BRONZE** data tier.

Bronze tier represents raw data as fetched, conforming to base FHIR R4 with minimal transformations.

## Conclusion

Some tests failed. See above for details.
