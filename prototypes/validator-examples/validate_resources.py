#!/usr/bin/env python3
"""
Example script demonstrating use of HAPI FHIR Validator to validate FHIR resources
against custom profiles in an Epic integration context.

This script validates sample resources against the base FHIR specification
and optionally against custom profiles.
"""

import os
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


class FHIRValidator:
    """Wrapper for HAPI FHIR Validator CLI tool."""
    
    def __init__(self, validator_path: str, ig_path: Optional[str] = None):
        """
        Initialize the FHIR validator.
        
        Args:
            validator_path: Path to the validator_cli.jar file
            ig_path: Path to the implementation guide directory (with profiles)
        """
        self.validator_path = Path(validator_path)
        self.ig_path = Path(ig_path) if ig_path else None
        
        if not self.validator_path.exists():
            raise FileNotFoundError(f"Validator not found at {validator_path}")
        
        if self.ig_path and not self.ig_path.exists():
            print(f"Warning: Implementation guide path doesn't exist: {ig_path}")
    
    def validate(self, resource_path: str, fhir_version: str = "4.0.1") -> Dict:
        """
        Validate a FHIR resource against profiles.
        
        Args:
            resource_path: Path to the FHIR resource file
            fhir_version: FHIR version to validate against
            
        Returns:
            Dict containing validation results
        """
        cmd = [
            "java", "-jar", str(self.validator_path),
            resource_path,
            "-version", fhir_version,
            "-output", "json"
        ]
        
        if self.ig_path and self.ig_path.exists():
            cmd.extend(["-ig", str(self.ig_path)])
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse validator output",
                "output": result.stdout,
                "stderr": result.stderr
            }
    
    def validate_string(self, resource_json: str, fhir_version: str = "4.0.1") -> Dict:
        """
        Validate a FHIR resource string against profiles.
        
        Args:
            resource_json: JSON string of the FHIR resource
            fhir_version: FHIR version to validate against
            
        Returns:
            Dict containing validation results
        """
        # Write resource to temporary file
        temp_file = Path("temp_resource.json")
        with open(temp_file, "w") as f:
            f.write(resource_json)
        
        try:
            return self.validate(str(temp_file), fhir_version)
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()


def create_sample_patient() -> Dict:
    """Create a sample patient resource for testing."""
    return {
        "resourceType": "Patient",
        "id": "example",
        "meta": {
            "profile": ["http://example.org/fhir/StructureDefinition/epic-patient"]
        },
        "identifier": [
            {
                "system": "urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.0",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR"
                        }
                    ]
                },
                "value": "12345"
            }
        ],
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
        "extension": [
            {
                "url": "http://example.org/fhir/StructureDefinition/patient-consent",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "425691002",
                            "display": "Consent given for electronic record sharing"
                        }
                    ]
                }
            }
        ]
    }


def create_sample_blood_pressure() -> Dict:
    """Create a sample blood pressure observation for testing."""
    return {
        "resourceType": "Observation",
        "id": "blood-pressure-example",
        "meta": {
            "profile": ["http://example.org/fhir/StructureDefinition/epic-vital-signs-observation"]
        },
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


def main():
    """Run validation examples."""
    parser = argparse.ArgumentParser(description='Validate FHIR resources against profiles')
    parser.add_argument('--validator', required=True, help='Path to validator_cli.jar')
    parser.add_argument('--ig', help='Path to implementation guide directory containing profiles')
    parser.add_argument('--fhir-version', default='4.0.1', help='FHIR version (default: 4.0.1)')
    parser.add_argument('--output-dir', default='./validation-results', help='Directory for validation results')
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Create validator
    validator = FHIRValidator(
        validator_path=args.validator,
        ig_path=args.ig
    )
    
    print(f"FHIR Validator initialized with version {args.fhir_version}")
    
    # Create and validate sample resources
    samples = {
        "patient.json": create_sample_patient(),
        "blood-pressure.json": create_sample_blood_pressure()
    }
    
    for filename, resource in samples.items():
        # Save resource
        resource_path = output_dir / filename
        with open(resource_path, 'w') as f:
            json.dump(resource, f, indent=2)
        
        print(f"\nValidating {filename}...")
        # Validate against profiles
        result = validator.validate(str(resource_path), args.fhir_version)
        
        # Save validation result
        result_path = output_dir / f"{filename.rsplit('.', 1)[0]}-validation.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Print summary
        if result.get("success", False):
            print(f"✓ {filename} is valid")
        else:
            print(f"✗ {filename} has validation issues")
            
            if "issues" in result:
                for issue in result["issues"]:
                    severity = issue.get("severity", "unknown")
                    message = issue.get("message", "No message")
                    print(f"  {severity.upper()}: {message}")


if __name__ == "__main__":
    main() 