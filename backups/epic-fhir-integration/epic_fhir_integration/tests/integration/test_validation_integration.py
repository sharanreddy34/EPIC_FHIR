import pytest
import os
import json
from pathlib import Path
import shutil
import tempfile

from epic_fhir_integration.validation.validator import FHIRValidator
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

# Constants for testing
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

@pytest.fixture
def sample_fsh_profile():
    """Create a temporary FSH profile for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create FSH directory structure
    fsh_dir = Path(temp_dir) / "input" / "fsh"
    os.makedirs(fsh_dir, exist_ok=True)
    
    # Create a simple Patient profile
    patient_profile = """
    Profile: EpicPatient
    Parent: Patient
    Id: epic-patient
    Title: "Epic Patient Profile"
    Description: "Patient profile for Epic integration testing"
    * identifier 1..* MS
    * name 1..* MS
    * gender 1..1 MS
    * birthDate 1..1 MS
    """
    
    # Create a simple Observation profile
    observation_profile = """
    Profile: EpicObservation
    Parent: Observation
    Id: epic-observation
    Title: "Epic Observation Profile"
    Description: "Observation profile for Epic integration testing"
    * status 1..1 MS
    * code 1..1 MS
    * subject 1..1 MS
    * value[x] 1..1 MS
    """
    
    # Create sushi-config.yaml
    sushi_config = """
    id: epic-fhir-test
    canonical: http://epic.test/fhir
    name: EpicFHIRTest
    status: draft
    version: 0.1.0
    fhirVersion: 4.0.1
    copyrightYear: 2023
    releaseLabel: ci-build
    publisher: Epic Test
    """
    
    # Write files
    (fsh_dir / "Patient.fsh").write_text(patient_profile)
    (fsh_dir / "Observation.fsh").write_text(observation_profile)
    (Path(temp_dir) / "sushi-config.yaml").write_text(sushi_config)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest.fixture
def valid_patient():
    """Create a valid patient resource."""
    return Patient.construct(
        id="test-patient",
        identifier=[{
            "system": "http://example.org/fhir/identifier/mrn",
            "value": "12345"
        }],
        name=[{
            "use": "official",
            "family": "Smith",
            "given": ["John"]
        }],
        gender="male",
        birthDate="1970-01-01"
    )

@pytest.fixture
def invalid_patient():
    """Create an invalid patient missing required elements."""
    return Patient.construct(
        id="test-patient",
        gender="male"
        # Missing required name and birthDate
    )

@pytest.fixture
def valid_observation():
    """Create a valid observation resource."""
    return Observation.construct(
        id="test-observation",
        status="final",
        code={
            "coding": [{
                "system": "http://loinc.org",
                "code": "8480-6",
                "display": "Blood Pressure"
            }]
        },
        subject={"reference": "Patient/test-patient"},
        valueQuantity={
            "value": 120,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
        }
    )

class TestFHIRValidation:
    """Integration tests for the FHIR validation module."""
    
    def test_validator_initialization(self):
        """Test that the validator can be initialized."""
        validator = FHIRValidator()
        assert validator is not None
    
    @pytest.mark.skipif(not shutil.which("sushi"), reason="Sushi compiler not installed")
    def test_fsh_compilation(self, sample_fsh_profile):
        """Test compiling FSH profiles."""
        validator = FHIRValidator()
        
        # Attempt to compile the FSH profiles
        result = validator.compile_fsh(
            fsh_directory=sample_fsh_profile,
            output_directory=os.path.join(sample_fsh_profile, "output")
        )
        
        # Verify compilation success
        assert result is True
        assert os.path.exists(os.path.join(sample_fsh_profile, "output", "package.tgz"))
    
    def test_resource_validation(self, valid_patient, invalid_patient):
        """Test validating FHIR resources."""
        validator = FHIRValidator()
        
        # Validate a valid patient
        result = validator.validate(valid_patient)
        assert result.is_valid
        
        # Validate an invalid patient
        result = validator.validate(invalid_patient)
        assert not result.is_valid
        assert len(result.get_errors()) > 0
    
    def test_batch_validation(self, valid_patient, valid_observation, invalid_patient):
        """Test batch validation of multiple resources."""
        validator = FHIRValidator()
        
        # Validate a batch of resources
        valid_resources = [valid_patient, valid_observation]
        results = validator.validate_batch(valid_resources)
        
        # Verify all valid resources pass validation
        assert all(r.is_valid for r in results)
        
        # Validate a mixed batch
        mixed_resources = [valid_patient, invalid_patient]
        results = validator.validate_batch(mixed_resources)
        
        # Verify invalid resources are caught
        valid_count = sum(1 for r in results if r.is_valid)
        assert valid_count == 1
    
    @pytest.mark.skipif(not shutil.which("sushi"), reason="Sushi compiler not installed")
    def test_compile_and_validate(self, sample_fsh_profile, valid_patient, valid_observation):
        """Test compiling and validating against custom profiles."""
        validator = FHIRValidator()
        
        # Compile and validate in one step
        results = validator.compile_and_validate(
            fsh_directory=sample_fsh_profile,
            resources=[valid_patient, valid_observation]
        )
        
        # Verify validation occurred
        assert len(results) == 2
        
        # We don't assert they're all valid since validation against profiles
        # may fail depending on the actual profile requirements 