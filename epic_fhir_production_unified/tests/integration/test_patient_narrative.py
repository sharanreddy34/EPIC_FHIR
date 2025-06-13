"""
Integration test for patient narrative generation.

This test ensures that the patient narrative generation functionality
works end-to-end by using a mock FHIR server with sample data.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
import tempfile

from epic_fhir_integration.llm.patient_narrative import (
    fetch_patient_complete,
    generate_patient_narrative
)


# Sample patient data for testing
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "test-patient-1",
    "meta": {
        "lastUpdated": "2023-01-01T12:00:00Z"
    },
    "name": [
        {
            "use": "official",
            "family": "Smith",
            "given": ["John"]
        }
    ],
    "gender": "male",
    "birthDate": "1970-01-01"
}

# Sample observation
SAMPLE_OBSERVATION = {
    "resourceType": "Observation",
    "id": "test-obs-1",
    "meta": {
        "lastUpdated": "2023-01-02T12:00:00Z"
    },
    "status": "final",
    "category": [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }
            ]
        }
    ],
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }
        ]
    },
    "subject": {
        "reference": "Patient/test-patient-1"
    },
    "effectiveDateTime": "2023-01-02T10:30:00Z",
    "valueQuantity": {
        "value": 72,
        "unit": "beats/minute",
        "system": "http://unitsofmeasure.org",
        "code": "/min"
    }
}

# Sample diagnostic report (echocardiogram)
SAMPLE_ECHO_REPORT = {
    "resourceType": "DiagnosticReport",
    "id": "test-echo-1",
    "meta": {
        "lastUpdated": "2023-01-03T14:00:00Z"
    },
    "status": "final",
    "category": [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "EC",
                    "display": "Echocardiography"
                }
            ]
        }
    ],
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "34140-4",
                "display": "Echocardiogram study"
            }
        ]
    },
    "subject": {
        "reference": "Patient/test-patient-1"
    },
    "effectiveDateTime": "2023-01-03T13:00:00Z",
    "issued": "2023-01-03T14:00:00Z",
    "conclusion": "Normal left ventricular size and function. No significant valvular abnormalities.",
    "result": [
        {
            "reference": "Observation/test-echo-obs-1"
        }
    ]
}

# Sample echo observation result
SAMPLE_ECHO_OBS = {
    "resourceType": "Observation",
    "id": "test-echo-obs-1",
    "meta": {
        "lastUpdated": "2023-01-03T14:00:00Z"
    },
    "status": "final",
    "category": [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "imaging",
                    "display": "Imaging"
                }
            ]
        }
    ],
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "10230-1",
                "display": "Left ventricular ejection fraction"
            }
        ]
    },
    "subject": {
        "reference": "Patient/test-patient-1"
    },
    "effectiveDateTime": "2023-01-03T13:00:00Z",
    "valueQuantity": {
        "value": 60,
        "unit": "%",
        "system": "http://unitsofmeasure.org",
        "code": "%"
    },
    "referenceRange": [
        {
            "low": {
                "value": 55,
                "unit": "%"
            },
            "high": {
                "value": 70,
                "unit": "%"
            }
        }
    ]
}


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client for testing."""
    mock_client = MagicMock()
    
    # Mock get_resource to return appropriate resources
    def mock_get_resource(resource_type, resource_id=None, params=None):
        if resource_type == "Patient" and resource_id == "test-patient-1":
            return SAMPLE_PATIENT
        
        if resource_type == "Patient" and params and "_id" in params:
            # Return a bundle with the patient and referenced resources
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {"resource": SAMPLE_PATIENT},
                    {"resource": SAMPLE_OBSERVATION},
                    {"resource": SAMPLE_ECHO_REPORT}
                ]
            }
            
        return {"resourceType": "Bundle", "entry": []}
    
    mock_client.get_resource.side_effect = mock_get_resource
    
    # Mock batch_get_resources to return echo observation
    def mock_batch_get_resources(resource_type, resource_ids):
        if resource_type == "Observation" and "test-echo-obs-1" in resource_ids:
            return {"test-echo-obs-1": SAMPLE_ECHO_OBS}
        return {}
    
    mock_client.batch_get_resources.side_effect = mock_batch_get_resources
    
    return mock_client


def test_fetch_patient_complete(mock_fhir_client):
    """Test fetching complete patient data."""
    # Test fetching patient data
    resources = fetch_patient_complete(mock_fhir_client, "test-patient-1")
    
    # Verify that we got the patient resource
    assert "Patient" in resources
    assert len(resources["Patient"]) == 1
    assert resources["Patient"][0]["id"] == "test-patient-1"
    
    # Verify that we got related resources
    assert "Observation" in resources
    assert "DiagnosticReport" in resources
    
    # Verify that diagnostic report results were fetched
    assert any(obs["id"] == "test-echo-obs-1" for obs in resources["Observation"])


def test_generate_patient_narrative(mock_fhir_client):
    """Test generating a patient narrative."""
    # First fetch the complete patient data
    resources = fetch_patient_complete(mock_fhir_client, "test-patient-1")
    
    # Then generate the narrative
    narrative = generate_patient_narrative(resources)
    
    # Verify that the narrative contains key sections
    assert "PATIENT SUMMARY" in narrative
    assert "John Smith" in narrative
    assert "male" in narrative
    assert "1970-01-01" in narrative
    
    # Verify that it contains the echo report section
    assert "ECHOCARDIOGRAPHY / ULTRASOUND REPORTS" in narrative
    assert "Echocardiogram study" in narrative
    assert "Normal left ventricular size and function" in narrative
    
    # Verify that it contains the observation data
    assert "Heart rate" in narrative
    assert "72 beats/minute" in narrative
    
    # Verify that it contains the echo observation
    assert "Left ventricular ejection fraction" in narrative
    assert "60 %" in narrative 