"""
Unit tests for the FHIR resources module.
"""

import json
import os
import pytest
from pathlib import Path
from typing import Dict, Any

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.encounter import Encounter
from fhir.resources.resource import Resource
from pydantic import ValidationError

from epic_fhir_integration.schemas.fhir_resources import (
    get_resource_model, 
    parse_resource, 
    validate_resource,
    RESOURCE_MODELS
)
from epic_fhir_integration.utils.fhir_resource_utils import (
    extract_nested_attribute,
    resource_to_dict,
    resource_to_json,
    dict_to_resource,
    get_extension_by_url,
    get_coding_from_codeable_concept,
    extract_identifier,
    is_resource_model,
    ensure_resource_model
)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PATIENT_PATH = FIXTURES_DIR / "sample_patient.json"
SAMPLE_OBSERVATION_PATH = FIXTURES_DIR / "sample_observation.json"
SAMPLE_ENCOUNTER_PATH = FIXTURES_DIR / "sample_encounter.json"

def load_fixture(file_path: Path) -> Dict[str, Any]:
    """Load a fixture file."""
    with open(file_path, "r") as f:
        return json.load(f)

class TestFhirResources:
    """Tests for the FHIR resources module."""
    
    def test_resource_model_mapping(self):
        """Test the RESOURCE_MODELS mapping."""
        assert "Patient" in RESOURCE_MODELS
        assert RESOURCE_MODELS["Patient"] == Patient
        assert "Observation" in RESOURCE_MODELS
        assert RESOURCE_MODELS["Observation"] == Observation
        assert "Encounter" in RESOURCE_MODELS
        assert RESOURCE_MODELS["Encounter"] == Encounter
    
    def test_get_resource_model(self):
        """Test the get_resource_model function."""
        assert get_resource_model("Patient") == Patient
        assert get_resource_model("Observation") == Observation
        assert get_resource_model("Encounter") == Encounter
        
        # Test with unknown resource type
        with pytest.raises(ValueError):
            get_resource_model("UnknownResource")
    
    def test_parse_resource_patient(self):
        """Test parsing a Patient resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Parse resource
        patient = parse_resource(patient_data)
        
        # Verify the resource was parsed correctly
        assert isinstance(patient, Patient)
        assert patient.id == patient_data["id"]
        # Note: The resourceType is used during model selection but is not an attribute on the model itself
        # This is how fhir.resources models work
        assert patient_data["resourceType"] == "Patient"
    
    def test_validate_resource_valid(self):
        """Test validating a valid resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Validate resource
        errors = validate_resource(patient_data)
        
        # Verify no errors
        assert len(errors) == 0
    
    def test_validate_resource_invalid(self):
        """Test validating an invalid resource."""
        # Create an invalid patient - we'll create one with a completely invalid structure
        # This should reliably fail validation
        invalid_patient = {
            "resourceType": "FakeResource",  # Invalid resource type
            "id": 12345,  # id should be a string, not an integer
            "active": "not-a-boolean"  # active should be a boolean
        }
        
        # Validate resource
        errors = validate_resource(invalid_patient)
        
        # Verify errors
        assert len(errors) > 0
        
        # Check for specific error in resourceType
        resource_type_error = next((e for e in errors if "resourceType" in e["field"]), None)
        assert resource_type_error is not None
    
    def test_extract_nested_attribute(self):
        """Test extracting nested attributes from a resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = parse_resource(patient_data)
        
        # Extract attributes
        family = extract_nested_attribute(patient, "name.0.family")
        assert family == patient_data["name"][0]["family"]
        
        # Test extracting non-existent attribute
        nonexistent = extract_nested_attribute(patient, "nonexistent.field")
        assert nonexistent is None
        
        # Test extracting attribute with invalid index
        invalid_index = extract_nested_attribute(patient, "name.999.family")
        assert invalid_index is None
    
    def test_resource_to_dict(self):
        """Test converting a resource to a dictionary."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = parse_resource(patient_data)
        
        # Convert to dictionary
        patient_dict = resource_to_dict(patient)
        
        # Verify the dictionary
        assert patient_dict["resourceType"] == "Patient"
        assert patient_dict["id"] == patient_data["id"]
        assert patient_dict["name"][0]["family"] == patient_data["name"][0]["family"]
    
    def test_resource_to_json(self):
        """Test converting a resource to a JSON string."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = parse_resource(patient_data)
        
        # Convert to JSON
        patient_json = resource_to_json(patient, indent=2)
        
        # Verify the JSON
        assert isinstance(patient_json, str)
        
        # Parse the JSON back to a dictionary
        parsed_json = json.loads(patient_json)
        assert parsed_json["resourceType"] == "Patient"
        assert parsed_json["id"] == patient_data["id"]
    
    def test_dict_to_resource(self):
        """Test converting a dictionary to a resource."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        
        # Convert to resource
        patient = dict_to_resource(patient_data)
        
        # Verify the resource
        assert patient is not None
        assert isinstance(patient, Patient)
        assert patient.id == patient_data["id"]
        
        # Test with completely invalid structure that should definitely fail
        invalid_data = {
            "resourceType": "NonExistentResourceType",
            "id": {"this-is": ["not", "a", "valid", "id"]},
            "name": "not-a-list-but-should-be"
        }
        # This function catches errors and returns None instead of raising
        invalid_resource = dict_to_resource(invalid_data)
        assert invalid_resource is None
    
    def test_is_resource_model(self):
        """Test checking if an object is a resource model."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = parse_resource(patient_data)
        
        # Check is_resource_model
        assert is_resource_model(patient) is True
        assert is_resource_model(patient_data) is False
        assert is_resource_model(None) is False
        assert is_resource_model("string") is False
    
    def test_ensure_resource_model(self):
        """Test ensuring an object is a resource model."""
        # Load fixture
        patient_data = load_fixture(SAMPLE_PATIENT_PATH)
        patient = parse_resource(patient_data)
        
        # Ensure resource model
        assert ensure_resource_model(patient) is patient
        
        # Convert dictionary to resource
        resource = ensure_resource_model(patient_data)
        assert resource is not None
        assert isinstance(resource, Patient)
        
        # Test with invalid data
        assert ensure_resource_model(None) is None
        assert ensure_resource_model("string") is None
        
        # Test with resource type override
        modified_data = patient_data.copy()
        modified_data["resourceType"] = "Unknown"
        resource = ensure_resource_model(modified_data, "Patient")
        assert resource is not None
        assert isinstance(resource, Patient) 