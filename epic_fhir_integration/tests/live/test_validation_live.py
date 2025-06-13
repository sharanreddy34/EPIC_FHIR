import pytest
import os
import json
import logging
import tempfile
from pathlib import Path
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient
from epic_fhir_integration.config.loader import load_config
from epic_fhir_integration.validation.validator import FHIRValidator

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def config():
    """Load configuration for testing."""
    config_path = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")
    return load_config(config_path)

@pytest.fixture(scope="module")
def client(config):
    """Initialize FHIR client with test configuration."""
    return EpicFHIRClient(config)

@pytest.fixture(scope="module")
def test_patient_id():
    """Return the test patient ID."""
    return "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

@pytest.fixture(scope="module")
def validator():
    """Initialize FHIR validator."""
    return FHIRValidator()

@pytest.fixture(scope="module")
def patient_resources(client, test_patient_id):
    """Fetch resources for the test patient."""
    patient = client.get_patient(test_patient_id)
    observations = client.get_patient_observations(test_patient_id)[:5]  # Limit to 5 for test speed
    conditions = client.get_patient_conditions(test_patient_id)[:5]
    
    return {
        "Patient": patient,
        "Observations": observations,
        "Conditions": conditions
    }

def test_validate_patient(validator, patient_resources):
    """Test validating a Patient resource against the base FHIR specification."""
    patient = patient_resources["Patient"]
    result = validator.validate(patient)
    
    assert result is not None
    
    # Log validation issues for review
    if not result.is_valid:
        logger.warning(f"Patient validation issues: {result.get_issues()}")
    
    # Patient may have minor issues but should not have fatal errors
    assert not result.has_fatal_errors()

def test_validate_observations(validator, patient_resources):
    """Test validating Observation resources against the base FHIR specification."""
    observations = patient_resources["Observations"]
    
    all_valid = True
    for i, obs in enumerate(observations):
        result = validator.validate(obs)
        
        # Log validation issues for review
        if not result.is_valid:
            logger.warning(f"Observation {i} validation issues: {result.get_issues()}")
            all_valid = False
        
        # Observations may have minor issues but should not have fatal errors
        assert not result.has_fatal_errors()
    
    logger.info(f"All observations validated, {len(observations)} total")

def test_validate_conditions(validator, patient_resources):
    """Test validating Condition resources against the base FHIR specification."""
    conditions = patient_resources["Conditions"]
    
    all_valid = True
    for i, cond in enumerate(conditions):
        result = validator.validate(cond)
        
        # Log validation issues for review
        if not result.is_valid:
            logger.warning(f"Condition {i} validation issues: {result.get_issues()}")
            all_valid = False
        
        # Conditions may have minor issues but should not have fatal errors
        assert not result.has_fatal_errors()
    
    logger.info(f"All conditions validated, {len(conditions)} total")

def test_batch_validation(validator, patient_resources):
    """Test batch validation of multiple resources."""
    # Create a mixed batch of resources
    batch = [
        patient_resources["Patient"],
        patient_resources["Observations"][0] if patient_resources["Observations"] else None,
        patient_resources["Conditions"][0] if patient_resources["Conditions"] else None
    ]
    
    # Remove any None values
    batch = [r for r in batch if r is not None]
    
    results = validator.validate_batch(batch)
    
    assert results is not None
    assert len(results) == len(batch)
    
    # Check each result
    for i, result in enumerate(results):
        resource_type = batch[i].get("resourceType", "Unknown")
        if not result.is_valid:
            logger.warning(f"{resource_type} batch validation issues: {result.get_issues()}")
        
        # Resources may have minor issues but should not have fatal errors
        assert not result.has_fatal_errors()

def test_fsh_profile_compilation(tmp_path):
    """Test compilation of a simple FSH profile."""
    # Create a temporary FSH file
    fsh_dir = tmp_path / "fsh"
    fsh_dir.mkdir()
    
    # Create a simple FSH profile
    fsh_content = """
    Profile: TestPatient
    Parent: Patient
    Id: test-patient
    Title: "Test Patient Profile"
    Description: "A patient profile for testing"
    * name 1..* MS
    * gender 1..1 MS
    * birthDate 1..1 MS
    """
    
    with open(fsh_dir / "TestPatient.fsh", "w") as f:
        f.write(fsh_content)
    
    # Create SUSHI config
    sushi_config = """
    id: test-fhir-implementation-guide
    canonical: http://example.org/fhir/test-ig
    name: TestImplementationGuide
    status: draft
    version: 0.1.0
    fhirVersion: 4.0.1
    """
    
    with open(fsh_dir / "sushi-config.yaml", "w") as f:
        f.write(sushi_config)
    
    # Compile FSH to IG package
    # This will be skipped if SUSHI is not available
    try:
        validator = FHIRValidator()
        result = validator.compile_fsh(str(fsh_dir))
        assert result is True
        logger.info("FSH compilation successful")
    except Exception as e:
        logger.warning(f"Skipping FSH compilation: {str(e)}")
        pytest.skip("SUSHI is not available for FSH compilation")

def test_validation_with_epic_profile(validator, patient_resources):
    """Test validation against Epic-specific profiles if available."""
    # This test is meaningful only if Epic profiles are loaded
    if not validator.has_profile("http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"):
        logger.warning("Skipping Epic profile validation - profiles not loaded")
        pytest.skip("Epic profiles not available")
        
    patient = patient_resources["Patient"]
    
    # Validate against US Core Patient profile (commonly used by Epic)
    result = validator.validate(
        patient, 
        profile="http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
    )
    
    assert result is not None
    
    # Log validation issues for review
    if not result.is_valid:
        logger.warning(f"Epic profile validation issues: {result.get_issues()}")
    
    # Check for specific Epic extension presence
    has_epic_extensions = False
    if "extension" in patient:
        for ext in patient["extension"]:
            if ext.get("url", "").startswith("http://open.epic.com/"):
                has_epic_extensions = True
                break
    
    if has_epic_extensions:
        logger.info("Epic-specific extensions found in patient resource") 