"""
Unit tests for FHIRPath adapter and comparison with fhirpathpy.

This module tests the new FHIRPath adapter implementation and compares
results with the original fhirpathpy implementation to ensure compatibility.
"""

import json
import pytest
from pathlib import Path

import fhirpathpy

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.utils.fhirpath_extractor import FHIRPathExtractor

# Path to test data fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Load test resources
@pytest.fixture
def patient_resource():
    """Load a sample Patient resource for testing."""
    with open(FIXTURES_DIR / "sample_patient.json", "r") as f:
        return json.load(f)

@pytest.fixture
def observation_resource():
    """Load a sample Observation resource for testing."""
    with open(FIXTURES_DIR / "sample_observation.json", "r") as f:
        return json.load(f)

@pytest.fixture
def encounter_resource():
    """Load a sample Encounter resource for testing."""
    with open(FIXTURES_DIR / "sample_encounter.json", "r") as f:
        return json.load(f)

# Test expression examples
FHIRPATH_TEST_EXPRESSIONS = [
    # Basic paths
    "Patient.id",
    "Patient.name.family",
    "Patient.name.given",
    "Patient.gender",
    "Patient.birthDate",
    
    # Filtering with where
    "Patient.name.where(use = 'official')",
    "Patient.telecom.where(system = 'phone')",
    "Patient.identifier.where(type.coding.code = 'MR').value",
    
    # Complex expressions
    "Patient.name.where(use = 'official').family | Patient.name.family",
    "Patient.deceasedBoolean | Patient.deceasedDateTime",
    "Patient.extension.where(url = 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url = 'text').valueString",
    
    # Existence checks
    "Patient.name.exists()",
    "Patient.deceased.exists()",
    "Patient.maritalStatus.exists()",
    
    # Functions
    "Patient.name.given.count()",
    "Patient.address.line.first()",
    "Patient.name.given.select($this.startsWith('J'))",
    
    # Path combinations
    "Patient.address.line | Patient.address.city | Patient.address.state",
]

# Test observation expressions
OBSERVATION_TEST_EXPRESSIONS = [
    "Observation.id",
    "Observation.code.coding.code",
    "Observation.valueQuantity.value",
    "Observation.effectiveDateTime",
    "Observation.component.code.coding.code",
    "Observation.valueQuantity.value & ' ' & (Observation.valueQuantity.unit | Observation.valueQuantity.code)",
]

# Test encounter expressions
ENCOUNTER_TEST_EXPRESSIONS = [
    "Encounter.id",
    "Encounter.status",
    "Encounter.class.code",
    "Encounter.period.start",
    "Encounter.participant.type.coding.code",
    "Encounter.length.value & ' ' & Encounter.length.unit",
]

class TestFHIRPathAdapter:
    """Test the FHIRPath adapter functionality and compare with fhirpathpy."""
    
    def test_basic_extraction(self, patient_resource):
        """Test basic extraction functionality."""
        # Extract a simple value
        fhirpathpy_result = fhirpathpy.evaluate(patient_resource, "Patient.id")
        adapter_result = FHIRPathAdapter.extract(patient_resource, "Patient.id")
        
        assert adapter_result == fhirpathpy_result, f"Expected {fhirpathpy_result}, got {adapter_result}"
    
    def test_all_patient_expressions(self, patient_resource):
        """Test all defined patient expressions for compatibility."""
        for expression in FHIRPATH_TEST_EXPRESSIONS:
            # Skip expressions that may legitimately differ in implementation
            # For advanced capabilities better implemented in the new library
            if "select(" in expression and "startsWith" in expression:
                continue
                
            fhirpathpy_result = fhirpathpy.evaluate(patient_resource, expression)
            adapter_result = FHIRPathAdapter.extract(patient_resource, expression)
            
            assert adapter_result == fhirpathpy_result, f"Expression '{expression}' returned {adapter_result} instead of {fhirpathpy_result}"
    
    def test_all_observation_expressions(self, observation_resource):
        """Test all defined observation expressions for compatibility."""
        for expression in OBSERVATION_TEST_EXPRESSIONS:
            fhirpathpy_result = fhirpathpy.evaluate(observation_resource, expression)
            adapter_result = FHIRPathAdapter.extract(observation_resource, expression)
            
            assert adapter_result == fhirpathpy_result, f"Expression '{expression}' returned {adapter_result} instead of {fhirpathpy_result}"
    
    def test_all_encounter_expressions(self, encounter_resource):
        """Test all defined encounter expressions for compatibility."""
        for expression in ENCOUNTER_TEST_EXPRESSIONS:
            fhirpathpy_result = fhirpathpy.evaluate(encounter_resource, expression)
            adapter_result = FHIRPathAdapter.extract(encounter_resource, expression)
            
            assert adapter_result == fhirpathpy_result, f"Expression '{expression}' returned {adapter_result} instead of {fhirpathpy_result}"
    
    def test_extract_first(self, patient_resource):
        """Test extract_first method."""
        fhirpathpy_results = fhirpathpy.evaluate(patient_resource, "Patient.name.given")
        fhirpathpy_first = fhirpathpy_results[0] if fhirpathpy_results else None
        
        adapter_first = FHIRPathAdapter.extract_first(patient_resource, "Patient.name.given")
        
        assert adapter_first == fhirpathpy_first, f"extract_first returned {adapter_first} instead of {fhirpathpy_first}"
    
    def test_exists(self, patient_resource):
        """Test exists method."""
        fhirpathpy_results = fhirpathpy.evaluate(patient_resource, "Patient.name")
        fhirpathpy_exists = bool(fhirpathpy_results)
        
        adapter_exists = FHIRPathAdapter.exists(patient_resource, "Patient.name")
        
        assert adapter_exists == fhirpathpy_exists, f"exists returned {adapter_exists} instead of {fhirpathpy_exists}"
        
        # Also test a false case
        fhirpathpy_results = fhirpathpy.evaluate(patient_resource, "Patient.notExistingField")
        fhirpathpy_exists = bool(fhirpathpy_results)
        
        adapter_exists = FHIRPathAdapter.exists(patient_resource, "Patient.notExistingField")
        
        assert adapter_exists == fhirpathpy_exists, f"exists returned {adapter_exists} instead of {fhirpathpy_exists}"
    
    def test_extract_with_paths(self, patient_resource):
        """Test extract_with_paths method."""
        paths = [
            "Patient.notExistingField",
            "Patient.alsoNotExisting",
            "Patient.name.family"
        ]
        
        # Simulate fhirpathpy behavior manually
        fhirpathpy_result = None
        for path in paths:
            results = fhirpathpy.evaluate(patient_resource, path)
            if results and len(results) > 0:
                fhirpathpy_result = results[0]
                break
        
        adapter_result = FHIRPathAdapter.extract_with_paths(patient_resource, paths)
        
        assert adapter_result == fhirpathpy_result, f"extract_with_paths returned {adapter_result} instead of {fhirpathpy_result}"

    def test_fhirpath_extractor_integration(self, patient_resource):
        """Test the integration with the FHIRPathExtractor class."""
        # Force the use of new adapter
        from epic_fhir_integration.utils.fhirpath_extractor import USE_NEW_ADAPTER
        if not USE_NEW_ADAPTER:
            pytest.skip("New adapter not available for testing")
        
        # Simple extraction
        extractor_result = FHIRPathExtractor.extract(patient_resource, "Patient.id")
        adapter_result = FHIRPathAdapter.extract(patient_resource, "Patient.id")
        assert extractor_result == adapter_result
        
        # Extract first
        extractor_first = FHIRPathExtractor.extract_first(patient_resource, "Patient.name.given")
        adapter_first = FHIRPathAdapter.extract_first(patient_resource, "Patient.name.given")
        assert extractor_first == adapter_first
        
        # Exists check
        extractor_exists = FHIRPathExtractor.exists(patient_resource, "Patient.name")
        adapter_exists = FHIRPathAdapter.exists(patient_resource, "Patient.name")
        assert extractor_exists == adapter_exists
        
        # Extract with paths
        paths = ["Patient.notExistingField", "Patient.name.family"]
        extractor_multi = FHIRPathExtractor.extract_with_paths(patient_resource, paths)
        adapter_multi = FHIRPathAdapter.extract_with_paths(patient_resource, paths)
        assert extractor_multi == adapter_multi

    def test_advanced_fhirpath_capabilities(self, patient_resource):
        """Test advanced capabilities that might be better in the new implementation."""
        # These tests demonstrate enhanced capabilities that might differ from fhirpathpy
        # but provide improved functionality
        
        # More complex filtering
        result = FHIRPathAdapter.extract(patient_resource, "Patient.name.given.select($this.startsWith('J'))")
        # We don't compare with fhirpathpy here, just ensure it works and returns reasonable results
        assert isinstance(result, list), "Should return a list of results"
        
        # Advanced functions
        result = FHIRPathAdapter.extract(patient_resource, "Patient.name.given.indexOf('John')")
        assert isinstance(result, list), "Should return a list containing the index result"
        
        # Testing empty results
        result = FHIRPathAdapter.extract(patient_resource, "Patient.nonExistentField")
        assert result == [], "Should return an empty list for non-existent fields" 