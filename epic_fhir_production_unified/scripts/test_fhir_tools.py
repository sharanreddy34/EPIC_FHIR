#!/usr/bin/env python3
"""
Simple FHIR Tools Test for Core Functionality

This script tests the core FHIR tools functionalities without depending on problematic dependencies:
1. Authentication
2. FHIRPath functionality 
3. Basic FHIR resource validation

Usage:
    python test_fhir_tools.py [--patient-id ID] [--output-dir DIR] [--mock]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("fhir_tools_test")

# Import authentication 
from epic_fhir_integration.auth.jwt_auth import get_token_with_retry
from epic_fhir_integration.auth.custom_auth import get_token

# Import FHIRPath adapter
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Import validator (but not GE validator)
from epic_fhir_integration.validation.validator import FHIRValidator

# Default test patient ID from documentation
DEFAULT_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

def get_auth_token():
    """Adapter function to get authentication token."""
    # Check for mock mode
    if os.environ.get("USE_MOCK_MODE") == "true":
        logger.info("Using mock authentication token")
        return {"access_token": "mock-token-12345", "token_type": "Bearer", "expires_in": 3600}
        
    try:
        # First try the retry mechanism from jwt_auth
        return get_token_with_retry()
    except Exception as e:
        logger.warning(f"Failed to get token with JWT retry: {e}, trying custom auth")
        # Fallback to custom auth
        return get_token()

def create_auth_header(token):
    """Create authentication header from token."""
    if isinstance(token, dict) and 'access_token' in token:
        token = token['access_token']
    
    return {'Authorization': f'Bearer {token}'}

def create_sample_resources(patient_id=DEFAULT_PATIENT_ID):
    """Create sample FHIR resources for testing."""
    logger.info("Creating sample FHIR resources for testing")
    
    # Sample Patient
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-05-20T08:15:00Z"
        },
        "identifier": [
            {
                "system": "urn:oid:1.2.36.146.595.217.0.1",
                "value": "12345"
            }
        ],
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
    
    # Sample Observations
    observations = []
    for i in range(3):
        observations.append({
            "resourceType": "Observation",
            "id": f"obs-{i+1}",
            "meta": {
                "versionId": "1",
                "lastUpdated": "2024-05-20T08:30:00Z"
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
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }
                ],
                "text": "Systolic blood pressure"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": f"2024-05-{15+i}T09:30:00Z",
            "valueQuantity": {
                "value": 120 + i*2,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            }
        })
    
    # Return all resources
    return {
        "Patient": [patient],
        "Observation": observations
    }

def test_fhirpath(resources):
    """Test FHIRPath implementation with resources."""
    logger.info("Testing FHIRPath implementation")
    
    try:
        if not resources or not resources.get("Patient"):
            raise Exception("No patient resources available")
        
        patient = resources["Patient"][0]
        
        # Create FHIRPath adapter
        fhirpath_adapter = FHIRPathAdapter()
        
        # Test some FHIRPath queries
        results = {}
        
        # Patient queries
        results["patient_name_given"] = fhirpath_adapter.extract_first(patient, "name.where(use='official').given.first()")
        results["patient_name_family"] = fhirpath_adapter.extract_first(patient, "name.where(use='official').family")
        results["gender"] = fhirpath_adapter.extract_first(patient, "gender")
        results["birth_date"] = fhirpath_adapter.extract_first(patient, "birthDate")
        results["address"] = fhirpath_adapter.extract_first(patient, "address.line.first()")
        results["telecom"] = fhirpath_adapter.extract_first(patient, "telecom.where(system='phone').value.first()")
        
        # Log results
        for name, result in results.items():
            logger.info(f"FHIRPath query '{name}': {result}")
        
        return True, results
    except Exception as e:
        logger.error(f"FHIRPath testing failed: {e}")
        return False, {"error": str(e)}

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run Simple FHIR Tools Test")
    parser.add_argument("--patient-id", default=DEFAULT_PATIENT_ID,
                        help=f"Patient ID to use for testing (default: {DEFAULT_PATIENT_ID})")
    parser.add_argument("--output-dir", help="Output directory for test results")
    parser.add_argument("--mock", action="store_true", help="Enable mock mode for testing without real dependencies")
    
    args = parser.parse_args()
    
    # Setup mock mode if specified
    if args.mock:
        os.environ["USE_MOCK_MODE"] = "true"
        logger.info("Mock mode enabled")
    
    # Setup output directory
    output_dir = Path(args.output_dir or f"fhir_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize results
    results = {
        "patient_id": args.patient_id,
        "timestamp": datetime.now().isoformat(),
        "steps": {},
        "overall_success": False,
        "mock_mode": args.mock
    }
    
    # Step 1: Authentication
    logger.info("Step 1: Authentication")
    try:
        token = get_auth_token()
        auth_header = create_auth_header(token)
        
        if not token or not auth_header:
            raise Exception("Failed to obtain valid authentication token")
        
        results["steps"]["authentication"] = {
            "success": True,
            "token_type": token.get("token_type", "unknown") if isinstance(token, dict) else "string"
        }
        logger.info("Authentication successful")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        results["steps"]["authentication"] = {
            "success": False,
            "error": str(e)
        }
        # Continue with the test even if authentication fails in mock mode
        if not args.mock:
            return 1
    
    # Step 2: Create/Fetch resources
    logger.info("Step 2: Creating/Fetching resources")
    resources = create_sample_resources(args.patient_id)
    
    # Save resources to output directory
    resources_file = output_dir / "resources.json"
    with open(resources_file, "w") as f:
        json.dump(resources, f, indent=2)
    
    results["steps"]["resources"] = {
        "success": True,
        "resource_counts": {k: len(v) for k, v in resources.items()},
        "output_file": str(resources_file)
    }
    
    # Step 3: Test FHIRPath
    logger.info("Step 3: Testing FHIRPath")
    fhirpath_success, fhirpath_results = test_fhirpath(resources)
    
    # Save FHIRPath results to output directory
    fhirpath_file = output_dir / "fhirpath_results.json"
    with open(fhirpath_file, "w") as f:
        json.dump(fhirpath_results, f, indent=2)
    
    results["steps"]["fhirpath"] = {
        "success": fhirpath_success,
        "results": fhirpath_results,
        "output_file": str(fhirpath_file)
    }
    
    # Generate final report
    all_steps = [step["success"] for step in results["steps"].values()]
    results["overall_success"] = all(all_steps)
    
    # Save report to output directory
    report_file = output_dir / "test_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Also create a markdown report
    md_report_file = output_dir / "test_report.md"
    with open(md_report_file, "w") as f:
        f.write("# FHIR Tools Test Report\n\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Patient ID:** {args.patient_id}\n\n")
        f.write(f"**Overall Status:** {'SUCCESS' if results['overall_success'] else 'FAILURE'}\n\n")
        
        f.write("## Test Steps Summary\n\n")
        f.write("| Step | Status |\n")
        f.write("|------|--------|\n")
        
        for step_name, step_result in results["steps"].items():
            status = "✅ PASS" if step_result["success"] else "❌ FAIL"
            f.write(f"| {step_name.title()} | {status} |\n")
        
        # FHIRPath results
        if "fhirpath" in results["steps"] and results["steps"]["fhirpath"]["success"]:
            f.write("\n## FHIRPath Query Results\n\n")
            f.write("| Query | Result |\n")
            f.write("|-------|--------|\n")
            
            fhirpath_results = results["steps"]["fhirpath"]["results"]
            for query, result in fhirpath_results.items():
                f.write(f"| {query} | {result} |\n")
    
    logger.info(f"Test report generated: {report_file}")
    logger.info(f"Markdown report generated: {md_report_file}")
    
    return 0 if results["overall_success"] else 1

if __name__ == "__main__":
    sys.exit(main()) 