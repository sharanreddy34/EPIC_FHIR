"""
Unit tests for the validators module.
"""

import json
import os
import unittest
from pathlib import Path

from epic_fhir_integration.utils.validators import (extract_field_value,
                                                   extract_with_fallback,
                                                   suggest_corrections,
                                                   validate_consistency,
                                                   validate_date_format,
                                                   validate_field_value,
                                                   validate_resource)


class TestValidators(unittest.TestCase):
    """Test cases for FHIR resource validators."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Load test fixtures
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        with open(fixtures_dir / "sample_patient.json") as f:
            self.patient = json.load(f)
            
        with open(fixtures_dir / "sample_observation.json") as f:
            self.observation = json.load(f)
            
        with open(fixtures_dir / "sample_encounter.json") as f:
            self.encounter = json.load(f)
            
        # Create a resource bundle for consistency tests
        self.resources = {
            "Patient": [self.patient],
            "Observation": [self.observation],
            "Encounter": [self.encounter]
        }
    
    def test_extract_field_value(self):
        """Test extracting field values from resources."""
        # Test simple field extraction
        self.assertEqual(
            extract_field_value(self.patient, "gender"), 
            "male"
        )
        
        # Test nested field extraction
        self.assertEqual(
            extract_field_value(self.patient, "name.0.family"), 
            "Doe"
        )
        
        # Test array index notation
        self.assertEqual(
            extract_field_value(self.patient, "telecom[0].value"), 
            "555-123-4567"
        )
        
        # Test array filter notation
        self.assertEqual(
            extract_field_value(self.patient, "name[use=official].family"), 
            "Doe"
        )
        
        # Test non-existent field
        self.assertIsNone(extract_field_value(self.patient, "non_existent_field"))
    
    def test_validate_date_format(self):
        """Test date format validation."""
        # Test valid date formats
        self.assertTrue(validate_date_format("2023-05-15"))
        self.assertTrue(validate_date_format("2023-05-15T14:30:00Z"))
        self.assertTrue(validate_date_format("2023-05-15T14:30:00.123Z"))
        self.assertTrue(validate_date_format("2023-05-15T14:30:00+01:00"))
        
        # Test invalid date formats
        self.assertFalse(validate_date_format("05/15/2023"))
        self.assertFalse(validate_date_format("2023-5-15"))
        self.assertFalse(validate_date_format("not a date"))
    
    def test_validate_field_value(self):
        """Test field value validation against schema."""
        # Test string validation
        field_schema = {"type": "string", "required": True}
        self.assertEqual(validate_field_value("test", field_schema), (True, None))
        self.assertEqual(validate_field_value(None, field_schema), (False, "Required field is missing"))
        self.assertEqual(validate_field_value(123, field_schema), (False, "Expected string but got int"))
        
        # Test date validation
        field_schema = {
            "type": "string", 
            "validation": "date",
            "required": False
        }
        self.assertEqual(validate_field_value("2023-05-15", field_schema), (True, None))
        self.assertEqual(validate_field_value(None, field_schema), (True, None))  # Not required
    
    def test_validate_resource(self):
        """Test resource validation against schema."""
        # Test valid patient resource
        errors = validate_resource(self.patient)
        self.assertEqual(len(errors), 0)
        
        # Test missing required field
        invalid_patient = self.patient.copy()
        invalid_patient.pop("id")
        errors = validate_resource(invalid_patient)
        self.assertGreater(len(errors), 0)
        
        # Test invalid field type
        invalid_patient = self.patient.copy()
        invalid_patient["active"] = "yes"  # Should be boolean
        errors = validate_resource(invalid_patient)
        self.assertGreater(len(errors), 0)
    
    def test_validate_consistency(self):
        """Test consistency validation across resources."""
        errors = validate_consistency(self.resources)
        self.assertEqual(len(errors), 0)
        
        # Test inconsistent patient reference
        inconsistent_resources = self.resources.copy()
        inconsistent_observation = self.observation.copy()
        inconsistent_observation["subject"]["reference"] = "Patient/wrong-id"
        inconsistent_resources["Observation"] = [inconsistent_observation]
        
        errors = validate_consistency(inconsistent_resources)
        self.assertGreater(len(errors), 0)
    
    def test_suggest_corrections(self):
        """Test generating correction suggestions for validation errors."""
        # Create some validation errors
        validation_errors = [
            {
                "resource_type": "Patient",
                "resource_id": "example-patient-1",
                "field": "gender",
                "message": "Value 'unknown_gender' is not one of the allowed values: [male, female, other, unknown]",
                "value": "unknown_gender"
            },
            {
                "resource_type": "Patient",
                "resource_id": "example-patient-1",
                "field": "birthDate",
                "message": "Value '05/15/1980' does not match pattern '^\\d{4}-\\d{2}-\\d{2}$'",
                "value": "05/15/1980"
            }
        ]
        
        suggestions = suggest_corrections(validation_errors)
        
        # Check if we got suggestions for the patient
        self.assertIn("example-patient-1", suggestions)
        
        # Check if we got suggestions for both fields
        corrections = suggestions["example-patient-1"]["corrections"]
        self.assertEqual(len(corrections), 2)
        
        # Check if gender suggestion includes allowed values
        gender_correction = next(c for c in corrections if c["field"] == "gender")
        self.assertIn("allowed values", gender_correction["suggestion"])
        
        # Check if birthDate suggestion mentions date format
        date_correction = next(c for c in corrections if c["field"] == "birthDate")
        self.assertIn("date format", date_correction["suggestion"])


if __name__ == "__main__":
    unittest.main() 