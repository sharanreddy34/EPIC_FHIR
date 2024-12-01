import pytest
import os
import logging
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient
from epic_fhir_integration.config.loader import load_config

logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    """Initialize FHIR client with test configuration."""
    config_path = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")
    config = load_config(config_path)
    return EpicFHIRClient(config)

@pytest.fixture
def test_patient_id():
    """Return the test patient ID."""
    return "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

def test_fetch_patient(client, test_patient_id):
    """Test fetching the patient resource."""
    patient = client.get_patient(test_patient_id)
    assert patient is not None
    assert patient.get("resourceType") == "Patient"
    assert patient.get("id") == test_patient_id
    
def test_fetch_encounters(client, test_patient_id):
    """Test fetching patient encounters."""
    encounters = client.get_patient_encounters(test_patient_id)
    assert encounters is not None
    assert len(encounters) > 0
    assert encounters[0].get("resourceType") == "Encounter"
    # Verify basic encounter structure
    for encounter in encounters:
        assert "status" in encounter
        assert "class" in encounter

def test_fetch_observations(client, test_patient_id):
    """Test fetching patient observations."""
    observations = client.get_patient_observations(test_patient_id)
    assert observations is not None
    assert len(observations) > 0
    assert observations[0].get("resourceType") == "Observation"
    # Verify basic observation structure
    for observation in observations:
        assert "status" in observation
        assert "code" in observation

def test_fetch_conditions(client, test_patient_id):
    """Test fetching patient conditions."""
    conditions = client.get_patient_conditions(test_patient_id)
    assert conditions is not None
    assert len(conditions) > 0
    assert conditions[0].get("resourceType") == "Condition"
    # Verify basic condition structure
    for condition in conditions:
        assert "clinicalStatus" in condition or "verificationStatus" in condition
        assert "code" in condition

def test_fetch_medications(client, test_patient_id):
    """Test fetching patient medications."""
    medications = client.get_patient_medications(test_patient_id)
    assert medications is not None
    assert len(medications) > 0
    assert medications[0].get("resourceType") in ["MedicationRequest", "MedicationStatement"]
    
def test_fetch_procedures(client, test_patient_id):
    """Test fetching patient procedures."""
    procedures = client.get_patient_procedures(test_patient_id)
    assert procedures is not None
    assert len(procedures) > 0
    assert procedures[0].get("resourceType") == "Procedure"
    # Verify basic procedure structure
    for procedure in procedures:
        assert "status" in procedure
        assert "code" in procedure

def test_resource_references(client, test_patient_id):
    """Test that resource references are intact and resolvable."""
    # Get a medication with references
    medications = client.get_patient_medications(test_patient_id)
    if len(medications) > 0:
        med = medications[0]
        # If medication has subject reference, resolve it
        if "subject" in med and "reference" in med["subject"]:
            ref = med["subject"]["reference"]
            assert ref.startswith("Patient/")
            patient_id = ref.split("/")[1]
            patient = client.get_resource("Patient", patient_id)
            assert patient is not None
            assert patient.get("resourceType") == "Patient" 