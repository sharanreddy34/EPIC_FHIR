#!/usr/bin/env python3
"""
FHIR Transformation Tests

This script tests the FHIR resource transformation functionality and 
validates that it addresses all the identified issues.
"""

import os
import sys
import json
import logging
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import transformation functions
from epic_fhir_integration.transform.fhir_resource_transformer import (
    transform_resource_bronze_to_silver,
    transform_resource_silver_to_gold,
    transform_resource_bronze_to_gold,
    FHIRResourceTransformer
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base test case
class FHIRTransformationTestCase(unittest.TestCase):
    """Base class for FHIR transformation tests."""
    
    def setUp(self):
        """Set up test resources."""
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create a transformer instance
        self.transformer = FHIRResourceTransformer(validation_mode="strict", debug=True)
    
    def tearDown(self):
        """Clean up after tests."""
        # Could remove test files here if needed
        pass

class TestBronzeToSilverTransformations(FHIRTransformationTestCase):
    """Test Bronze to Silver transformations."""
    
    def test_issue1_data_consistency(self):
        """Test fixing data consistency issues."""
        # Create a patient with inconsistent gender data
        patient = {
            "resourceType": "Patient",
            "id": "inconsistent-gender",
            "gender": "male",
            "_gender": {
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                        "valueCode": "unknown"
                    }
                ]
            }
        }
        
        # Transform to Silver
        silver_patient = self.transformer.bronze_to_silver(patient)
        
        # Verify fix: Should remove data-absent-reason extension since gender is present
        self.assertEqual(silver_patient["gender"], "male")
        self.assertFalse(any(
            ext.get("url") == "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
            for ext in silver_patient["_gender"]["extension"]
        ), "Data-absent-reason extension should be removed when gender is present")
        
        # Output to file for inspection
        with open(self.output_dir / "issue1_silver.json", "w") as f:
            json.dump(silver_patient, f, indent=2)
    
    def test_issue3_cardinality_requirements(self):
        """Test fixing missing cardinality requirements."""
        # Create a patient with missing required fields
        patient = {
            "resourceType": "Patient",
            "id": "missing-requirements",
            "name": [
                {
                    "given": ["John"]
                    # Missing "family" and "text"
                    # Missing "use"
                }
            ]
            # Missing "identifier"
        }
        
        # Transform to Silver
        silver_patient = self.transformer.bronze_to_silver(patient)
        
        # Verify fixes:
        
        # 1. name.use should be added
        self.assertIn("use", silver_patient["name"][0])
        
        # 2. name.text should be generated from given name
        self.assertIn("text", silver_patient["name"][0])
        self.assertEqual(silver_patient["name"][0]["text"], "John")
        
        # 3. identifier should be added
        self.assertIn("identifier", silver_patient)
        self.assertEqual(len(silver_patient["identifier"]), 1)
        self.assertEqual(silver_patient["identifier"][0]["value"], "TEMP-missing-requirements")
        
        # Output to file for inspection
        with open(self.output_dir / "issue3_silver.json", "w") as f:
            json.dump(silver_patient, f, indent=2)
    
    def test_issue6_validation_logic(self):
        """Test adding validation logic for invalid data."""
        # Create a patient with invalid date
        patient = {
            "resourceType": "Patient",
            "id": "invalid-date",
            "birthDate": "01/01/2000"  # Wrong format, should be YYYY-MM-DD
        }
        
        # Transform to Silver
        silver_patient = self.transformer.bronze_to_silver(patient)
        
        # Verify fix: Should add validation warning extension
        self.assertIn("_birthDate", silver_patient)
        self.assertIn("extension", silver_patient["_birthDate"])
        
        # Should keep the original data
        self.assertEqual(silver_patient["birthDate"], "01/01/2000")
        
        # Should have validation warning
        has_validation_warning = any(
            ext.get("url") == "http://example.org/fhir/StructureDefinition/validation-issue"
            for ext in silver_patient["_birthDate"]["extension"]
        )
        self.assertTrue(has_validation_warning, "Should add validation warning for invalid date")
        
        # Output to file for inspection
        with open(self.output_dir / "issue6_silver.json", "w") as f:
            json.dump(silver_patient, f, indent=2)

class TestSilverToGoldTransformations(FHIRTransformationTestCase):
    """Test Silver to Gold transformations."""
    
    def test_issue2_profile_conformance(self):
        """Test ensuring profile conformance only when requirements are met."""
        # Create two patients - one that meets US Core requirements, one that doesn't
        patient_meets_requirements = {
            "resourceType": "Patient",
            "id": "meets-requirements",
            "identifier": [{
                "system": "http://example.org/fhir/identifier/mrn",
                "value": "12345"
            }],
            "name": [{
                "family": "Smith",
                "given": ["John"]
            }]
        }
        
        patient_missing_requirements = {
            "resourceType": "Patient",
            "id": "missing-requirements",
            # Missing identifier and name.family
            "name": [{
                "given": ["John"]
            }]
        }
        
        # Transform both to Gold
        gold_patient1 = transform_resource_bronze_to_gold(patient_meets_requirements)
        gold_patient2 = transform_resource_bronze_to_gold(patient_missing_requirements)
        
        # Patient 1 should have US Core profile
        self.assertIn("meta", gold_patient1)
        self.assertIn("profile", gold_patient1["meta"])
        self.assertIn("http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient", 
                    gold_patient1["meta"]["profile"])
        
        # Patient 2 should NOT have US Core profile since it doesn't meet requirements
        us_core_applied = False
        if "meta" in gold_patient2 and "profile" in gold_patient2["meta"]:
            us_core_applied = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient" in gold_patient2["meta"]["profile"]
        
        self.assertFalse(us_core_applied, 
                       "US Core profile should not be applied to resources that don't meet requirements")
        
        # Output to files for inspection
        with open(self.output_dir / "issue2_gold_meets_requirements.json", "w") as f:
            json.dump(gold_patient1, f, indent=2)
            
        with open(self.output_dir / "issue2_gold_missing_requirements.json", "w") as f:
            json.dump(gold_patient2, f, indent=2)
    
    def test_issue4_extension_structure(self):
        """Test fixing improper extension structure."""
        # Create a patient with US Core race extension that's missing components
        patient = {
            "resourceType": "Patient",
            "id": "improper-extension",
            "extension": [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
                    # Missing required nested extensions (ombCategory and text)
                }
            ]
        }
        
        # Transform to Gold
        gold_patient = transform_resource_bronze_to_gold(patient)
        
        # Verify fixes:
        race_extension = None
        for ext in gold_patient["extension"]:
            if ext["url"] == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
                race_extension = ext
                break
                
        self.assertIsNotNone(race_extension, "Race extension should be preserved")
        self.assertIn("extension", race_extension)
        
        # Should have ombCategory extension
        has_omb = any(nested["url"] == "ombCategory" for nested in race_extension["extension"])
        self.assertTrue(has_omb, "Should add missing ombCategory extension")
        
        # Should have text extension
        has_text = any(nested["url"] == "text" for nested in race_extension["extension"])
        self.assertTrue(has_text, "Should add missing text extension")
        
        # Output to file for inspection
        with open(self.output_dir / "issue4_gold.json", "w") as f:
            json.dump(gold_patient, f, indent=2)
    
    def test_issue7_narrative_generation(self):
        """Test generating comprehensive narrative."""
        # Create a patient with minimal data
        patient = {
            "resourceType": "Patient",
            "id": "minimal-data",
            "name": [{
                "family": "Smith",
                "given": ["John"]
            }],
            "gender": "male",
            "birthDate": "1980-01-01"
        }
        
        # Transform to Gold
        gold_patient = transform_resource_bronze_to_gold(patient)
        
        # Verify narrative is generated
        self.assertIn("text", gold_patient)
        self.assertIn("status", gold_patient["text"])
        self.assertEqual(gold_patient["text"]["status"], "generated")
        self.assertIn("div", gold_patient["text"])
        
        # Verify narrative contains key patient information
        narrative = gold_patient["text"]["div"]
        self.assertIn("Smith", narrative)
        self.assertIn("John", narrative)
        self.assertIn("male", narrative.lower())
        self.assertIn("1980-01-01", narrative)
        
        # Output to file for inspection
        with open(self.output_dir / "issue7_gold.json", "w") as f:
            json.dump(gold_patient, f, indent=2)
            
    def test_issue8_sensitive_data(self):
        """Test handling of sensitive data."""
        # Create a patient with PHI
        patient = {
            "resourceType": "Patient",
            "id": "contains-phi",
            "name": [{
                "family": "Smith",
                "given": ["John"]
            }],
            "birthDate": "1980-01-01",
            "telecom": [{
                "system": "phone",
                "value": "555-123-4567"
            }]
        }
        
        # Transform to Gold
        gold_patient = transform_resource_bronze_to_gold(patient)
        
        # Verify PHI handling
        self.assertIn("meta", gold_patient)
        self.assertIn("security", gold_patient["meta"])
        
        # Should have PHI security tag
        has_phi_tag = any(
            sec.get("system") == "http://terminology.hl7.org/CodeSystem/v3-ActCode" and
            sec.get("code") == "PHI"
            for sec in gold_patient["meta"]["security"]
        )
        self.assertTrue(has_phi_tag, "Should add PHI security tag")
        
        # Should have restricted handling tag
        has_restricted_tag = any(
            sec.get("system") == "http://example.org/fhir/security-tags" and
            sec.get("code") == "PHI-RESTRICTED"
            for sec in gold_patient["meta"]["security"]
        )
        self.assertTrue(has_restricted_tag, "Should add PHI-RESTRICTED security tag")
        
        # Output to file for inspection
        with open(self.output_dir / "issue8_gold.json", "w") as f:
            json.dump(gold_patient, f, indent=2)

class TestEndToEndTransformations(FHIRTransformationTestCase):
    """Test end-to-end transformations for common resource types."""
    
    def test_complete_patient_transformation(self):
        """Test complete transformation of a Patient resource."""
        # Create a realistic patient with various issues
        patient = {
            "resourceType": "Patient",
            "id": "test-patient-complete",
            "meta": {
                "lastUpdated": "2023-01-01T12:00:00Z"
            },
            "name": [
                {
                    "given": ["John", "Q"],
                    # No family name
                    "use": "invalid-use"  # Invalid value
                }
            ],
            "gender": "male",
            "_gender": {
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason",
                        "valueCode": "unknown"
                    }
                ]
            },
            "birthDate": "01/01/1980",  # Invalid format
            "telecom": [
                {
                    "system": "invalid-system",
                    "value": "555-123-4567"
                }
            ],
            "extension": [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
                    # Missing nested extensions
                }
            ]
        }
        
        # Transform through both tiers
        silver_patient = transform_resource_bronze_to_silver(patient)
        gold_patient = transform_resource_silver_to_gold(silver_patient)
        
        # Also test direct bronze-to-gold
        direct_gold_patient = transform_resource_bronze_to_gold(patient)
        
        # Write all versions to files
        with open(self.output_dir / "complete_bronze.json", "w") as f:
            json.dump(patient, f, indent=2)
            
        with open(self.output_dir / "complete_silver.json", "w") as f:
            json.dump(silver_patient, f, indent=2)
            
        with open(self.output_dir / "complete_gold.json", "w") as f:
            json.dump(gold_patient, f, indent=2)
            
        with open(self.output_dir / "complete_direct_gold.json", "w") as f:
            json.dump(direct_gold_patient, f, indent=2)
            
        # Verify both gold versions are equivalent
        self.assertEqual(
            gold_patient["meta"]["tag"], 
            direct_gold_patient["meta"]["tag"],
            "Quality tier tags should be the same in both gold versions"
        )
        
        # Check core fixes
        self.assertIn("family", gold_patient["name"][0]) 
        self.assertEqual(gold_patient["name"][0]["use"], "usual")
        self.assertIn("identifier", gold_patient)
        self.assertIn("text", gold_patient)
        self.assertIn("security", gold_patient["meta"])
    
    def test_observation_transformation(self):
        """Test transformation of an Observation resource."""
        observation = {
            "resourceType": "Observation",
            "id": "test-observation",
            # Missing status (required)
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }
                ]
            },
            "subject": {
                "reference": "12345"  # Invalid reference format
            },
            "valueQuantity": {
                "value": 140,
                "unit": "mmHg"
            }
        }
        
        # Transform
        gold_observation = transform_resource_bronze_to_gold(observation)
        
        # Verify fixes
        self.assertEqual(gold_observation["status"], "unknown")
        self.assertEqual(gold_observation["subject"]["reference"], "Patient/12345")
        self.assertIn("text", gold_observation)
        
        # Write to file
        with open(self.output_dir / "observation_gold.json", "w") as f:
            json.dump(gold_observation, f, indent=2)
    
    def test_encounter_transformation(self):
        """Test transformation of an Encounter resource."""
        encounter = {
            "resourceType": "Encounter",
            "id": "test-encounter",
            "status": "invalid-status",
            "class": {
                "code": "AMB",
                "display": "Ambulatory"
            },
            "period": {
                "start": "2023-01-01 12:00:00",  # Invalid format (missing T)
                "end": "2023-01-02 15:30:00"     # Invalid format (missing T)
            },
            "subject": {
                "reference": "Patient/12345"
            }
        }
        
        # Transform
        gold_encounter = transform_resource_bronze_to_gold(encounter)
        
        # Verify fixes
        self.assertEqual(gold_encounter["status"], "unknown")
        if "period" in gold_encounter:
            self.assertIn("T", gold_encounter["period"]["start"])
            self.assertIn("T", gold_encounter["period"]["end"])
        self.assertIn("text", gold_encounter)
        
        # Write to file
        with open(self.output_dir / "encounter_gold.json", "w") as f:
            json.dump(gold_encounter, f, indent=2)

if __name__ == "__main__":
    unittest.main() 