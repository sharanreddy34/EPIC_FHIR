"""
Unit tests for the codeable_concept module.
"""

import unittest

from epic_fhir_integration.utils.codeable_concept import (
    extract_display,
    extract_coding_details,
    normalize_value,
    code_lookup,
    extract_concepts_from_array,
    get_code_system_name
)


class TestCodeableConcept(unittest.TestCase):
    """Test cases for CodeableConcept utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample CodeableConcept with both text and coding
        self.complete_concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                }
            ],
            "text": "Systolic BP"
        }
        
        # CodeableConcept with only coding
        self.coding_only_concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                }
            ]
        }
        
        # CodeableConcept with only text
        self.text_only_concept = {
            "text": "Systolic BP"
        }
        
        # CodeableConcept with multiple coding entries
        self.multiple_coding_concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                },
                {
                    "system": "http://snomed.info/sct",
                    "code": "271649006",
                    "display": "Systolic blood pressure"
                }
            ],
            "text": "Systolic BP"
        }
        
        # CodeableConcept without display
        self.no_display_concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6"
                }
            ]
        }
        
        # Sample lookup table
        self.lookup_table = {
            ("http://loinc.org", "8480-6"): "Systolic blood pressure",
            ("http://snomed.info/sct", "271649006"): "Systolic blood pressure"
        }
        
    def test_extract_display(self):
        """Test extracting display from CodeableConcept."""
        # Test with complete concept - should prefer text
        self.assertEqual(extract_display(self.complete_concept), "Systolic BP")
        
        # Test with coding only
        self.assertEqual(extract_display(self.coding_only_concept), "Systolic blood pressure")
        
        # Test with text only
        self.assertEqual(extract_display(self.text_only_concept), "Systolic BP")
        
        # Test with no display in coding
        self.assertEqual(extract_display(self.no_display_concept), "8480-6")
        
        # Test with None
        self.assertIsNone(extract_display(None))
        
        # Test with non-dict
        self.assertIsNone(extract_display("not a dict"))
        
    def test_extract_coding_details(self):
        """Test extracting detailed information from CodeableConcept."""
        # Test with complete concept
        details = extract_coding_details(self.complete_concept)
        self.assertEqual(details["display"], "Systolic BP")
        self.assertEqual(details["code"], "8480-6")
        self.assertEqual(details["system"], "http://loinc.org")
        self.assertEqual(details["system_name"], "LOINC")
        
        # Test with preferred system that matches
        details = extract_coding_details(self.multiple_coding_concept, "http://snomed.info/sct")
        self.assertEqual(details["code"], "271649006")
        self.assertEqual(details["system"], "http://snomed.info/sct")
        self.assertEqual(details["system_name"], "SNOMED")
        
        # Test with preferred system that doesn't match (should use first coding)
        details = extract_coding_details(self.multiple_coding_concept, "http://unknown.system")
        self.assertEqual(details["code"], "8480-6")
        self.assertEqual(details["system"], "http://loinc.org")
        
        # Test with non-dict
        self.assertEqual(extract_coding_details("not a dict"), {})
        
    def test_normalize_value(self):
        """Test normalizing values to standard forms."""
        # Test gender normalization
        self.assertEqual(normalize_value("male"), "male")
        self.assertEqual(normalize_value("M"), "male")
        self.assertEqual(normalize_value("Man"), "male")
        self.assertEqual(normalize_value("female"), "female")
        self.assertEqual(normalize_value("F"), "female")
        self.assertEqual(normalize_value("Woman"), "female")
        
        # Test severity normalization
        self.assertEqual(normalize_value("mild"), "mild")
        self.assertEqual(normalize_value("light"), "mild")
        self.assertEqual(normalize_value("moderate"), "moderate")
        self.assertEqual(normalize_value("medium"), "moderate")
        self.assertEqual(normalize_value("severe"), "severe")
        self.assertEqual(normalize_value("high"), "severe")
        self.assertEqual(normalize_value("critical"), "severe")
        
        # Test status normalization
        self.assertEqual(normalize_value("active"), "active")
        self.assertEqual(normalize_value("in progress"), "active")
        self.assertEqual(normalize_value("in-progress"), "active")
        self.assertEqual(normalize_value("completed"), "completed")
        self.assertEqual(normalize_value("finished"), "completed")
        self.assertEqual(normalize_value("resolved"), "completed")
        
        # Test unknown value
        self.assertEqual(normalize_value("unknown value"), "unknown value")
        
        # Test non-string
        self.assertEqual(normalize_value(None), None)
        self.assertEqual(normalize_value(123), 123)
        
    def test_code_lookup(self):
        """Test looking up display values for codes."""
        # Test lookup with existing code
        self.assertEqual(
            code_lookup("8480-6", "http://loinc.org", self.lookup_table),
            "Systolic blood pressure"
        )
        
        # Test lookup with non-existent code
        self.assertIsNone(
            code_lookup("unknown", "http://loinc.org", self.lookup_table)
        )
        
    def test_extract_concepts_from_array(self):
        """Test extracting details from an array of CodeableConcepts."""
        # Test with array of concepts
        concepts = [self.complete_concept, self.coding_only_concept]
        results = extract_concepts_from_array(concepts)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["display"], "Systolic BP")
        self.assertEqual(results[1]["display"], "Systolic blood pressure")
        
        # Test with preferred system
        concepts = [self.multiple_coding_concept]
        results = extract_concepts_from_array(concepts, "http://snomed.info/sct")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["system"], "http://snomed.info/sct")
        self.assertEqual(results[0]["code"], "271649006")
        
        # Test with empty list
        self.assertEqual(extract_concepts_from_array([]), [])
        
        # Test with None
        self.assertEqual(extract_concepts_from_array(None), [])
        
    def test_get_code_system_name(self):
        """Test getting human-readable names for code system URLs."""
        self.assertEqual(get_code_system_name("http://loinc.org"), "LOINC")
        self.assertEqual(get_code_system_name("http://snomed.info/sct"), "SNOMED")
        self.assertEqual(get_code_system_name("http://www.nlm.nih.gov/research/umls/rxnorm"), "RxNorm")
        
        # Test with unknown system
        self.assertIsNone(get_code_system_name("http://unknown.system"))
        

if __name__ == "__main__":
    unittest.main() 