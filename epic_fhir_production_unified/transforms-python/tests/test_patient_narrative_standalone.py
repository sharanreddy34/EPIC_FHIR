"""
Standalone test for patient narrative generation.

This test ensures that the patient narrative generation functionality
works without requiring the entire transforms pipeline.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime

# Set up our minimal mock environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockFHIRClient:
    """Mock FHIR client for testing."""
    
    def __init__(self):
        self.get_resource_calls = []
        self.batch_get_resources_calls = []
    
    def get_resource(self, resource_type, resource_id=None, params=None):
        """Mock get_resource method."""
        self.get_resource_calls.append((resource_type, resource_id, params))
        
        # Return sample patient
        if resource_type == "Patient" and resource_id == "test-patient-1":
            return {
                "resourceType": "Patient",
                "id": "test-patient-1",
                "meta": {"lastUpdated": "2023-01-01T12:00:00Z"},
                "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
                "gender": "male",
                "birthDate": "1970-01-01"
            }
        
        # Return bundle with revinclude resources
        if resource_type == "Patient" and params and "_revinclude" in params:
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "test-patient-1",
                            "meta": {"lastUpdated": "2023-01-01T12:00:00Z"},
                            "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
                            "gender": "male",
                            "birthDate": "1970-01-01"
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "condition-1",
                            "subject": {"reference": "Patient/test-patient-1"},
                            "code": {
                                "coding": [{"system": "http://snomed.info/sct", "code": "123456", "display": "Hypertension"}]
                            },
                            "clinicalStatus": {
                                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active", "display": "Active"}]
                            },
                            "recordedDate": "2022-01-01"
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "DiagnosticReport",
                            "id": "echo-1",
                            "subject": {"reference": "Patient/test-patient-1"},
                            "code": {
                                "coding": [{"system": "http://loinc.org", "code": "45030-7", "display": "Echocardiogram report"}]
                            },
                            "status": "final",
                            "effectiveDateTime": "2023-01-15T10:30:00Z",
                            "conclusion": "Normal echocardiogram with preserved ejection fraction.",
                            "result": []
                        }
                    }
                ]
            }
        
        return {"resourceType": "Bundle", "type": "searchset", "entry": []}
    
    def batch_get_resources(self, resource_type, ids):
        """Mock batch_get_resources method."""
        self.batch_get_resources_calls.append((resource_type, ids))
        return {}

def test_patient_narrative_generation():
    """Test that patient narrative generation works correctly."""
    # Import the module to test
    try:
        from src.epic_fhir_integration.llm.patient_narrative import (
            fetch_patient_complete,
            generate_patient_narrative
        )
    except ImportError:
        pytest.skip("Patient narrative module not available")
    
    # Create mock client
    mock_client = MockFHIRClient()
    
    # Fetch patient data
    resources = fetch_patient_complete(mock_client, "test-patient-1")
    
    # Verify that the correct API calls were made
    assert len(mock_client.get_resource_calls) >= 2
    assert mock_client.get_resource_calls[0][0] == "Patient"  # First call to get Patient
    assert mock_client.get_resource_calls[1][0] == "Patient"  # Second call with _revinclude
    
    # Generate narrative
    narrative = generate_patient_narrative(resources)
    
    # Verify narrative contains expected sections
    assert "PATIENT SUMMARY" in narrative
    assert "John Smith" in narrative
    assert "Gender: male" in narrative
    assert "Birth Date: 1970-01-01" in narrative
    
    # Check for condition
    assert "PROBLEMS" in narrative
    assert "Hypertension" in narrative
    assert "Status: Active" in narrative
    
    # Check for echo report
    assert "ECHOCARDIOGRAPHY / ULTRASOUND REPORTS" in narrative
    assert "Echocardiogram report" in narrative
    assert "Normal echocardiogram with preserved ejection fraction" in narrative


if __name__ == "__main__":
    test_patient_narrative_generation() 