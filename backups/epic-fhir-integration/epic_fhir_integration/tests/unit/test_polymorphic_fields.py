"""
Unit tests for the polymorphic_fields module.
"""

import json
import unittest
from pathlib import Path

from epic_fhir_integration.utils.polymorphic_fields import (
    extract_best_polymorphic_value,
    extract_polymorphic_field,
    extract_value_from_polymorphic,
    identify_polymorphic_fields,
    get_normalized_type,
    get_preferred_extraction_type
)


class TestPolymorphicFields(unittest.TestCase):
    """Test cases for FHIR polymorphic field utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test resources with polymorphic fields
        self.observation = {
            "resourceType": "Observation",
            "id": "test-observation-1",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                }],
                "text": "Systolic blood pressure"
            },
            "subject": {
                "reference": "Patient/test-patient-1"
            },
            "effectiveDateTime": "2023-05-15T10:30:00Z",
            "valueQuantity": {
                "value": 120,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            }
        }
        
        self.condition = {
            "resourceType": "Condition",
            "id": "test-condition-1",
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                    "display": "Active"
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Diabetes"
                }],
                "text": "Type 2 Diabetes"
            },
            "subject": {
                "reference": "Patient/test-patient-1"
            },
            "onsetDateTime": "2022-01-15"
        }
        
        self.medication_request = {
            "resourceType": "MedicationRequest",
            "id": "test-medication-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "197381",
                    "display": "Amoxicillin"
                }],
                "text": "Amoxicillin 500mg"
            },
            "subject": {
                "reference": "Patient/test-patient-1"
            },
            "authoredOn": "2023-05-16T14:30:00Z"
        }
        
    def test_identify_polymorphic_fields(self):
        """Test identifying polymorphic fields in resources."""
        # Test observation polymorphic fields
        fields = identify_polymorphic_fields(self.observation)
        self.assertIn("value", fields)
        self.assertIn("effective", fields)
        
        # Test condition polymorphic fields
        fields = identify_polymorphic_fields(self.condition)
        self.assertIn("onset", fields)
        
        # Test medication request polymorphic fields
        fields = identify_polymorphic_fields(self.medication_request)
        self.assertIn("medication", fields)
        
        # Test with non-existent resource type
        fields = identify_polymorphic_fields({"resourceType": "NonExistent"})
        self.assertEqual(fields, [])
        
        # Test with missing resource type
        fields = identify_polymorphic_fields({})
        self.assertEqual(fields, [])
        
    def test_extract_polymorphic_field(self):
        """Test extracting polymorphic field values."""
        # Test extracting valueQuantity from Observation
        value, type_suffix = extract_polymorphic_field(self.observation, "value")
        self.assertEqual(type_suffix, "Quantity")
        self.assertEqual(value["value"], 120)
        self.assertEqual(value["unit"], "mmHg")
        
        # Test extracting effectiveDateTime from Observation
        value, type_suffix = extract_polymorphic_field(self.observation, "effective")
        self.assertEqual(type_suffix, "DateTime")
        self.assertEqual(value, "2023-05-15T10:30:00Z")
        
        # Test extracting onsetDateTime from Condition
        value, type_suffix = extract_polymorphic_field(self.condition, "onset")
        self.assertEqual(type_suffix, "DateTime")
        self.assertEqual(value, "2022-01-15")
        
        # Test extracting non-existent field
        value, type_suffix = extract_polymorphic_field(self.observation, "nonexistent")
        self.assertIsNone(value)
        self.assertIsNone(type_suffix)
        
    def test_get_normalized_type(self):
        """Test normalized type name conversion."""
        self.assertEqual(get_normalized_type("Quantity"), "quantity")
        self.assertEqual(get_normalized_type("CodeableConcept"), "codeableConcept")
        self.assertEqual(get_normalized_type("DateTime"), "dateTime")
        self.assertEqual(get_normalized_type("String"), "string")
        self.assertEqual(get_normalized_type("CustomType"), "customtype")  # Not in map, so lowercase
        
    def test_extract_value_from_polymorphic(self):
        """Test extracting structured values from polymorphic fields."""
        # Test extracting from valueQuantity
        result = extract_value_from_polymorphic(self.observation, "value")
        self.assertEqual(result["type"], "quantity")
        self.assertEqual(result["value"], 120)
        self.assertEqual(result["unit"], "mmHg")
        self.assertEqual(result["display"], "120 mmHg")
        
        # Test extracting from effectiveDateTime
        result = extract_value_from_polymorphic(self.observation, "effective")
        self.assertEqual(result["type"], "dateTime")
        self.assertEqual(result["value"], "2023-05-15T10:30:00Z")
        self.assertEqual(result["display"], "2023-05-15T10:30:00Z")
        
        # Test extracting from medicationCodeableConcept
        result = extract_value_from_polymorphic(self.medication_request, "medication")
        self.assertEqual(result["type"], "codeableConcept")
        self.assertEqual(result["code"], "197381")
        self.assertEqual(result["system"], "http://www.nlm.nih.gov/research/umls/rxnorm")
        self.assertEqual(result["display"], "Amoxicillin")
        self.assertEqual(result["value"], "Amoxicillin")
        
        # Test with non-existent field
        result = extract_value_from_polymorphic(self.observation, "nonexistent")
        self.assertEqual(result, {})
        
    def test_get_preferred_extraction_type(self):
        """Test preferred extraction type ordering."""
        # Test Observation value preferences
        types = get_preferred_extraction_type("value", "Observation")
        self.assertEqual(types[0], "Quantity")  # Should be first preference
        
        # Test Condition onset preferences
        types = get_preferred_extraction_type("onset", "Condition")
        self.assertEqual(types[0], "DateTime")  # Should be first preference
        
        # Test MedicationRequest medication preferences
        types = get_preferred_extraction_type("medication", "MedicationRequest")
        self.assertEqual(types[0], "CodeableConcept")  # Should be first preference
        
        # Test default preferences
        types = get_preferred_extraction_type("unknown", "Unknown")
        self.assertEqual(types[0], "String")  # Default first preference
        
    def test_extract_best_polymorphic_value(self):
        """Test extracting the best value from polymorphic fields."""
        # Test best value from valueQuantity
        value = extract_best_polymorphic_value(self.observation, "value")
        self.assertEqual(value, "120 mmHg")
        
        # Test best value from effectiveDateTime
        value = extract_best_polymorphic_value(self.observation, "effective")
        self.assertEqual(value, "2023-05-15T10:30:00Z")
        
        # Test best value from medicationCodeableConcept
        value = extract_best_polymorphic_value(self.medication_request, "medication")
        self.assertEqual(value, "Amoxicillin")
        
        # Test with non-existent field
        value = extract_best_polymorphic_value(self.observation, "nonexistent")
        self.assertIsNone(value)
        
        # Test with missing resource type
        value = extract_best_polymorphic_value({}, "value")
        self.assertIsNone(value)
        

if __name__ == "__main__":
    unittest.main() 