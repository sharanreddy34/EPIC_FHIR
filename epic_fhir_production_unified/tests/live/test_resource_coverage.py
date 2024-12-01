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
    assert patient.get("id") == test_patient_id
    
    # Verify basic patient information is present
    assert "name" in patient
    assert "birthDate" in patient
    logger.info(f"Successfully retrieved patient with ID: {test_patient_id}")

def test_fetch_encounters(client, test_patient_id):
    """Test fetching encounters for the patient."""
    encounters = client.get_patient_encounters(test_patient_id)
    assert encounters is not None
    assert "entry" in encounters
    assert len(encounters["entry"]) > 0
    
    # Verify encounter structure
    for entry in encounters["entry"][:3]:  # Check first 3 encounters
        encounter = entry["resource"]
        assert "status" in encounter
        assert "class" in encounter
        assert "period" in encounter
    
    logger.info(f"Successfully retrieved {len(encounters['entry'])} encounters for patient")

def test_fetch_observations(client, test_patient_id):
    """Test fetching observations for the patient."""
    observations = client.get_patient_observations(test_patient_id)
    assert observations is not None
    assert "entry" in observations
    assert len(observations["entry"]) > 0
    
    # Verify observation structure
    for entry in observations["entry"][:3]:  # Check first 3 observations
        observation = entry["resource"]
        assert "status" in observation
        assert "code" in observation
        
    logger.info(f"Successfully retrieved {len(observations['entry'])} observations for patient")

def test_fetch_conditions(client, test_patient_id):
    """Test fetching conditions for the patient."""
    conditions = client.get_patient_conditions(test_patient_id)
    assert conditions is not None
    assert "entry" in conditions
    
    # Verify condition structure if any conditions exist
    if len(conditions["entry"]) > 0:
        for entry in conditions["entry"][:3]:  # Check first 3 conditions
            condition = entry["resource"]
            assert "clinicalStatus" in condition or "verificationStatus" in condition
            assert "code" in condition
            
    logger.info(f"Successfully retrieved {len(conditions['entry'])} conditions for patient")

def test_fetch_medications(client, test_patient_id):
    """Test fetching medications for the patient."""
    medications = client.get_patient_medications(test_patient_id)
    assert medications is not None
    assert "entry" in medications
    
    # Verify medication structure if any medications exist
    if len(medications["entry"]) > 0:
        for entry in medications["entry"][:3]:  # Check first 3 medications
            medication = entry["resource"]
            assert "status" in medication
            
    logger.info(f"Successfully retrieved {len(medications['entry'])} medications for patient")

def test_fetch_procedures(client, test_patient_id):
    """Test fetching procedures for the patient."""
    procedures = client.get_patient_procedures(test_patient_id)
    assert procedures is not None
    assert "entry" in procedures
    
    # Verify procedure structure if any procedures exist
    if len(procedures["entry"]) > 0:
        for entry in procedures["entry"][:3]:  # Check first 3 procedures
            procedure = entry["resource"]
            assert "status" in procedure
            assert "code" in procedure
            
    logger.info(f"Successfully retrieved {len(procedures['entry'])} procedures for patient")

def test_resource_references(client, test_patient_id):
    """Test resolving resource references."""
    encounters = client.get_patient_encounters(test_patient_id)
    
    if len(encounters["entry"]) > 0:
        # Get the first encounter
        encounter = encounters["entry"][0]["resource"]
        
        # Check for references to practitioners
        if "participant" in encounter:
            for participant in encounter["participant"]:
                if "individual" in participant and "reference" in participant["individual"]:
                    reference = participant["individual"]["reference"]
                    logger.info(f"Found reference: {reference}")
                    
                    # Try to resolve the reference
                    if reference.startswith("Practitioner/"):
                        practitioner_id = reference.split("/")[1]
                        practitioner = client.get_practitioner(practitioner_id)
                        assert practitioner is not None
                        assert "id" in practitioner
                        assert practitioner["id"] == practitioner_id
                        logger.info(f"Successfully resolved reference to {reference}")
    
    logger.info("Resource reference resolution test completed") 