"""
Unit tests for the transform_utils module.
"""

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from epic_fhir_integration.transform.transform_utils import (calculate_age,
                                                           extract_birth_date,
                                                           extract_code_display,
                                                           extract_gender,
                                                           extract_language,
                                                           extract_observation_data,
                                                           extract_observation_value,
                                                           extract_patient_demographics,
                                                           transform_observation_to_row,
                                                           transform_patient_to_row)


class TestTransformUtils(unittest.TestCase):
    """Test cases for FHIR resource transformation utilities."""
    
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
    
    def test_calculate_age(self):
        """Test age calculation from birth date."""
        # Calculate expected age based on fixture birth date
        birth_date = "1980-06-15"
        birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.now()
        expected_age = today.year - birth_date_obj.year
        if (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day):
            expected_age -= 1
            
        # Test the function
        calculated_age = calculate_age(birth_date)
        self.assertEqual(calculated_age, expected_age)
        
        # Test with invalid birth date
        self.assertIsNone(calculate_age("invalid-date"))
        self.assertIsNone(calculate_age(None))
    
    def test_extract_birth_date(self):
        """Test birth date extraction from patient resource."""
        # Test normal extraction
        self.assertEqual(extract_birth_date(self.patient), "1980-06-15")
        
        # Test with missing birth date
        patient_without_birthdate = self.patient.copy()
        patient_without_birthdate.pop("birthDate")
        self.assertIsNone(extract_birth_date(patient_without_birthdate))
        
        # Test with birth date in extension
        patient_with_extension = patient_without_birthdate.copy()
        patient_with_extension["extension"].append({
            "url": "http://hl7.org/fhir/StructureDefinition/patient-birthDate",
            "valueDate": "1980-06-15"
        })
        self.assertEqual(extract_birth_date(patient_with_extension), "1980-06-15")
    
    def test_extract_gender(self):
        """Test gender extraction from patient resource."""
        # Test normal extraction
        self.assertEqual(extract_gender(self.patient), "male")
        
        # Test with missing gender
        patient_without_gender = self.patient.copy()
        patient_without_gender.pop("gender")
        self.assertIsNone(extract_gender(patient_without_gender))
        
        # Test with gender in extension
        patient_with_extension = patient_without_gender.copy()
        patient_with_extension["extension"].append({
            "url": "http://hl7.org/fhir/StructureDefinition/patient-gender",
            "valueCode": "female"
        })
        self.assertEqual(extract_gender(patient_with_extension), "female")
        
        # Test normalization of gender values
        patient_with_abbrev = patient_without_gender.copy()
        patient_with_abbrev["gender"] = "M"
        self.assertEqual(extract_gender(patient_with_abbrev), "male")
    
    def test_extract_language(self):
        """Test language extraction from patient resource."""
        # Test normal extraction
        language = extract_language(self.patient)
        self.assertEqual(language, "English")
        
        # Test with missing communication section
        patient_without_comm = self.patient.copy()
        patient_without_comm.pop("communication")
        self.assertIsNone(extract_language(patient_without_comm))
    
    def test_extract_patient_demographics(self):
        """Test comprehensive demographics extraction."""
        demographics = extract_patient_demographics(self.patient)
        
        # Check basic fields
        self.assertEqual(demographics["patient_id"], "example-patient-1")
        self.assertEqual(demographics["gender"], "male")
        self.assertEqual(demographics["birth_date"], "1980-06-15")
        self.assertIn("age", demographics)
        
        # Check name components
        self.assertEqual(demographics["name"]["family"], "Doe")
        self.assertEqual(demographics["name"]["first"], "John")
        
        # Check address
        self.assertEqual(demographics["address"]["city"], "Anytown")
        self.assertEqual(demographics["address"]["state"], "CA")
        
        # Check extensions
        self.assertEqual(demographics["ethnicity"], "Hispanic or Latino")
        self.assertEqual(demographics["race"], "White")
    
    def test_transform_patient_to_row(self):
        """Test transformation of patient resource to row format."""
        row = transform_patient_to_row(self.patient)
        
        # Check flattened fields
        self.assertEqual(row["patient_id"], "example-patient-1")
        self.assertEqual(row["gender"], "male")
        self.assertEqual(row["birth_date"], "1980-06-15")
        self.assertEqual(row["name_family"], "Doe")
        self.assertEqual(row["name_first"], "John")
        self.assertEqual(row["address_city"], "Anytown")
        self.assertEqual(row["address_state"], "CA")
        self.assertEqual(row["has_birth_date"], "yes")
        self.assertEqual(row["has_gender"], "yes")
    
    def test_extract_code_display(self):
        """Test extraction of display text from codeable concept."""
        # Create a test codeable concept
        concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }
            ],
            "text": "Heart rate measurement"
        }
        
        # Test with text present (should be preferred)
        self.assertEqual(extract_code_display(concept), "Heart rate measurement")
        
        # Test without text
        concept_without_text = concept.copy()
        concept_without_text.pop("text")
        self.assertEqual(extract_code_display(concept_without_text), "Heart rate")
        
        # Test with neither text nor display
        concept_minimal = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4"
                }
            ]
        }
        self.assertEqual(extract_code_display(concept_minimal), "8867-4")
    
    def test_extract_observation_value(self):
        """Test extraction of observation value."""
        # Test quantity value (from fixture)
        value_data = extract_observation_value(self.observation)
        self.assertEqual(value_data["value"], 80)
        self.assertEqual(value_data["unit"], "beats/minute")
        self.assertEqual(value_data["type"], "quantity")
        self.assertEqual(value_data["text"], "80 beats/minute")
        
        # Test string value
        observation_string = self.observation.copy()
        observation_string.pop("valueQuantity")
        observation_string["valueString"] = "Normal"
        value_data = extract_observation_value(observation_string)
        self.assertEqual(value_data["value"], "Normal")
        self.assertEqual(value_data["type"], "string")
        
        # Test boolean value
        observation_boolean = self.observation.copy()
        observation_boolean.pop("valueQuantity")
        observation_boolean["valueBoolean"] = True
        value_data = extract_observation_value(observation_boolean)
        self.assertEqual(value_data["value"], True)
        self.assertEqual(value_data["type"], "boolean")
        self.assertEqual(value_data["text"], "Yes")
    
    def test_extract_observation_data(self):
        """Test comprehensive observation data extraction."""
        observation_data = extract_observation_data(self.observation)
        
        # Check basic fields
        self.assertEqual(observation_data["observation_id"], "example-observation-1")
        self.assertEqual(observation_data["patient_id"], "example-patient-1")
        self.assertEqual(observation_data["status"], "final")
        
        # Check code information
        self.assertEqual(observation_data["code"]["text"], "Heart rate")
        self.assertEqual(observation_data["code"]["system"], "http://loinc.org")
        self.assertEqual(observation_data["code"]["code"], "8867-4")
        
        # Check value information
        self.assertEqual(observation_data["value"]["value"], 80)
        self.assertEqual(observation_data["value"]["unit"], "beats/minute")
        
        # Check dates
        self.assertEqual(observation_data["effective_date"], "2023-05-15T15:00:00Z")
        self.assertEqual(observation_data["issued_date"], "2023-05-15T15:05:00Z")
        
        # Check categories
        self.assertEqual(observation_data["categories"], ["Vital Signs"])
        
        # Check reference ranges
        self.assertEqual(len(observation_data["reference_ranges"]), 1)
        ref_range = observation_data["reference_ranges"][0]
        self.assertEqual(ref_range["low"]["value"], 60)
        self.assertEqual(ref_range["high"]["value"], 100)
    
    def test_transform_observation_to_row(self):
        """Test transformation of observation resource to row format."""
        row = transform_observation_to_row(self.observation)
        
        # Check flattened fields
        self.assertEqual(row["observation_id"], "example-observation-1")
        self.assertEqual(row["patient_id"], "example-patient-1")
        self.assertEqual(row["code"], "Heart rate")
        self.assertEqual(row["code_system"], "http://loinc.org")
        self.assertEqual(row["value"], "80")
        self.assertEqual(row["value_unit"], "beats/minute")
        self.assertEqual(row["status"], "final")
        self.assertEqual(row["category"], "Vital Signs")
        self.assertIn("reference_range", row)


if __name__ == "__main__":
    unittest.main() 