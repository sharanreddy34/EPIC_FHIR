#!/usr/bin/env python3
"""
Standalone FHIR Transformation Test

This script directly tests the FHIR transformation functionality without
relying on package imports that have dependency issues.
"""

import json
import os
import sys
from pathlib import Path

# Import the transformation module directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from epic_fhir_integration.transform.fhir_resource_transformer import (
    FHIRResourceTransformer,
    transform_resource_bronze_to_silver,
    transform_resource_silver_to_gold,
    transform_resource_bronze_to_gold
)

def test_patient_transformations():
    """Test transformations on a Patient resource with various issues."""
    # Create test output directory
    output_dir = Path("transformation_test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create a test patient with various issues
    patient = {
        "resourceType": "Patient",
        "id": "test-patient",
        "meta": {
            "lastUpdated": "2023-01-01T12:00:00Z"
        },
        "name": [
            {
                "given": ["John", "Q"],
                # Missing family name
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
    
    # Save original bronze resource
    with open(output_dir / "patient_bronze.json", "w") as f:
        json.dump(patient, f, indent=2)
    
    print("STEP 1: Bronze to Silver Transformation")
    silver_patient = transform_resource_bronze_to_silver(patient)
    
    # Save silver resource
    with open(output_dir / "patient_silver.json", "w") as f:
        json.dump(silver_patient, f, indent=2)
    
    # Check key fixes in silver tier
    print("\nSilver tier fixes:")
    
    # Check data consistency fixes
    print("- Data consistency (gender):", end=" ")
    if any(
        ext.get("url") == "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
        for ext in silver_patient["_gender"]["extension"]
    ):
        print("❌ Failed - data-absent-reason extension still present")
    else:
        print("✅ Fixed - removed inconsistent data-absent-reason extension")
    
    # Check name.use fixes
    print("- Name use validation:", end=" ")
    if silver_patient["name"][0]["use"] != "usual":
        print(f"❌ Failed - invalid use '{silver_patient['name'][0]['use']}' not corrected")
    else:
        print("✅ Fixed - corrected invalid name use to 'usual'")
    
    # Check for added identifier
    print("- Required identifier:", end=" ")
    if "identifier" not in silver_patient:
        print("❌ Failed - missing identifier not added")
    else:
        print("✅ Fixed - added required identifier")
    
    # Check for birthDate validation
    print("- BirthDate validation:", end=" ")
    if "_birthDate" not in silver_patient or "extension" not in silver_patient["_birthDate"]:
        print("❌ Failed - missing validation for invalid birthDate")
    else:
        print("✅ Fixed - added validation warning for invalid birthDate")
    
    # Check telecom system fix
    print("- Telecom system validation:", end=" ")
    if silver_patient["telecom"][0]["system"] != "other":
        print(f"❌ Failed - invalid system '{silver_patient['telecom'][0]['system']}' not corrected")
    else:
        print("✅ Fixed - corrected invalid telecom system to 'other'")
    
    print("\nSTEP 2: Silver to Gold Transformation")
    gold_patient = transform_resource_silver_to_gold(silver_patient)
    
    # Save gold resource
    with open(output_dir / "patient_gold.json", "w") as f:
        json.dump(gold_patient, f, indent=2)
    
    # Check key fixes in gold tier
    print("\nGold tier fixes:")
    
    # Check for extension structure fixes
    print("- Extension structure:", end=" ")
    race_ext = None
    for ext in gold_patient["extension"]:
        if ext["url"] == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
            race_ext = ext
            break
    
    if not race_ext or "extension" not in race_ext:
        print("❌ Failed - race extension not properly structured")
    else:
        has_omb = any(nested["url"] == "ombCategory" for nested in race_ext["extension"])
        has_text = any(nested["url"] == "text" for nested in race_ext["extension"])
        if not has_omb or not has_text:
            print("❌ Failed - race extension missing required components")
        else:
            print("✅ Fixed - added required components to race extension")
    
    # Check for narrative
    print("- Narrative generation:", end=" ")
    if "text" not in gold_patient or "div" not in gold_patient["text"]:
        print("❌ Failed - narrative not generated")
    else:
        print("✅ Fixed - comprehensive narrative generated")
    
    # Check for PHI security tags
    print("- PHI handling:", end=" ")
    has_phi_tag = False
    if "meta" in gold_patient and "security" in gold_patient["meta"]:
        has_phi_tag = any(
            sec.get("code") == "PHI" for sec in gold_patient["meta"]["security"]
        )
    
    if not has_phi_tag:
        print("❌ Failed - PHI security tags not added")
    else:
        print("✅ Fixed - PHI security tags added")
    
    print("\nSTEP 3: Direct Bronze to Gold Transformation")
    direct_gold_patient = transform_resource_bronze_to_gold(patient)
    
    # Save direct gold resource
    with open(output_dir / "patient_direct_gold.json", "w") as f:
        json.dump(direct_gold_patient, f, indent=2)
    
    # Check if direct transformation produces equivalent results
    print("\nDirect Bronze to Gold equivalence check:")
    
    # Compare key parts of both gold resources
    if gold_patient["meta"]["tag"] == direct_gold_patient["meta"]["tag"]:
        print("✅ Quality tier tags match")
    else:
        print("❌ Quality tier tags differ")
    
    if "text" in gold_patient and "text" in direct_gold_patient:
        print("✅ Both have narratives")
    else:
        print("❌ Narrative presence differs")
    
    if ("meta" in gold_patient and "security" in gold_patient["meta"] and
        "meta" in direct_gold_patient and "security" in direct_gold_patient["meta"]):
        print("✅ Both have security metadata")
    else:
        print("❌ Security metadata differs")
    
    print(f"\nTransformation test complete! Output files saved to {output_dir}")

def test_observation_transformations():
    """Test transformations on an Observation resource with various issues."""
    # Create test output directory
    output_dir = Path("transformation_test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create a test observation with various issues
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
    
    # Transform directly to gold
    gold_observation = transform_resource_bronze_to_gold(observation)
    
    # Save gold resource
    with open(output_dir / "observation_gold.json", "w") as f:
        json.dump(gold_observation, f, indent=2)
    
    # Check key fixes
    print("\nObservation transformation fixes:")
    
    # Check status fix
    print("- Required status:", end=" ")
    if "status" not in gold_observation:
        print("❌ Failed - missing status not added")
    else:
        print(f"✅ Fixed - added status '{gold_observation['status']}'")
    
    # Check subject reference fix
    print("- Subject reference format:", end=" ")
    if not gold_observation["subject"]["reference"].startswith("Patient/"):
        print("❌ Failed - subject reference format not fixed")
    else:
        print(f"✅ Fixed - corrected to '{gold_observation['subject']['reference']}'")
    
    # Check for narrative
    print("- Narrative generation:", end=" ")
    if "text" not in gold_observation or "div" not in gold_observation["text"]:
        print("❌ Failed - narrative not generated")
    else:
        print("✅ Fixed - narrative generated")

def test_encounter_transformations():
    """Test transformations on an Encounter resource with various issues."""
    # Create test output directory
    output_dir = Path("transformation_test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create a test encounter with various issues
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
    
    # Transform directly to gold
    gold_encounter = transform_resource_bronze_to_gold(encounter)
    
    # Save gold resource
    with open(output_dir / "encounter_gold.json", "w") as f:
        json.dump(gold_encounter, f, indent=2)
    
    # Check key fixes
    print("\nEncounter transformation fixes:")
    
    # Check status fix
    print("- Status validation:", end=" ")
    if gold_encounter["status"] != "unknown":
        print(f"❌ Failed - invalid status not corrected to 'unknown'")
    else:
        print("✅ Fixed - corrected invalid status to 'unknown'")
    
    # Check period datetime format fix
    print("- Period datetime format:", end=" ")
    if "period" not in gold_encounter:
        print("❌ Failed - period missing")
    elif "start" not in gold_encounter["period"] or "end" not in gold_encounter["period"]:
        print("❌ Failed - period fields missing")
    else:
        has_t_start = "T" in gold_encounter["period"]["start"]
        has_t_end = "T" in gold_encounter["period"]["end"]
        if not has_t_start or not has_t_end:
            print("❌ Failed - datetime format not corrected")
        else:
            print("✅ Fixed - corrected datetime format")
    
    # Check for narrative
    print("- Narrative generation:", end=" ")
    if "text" not in gold_encounter or "div" not in gold_encounter["text"]:
        print("❌ Failed - narrative not generated")
    else:
        print("✅ Fixed - narrative generated")

if __name__ == "__main__":
    print("Running FHIR Transformation Tests\n")
    print("=" * 50)
    print("PATIENT TRANSFORMATION TEST")
    print("=" * 50)
    test_patient_transformations()
    
    print("\n" + "=" * 50)
    print("OBSERVATION TRANSFORMATION TEST")
    print("=" * 50)
    test_observation_transformations()
    
    print("\n" + "=" * 50)
    print("ENCOUNTER TRANSFORMATION TEST")
    print("=" * 50)
    test_encounter_transformations()
    
    print("\nAll tests completed!") 