#!/usr/bin/env python3
"""
Prototype for testing the fhirpath library as a replacement for fhirpathpy.

This prototype compares the functionality and performance of fhirpath vs fhirpathpy
for extracting data from FHIR resources.
"""

import json
import time
from typing import Any, Dict, List

# For comparing implementations
import fhirpathpy

# New implementation to test
# Note: This requires installation: pip install fhirpath
try:
    import fhirpath
    FHIRPATH_AVAILABLE = True
except ImportError:
    FHIRPATH_AVAILABLE = False
    print("fhirpath package not installed. Run: pip install fhirpath")


# Sample FHIR resources for testing
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "example",
    "active": True,
    "name": [
        {
            "use": "official",
            "family": "Smith",
            "given": ["John", "Jacob"]
        }
    ],
    "gender": "male",
    "birthDate": "1974-12-25",
    "address": [
        {
            "use": "home",
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345"
        }
    ],
    "telecom": [
        {
            "system": "phone",
            "value": "555-123-4567",
            "use": "home"
        },
        {
            "system": "email",
            "value": "john.smith@example.com"
        }
    ]
}

SAMPLE_OBSERVATION = {
    "resourceType": "Observation",
    "id": "blood-pressure",
    "status": "final",
    "category": [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }
            ]
        }
    ],
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }
        ],
        "text": "Blood pressure systolic & diastolic"
    },
    "subject": {
        "reference": "Patient/example"
    },
    "effectiveDateTime": "2023-01-15T12:30:00Z",
    "component": [
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }
                ],
                "text": "Systolic blood pressure"
            },
            "valueQuantity": {
                "value": 120,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            }
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }
                ],
                "text": "Diastolic blood pressure"
            },
            "valueQuantity": {
                "value": 80,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            }
        }
    ]
}


def compare_fhirpath_implementations():
    """Compare the functionality and performance of fhirpath vs fhirpathpy."""
    
    if not FHIRPATH_AVAILABLE:
        print("Cannot compare - fhirpath package not installed")
        return
    
    # Test cases for comparison
    test_expressions = [
        # Patient resource expressions
        {"resource": SAMPLE_PATIENT, "path": "Patient.name.where(use = 'official').family"},
        {"resource": SAMPLE_PATIENT, "path": "Patient.telecom.where(system = 'phone').value"},
        {"resource": SAMPLE_PATIENT, "path": "Patient.gender = 'male'"},
        
        # Observation resource expressions 
        {"resource": SAMPLE_OBSERVATION, "path": "Observation.component.code.coding.code"},
        {"resource": SAMPLE_OBSERVATION, "path": "Observation.component.valueQuantity.value"},
        {"resource": SAMPLE_OBSERVATION, "path": "Observation.effectiveDateTime"}
    ]
    
    print("Comparing fhirpathpy vs fhirpath implementations:\n")
    
    # Execute each test case with both implementations
    for i, test in enumerate(test_expressions):
        resource = test["resource"]
        path = test["path"]
        
        print(f"Test {i+1}: {path}")
        
        # Execute with fhirpathpy
        start_time = time.time()
        fhirpathpy_result = fhirpathpy.evaluate(resource, path)
        fhirpathpy_time = time.time() - start_time
        
        # Execute with fhirpath
        start_time = time.time()
        fhirpath_result = fhirpath.evaluate(resource, path)
        fhirpath_time = time.time() - start_time
        
        # Compare results
        print(f"  fhirpathpy result: {fhirpathpy_result}")
        print(f"  fhirpath result:   {fhirpath_result}")
        print(f"  fhirpathpy time:   {fhirpathpy_time:.6f} seconds")
        print(f"  fhirpath time:     {fhirpath_time:.6f} seconds")
        print(f"  Speed difference:  {fhirpathpy_time/fhirpath_time:.2f}x\n")

        # Check result equality
        is_equal = fhirpathpy_result == fhirpath_result
        print(f"  Results match: {is_equal}")
        if not is_equal:
            print(f"  Result difference: fhirpathpy={type(fhirpathpy_result)}, fhirpath={type(fhirpath_result)}")
        print("\n" + "-"*50 + "\n")


def test_fhirpath_compatibility():
    """Test if the new fhirpath implementation is compatible with our existing use patterns."""
    
    if not FHIRPATH_AVAILABLE:
        print("Cannot test compatibility - fhirpath package not installed")
        return
    
    print("Testing fhirpath compatibility with existing patterns:\n")
    
    # Test patient demographics extraction
    patient = SAMPLE_PATIENT
    
    print("Patient Demographics Extraction Test:")
    
    # FHIRPATH expressions for existing patterns
    expressions = {
        "id": "Patient.id",
        "active": "Patient.active",
        "gender": "Patient.gender",
        "birthDate": "Patient.birthDate",
        "familyName": "Patient.name.where(use = 'official').family | Patient.name.family",
        "givenNames": "Patient.name.where(use = 'official').given | Patient.name.given",
        "phone": "Patient.telecom.where(system = 'phone' and use = 'home').value | Patient.telecom.where(system = 'phone').value",
        "email": "Patient.telecom.where(system = 'email').value",
        "city": "Patient.address.where(use = 'home').city | Patient.address.city",
        "state": "Patient.address.where(use = 'home').state | Patient.address.state",
    }
    
    # Extract with fhirpathpy (current)
    print("Using fhirpathpy:")
    fhirpathpy_demographics = {}
    for key, path in expressions.items():
        result = fhirpathpy.evaluate(patient, path)
        fhirpathpy_demographics[key] = result[0] if result and len(result) > 0 else None
        print(f"  {key}: {fhirpathpy_demographics[key]}")
    
    # Extract with fhirpath (new)
    print("\nUsing fhirpath:")
    fhirpath_demographics = {}
    for key, path in expressions.items():
        result = fhirpath.evaluate(patient, path)
        fhirpath_demographics[key] = result[0] if result and len(result) > 0 else None
        print(f"  {key}: {fhirpath_demographics[key]}")
    
    # Compare results
    print("\nResults Comparison:")
    for key in expressions:
        match = fhirpathpy_demographics[key] == fhirpath_demographics[key]
        print(f"  {key}: {'✓' if match else '✗'}")


def main():
    """Main function to run the prototype."""
    print("FHIRPath Implementation Comparison Prototype\n")
    print("=" * 50)
    
    if not FHIRPATH_AVAILABLE:
        print("WARNING: fhirpath package not installed")
        print("Install with: pip install fhirpath")
        print("Continuing with fhirpathpy tests only...\n")
    
    # Compare implementations
    compare_fhirpath_implementations()
    
    # Test compatibility
    test_fhirpath_compatibility()


if __name__ == "__main__":
    main() 