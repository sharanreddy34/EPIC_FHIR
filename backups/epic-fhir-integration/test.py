#!/usr/bin/env python3
"""
Quick Test for FHIR Resource Transformer

This script tests the FHIR resource transformer to verify that it works.
"""

import json
import sys
import os
from pathlib import Path

# Add the current directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import our transformer class
from epic_fhir_integration.transform.fhir_resource_transformer import FHIRResourceTransformer

# Create a simple Patient with issues
patient = {
    "resourceType": "Patient",
    "id": "test-patient",
    "birthDate": "01/01/1980",  # Wrong format
    "name": [{"given": ["John"]}]  # Missing family name
}

# Create output directory
output_dir = Path("test_output")
output_dir.mkdir(exist_ok=True)

# Save the original patient
with open(output_dir / "test_patient_bronze.json", "w") as f:
    json.dump(patient, f, indent=2)
    
print("Testing FHIR resource transformer...")

# Create a transformer instance
transformer = FHIRResourceTransformer(validation_mode="strict", debug=True)

# Transform to silver tier
silver_patient = transformer.bronze_to_silver(patient)

# Save silver tier patient
with open(output_dir / "test_patient_silver.json", "w") as f:
    json.dump(silver_patient, f, indent=2)
    
# Transform to gold tier
gold_patient = transformer.silver_to_gold(silver_patient)

# Save gold tier patient
with open(output_dir / "test_patient_gold.json", "w") as f:
    json.dump(gold_patient, f, indent=2)

print("\nTransformation complete!")
print(f"Bronze patient saved to: {output_dir}/test_patient_bronze.json")
print(f"Silver patient saved to: {output_dir}/test_patient_silver.json") 
print(f"Gold patient saved to: {output_dir}/test_patient_gold.json")
