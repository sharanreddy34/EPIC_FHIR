#!/usr/bin/env python3
"""
Direct FHIR Functionality Test

This script directly tests the FHIRPath adapter without importing through the package's __init__.py
to avoid dependencies on Great Expectations.
"""

import json
import sys
from pathlib import Path

# Import directly from the module
sys.path.append(str(Path(__file__).parent.parent))
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Sample patient data
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "test-patient",
    "name": [
        {
            "use": "official",
            "family": "Smith",
            "given": ["John", "Samuel"]
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
    ],
    "gender": "male",
    "birthDate": "1970-01-25",
    "address": [
        {
            "use": "home",
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345"
        }
    ],
    "active": True
}

def main():
    """Test FHIRPath functionality directly."""
    print("Testing FHIRPath adapter...")
    
    try:
        # Create FHIRPath adapter
        adapter = FHIRPathAdapter()
        print("✅ FHIRPathAdapter instantiated successfully")
        
        # Test FHIRPath queries
        queries = {
            "name.where(use='official').given.first()": "First name",
            "name.where(use='official').family": "Family name",
            "gender": "Gender",
            "birthDate": "Birth date",
            "address.line.first()": "Address line",
            "telecom.where(system='phone').value.first()": "Phone number"
        }
        
        results = {}
        for path, description in queries.items():
            result = adapter.extract_first(SAMPLE_PATIENT, path)
            results[description] = result
            print(f"✅ {description}: {result}")
        
        # Save results
        output_dir = Path("fhir_test_output")
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "fhirpath_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to {output_dir / 'fhirpath_results.json'}")
        print("\nFHIRPath testing completed successfully!")
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 