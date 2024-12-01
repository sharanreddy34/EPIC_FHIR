import os
import pytest
import json
from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.io.fhir_client import FHIRClient

SANDBOX_PATIENT_ID = "Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"  # Sample test patient from plan

@pytest.fixture(scope="module")
def sandbox_client():
    """Create a FHIR client connected to the Epic sandbox."""
    client = FHIRClient(
        base_url=os.environ["EPIC_BASE_URL"],
        token_client=JWTClient(
            client_id=os.environ["EPIC_CLIENT_ID"],
            private_key=os.environ["EPIC_PRIVATE_KEY"],
        ),
    )
    return client

def test_connection(sandbox_client):
    """Test basic connection to Epic FHIR API without PHI access."""
    metadata = sandbox_client.get("metadata")
    assert metadata["resourceType"] == "CapabilityStatement"
    assert "rest" in metadata
    print(f"Successfully connected to {os.environ.get('EPIC_BASE_URL', 'EPIC FHIR API')}")

def test_patient_pull(sandbox_client):
    """Test retrieving a specific patient from the sandbox."""
    bundle = sandbox_client.get(f"Patient/{SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Bundle" or bundle["resourceType"] == "Patient"
    if bundle["resourceType"] == "Bundle":
        # For search responses
        assert len(bundle.get("entry", [])) > 0
        entry = bundle["entry"][0]["resource"]
    else:
        # For direct resource responses
        entry = bundle
    
    # Validate basic patient data structure
    assert "id" in entry
    assert "name" in entry
    
    print(f"Successfully retrieved test patient data")

def test_observation_pull(sandbox_client):
    """Test retrieving observations for a patient."""
    bundle = sandbox_client.get(f"Observation?patient={SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Bundle"
    assert "entry" in bundle
    
    count = len(bundle.get("entry", []))
    assert count > 0, "Expected at least one observation for test patient"
    
    print(f"Successfully retrieved {count} observations for test patient")

def test_encounter_pull(sandbox_client):
    """Test retrieving encounters for a patient."""
    bundle = sandbox_client.get(f"Encounter?patient={SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Bundle"
    
    count = len(bundle.get("entry", []))
    print(f"Successfully retrieved {count} encounters for test patient")

def test_condition_pull(sandbox_client):
    """Test retrieving conditions for a patient."""
    bundle = sandbox_client.get(f"Condition?patient={SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Bundle"
    
    count = len(bundle.get("entry", []))
    print(f"Successfully retrieved {count} conditions for test patient")

def test_medication_request_pull(sandbox_client):
    """Test retrieving medication requests for a patient."""
    bundle = sandbox_client.get(f"MedicationRequest?patient={SANDBOX_PATIENT_ID}")
    assert bundle["resourceType"] == "Bundle"
    
    count = len(bundle.get("entry", []))
    print(f"Successfully retrieved {count} medication requests for test patient") 