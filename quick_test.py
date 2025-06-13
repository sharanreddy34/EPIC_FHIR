#!/usr/bin/env python3
"""
Quick Test for FHIR Resource Transformer

This script tests the FHIR resource transformer to verify that it works.
"""

import json
from pathlib import Path
from epic_fhir_integration.transform.fhir_resource_transformer import transform_resource_bronze_to_gold

# Create a simple Patient with issues
patient = {
    "resourceType": "Patient",
    "id": "test-patient",
    "birthDate": "01/01/1980",  # Wrong format
    "name": [{"given": ["John"]}]  # Missing family name
}

# Transform and output
output_dir = Path("quick_test_output")
output_dir.mkdir(exist_ok=True)

# Direct transformation to gold
gold_patient = transform_resource_bronze_to_gold(patient)

# Save output
print("Transforming patient to gold tier...")
with open(output_dir / "gold_patient.json", "w") as f:
    json.dump(gold_patient, f, indent=2)

# Print key transformations
print("\nKey transformations:")
print(f"- Added name.use: {gold_patient['name'][0].get('use', 'NOT ADDED')}")
print(f"- Added name.text: {gold_patient['name'][0].get('text', 'NOT ADDED')}")
print(f"- Added identifier: {'identifier' in gold_patient}")
print(f"- Added narrative: {'text' in gold_patient}")
print(f"- Added PHI tags: {'security' in gold_patient['meta'] if 'meta' in gold_patient else False}")

print(f"\nOutput saved to {output_dir}/gold_patient.json") 