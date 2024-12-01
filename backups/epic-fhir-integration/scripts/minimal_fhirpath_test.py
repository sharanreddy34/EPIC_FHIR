#!/usr/bin/env python3
"""
Minimal FHIRPath test script to verify test data.
This doesn't require any dependencies from the epic_fhir_integration package.
"""

import os
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("minimal_fhirpath_test")

def main():
    """Simple test to verify the structure of test data."""
    # Get test data path from environment or use default
    test_data_path = os.environ.get("EPIC_TEST_DATA_PATH", "test_data")
    
    logger.info(f"Looking for test data in: {test_data_path}")
    
    # Check if patient bundle exists
    patient_bundle_path = os.path.join(test_data_path, "Patient", "bundle.json")
    if not os.path.exists(patient_bundle_path):
        logger.error(f"Patient bundle not found at: {patient_bundle_path}")
        return 1
    
    logger.info(f"Found patient bundle at: {patient_bundle_path}")
    
    # Load patient bundle
    try:
        with open(patient_bundle_path, 'r') as f:
            bundle = json.load(f)
        
        # Verify bundle structure
        if bundle.get("resourceType") != "Bundle":
            logger.error("Invalid bundle: resourceType is not 'Bundle'")
            return 1
        
        entries = bundle.get("entry", [])
        logger.info(f"Bundle contains {len(entries)} entries")
        
        # Process each patient
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            
            # Simple path extraction
            patient_id = resource.get("id", "unknown")
            gender = resource.get("gender", "unknown")
            
            # Extract name (slightly more complex path)
            names = resource.get("name", [])
            family_name = names[0].get("family") if names else "unknown"
            given_names = names[0].get("given", []) if names else []
            
            logger.info(f"Patient {i+1}:")
            logger.info(f"  ID: {patient_id}")
            logger.info(f"  Gender: {gender}")
            logger.info(f"  Family name: {family_name}")
            logger.info(f"  Given names: {', '.join(given_names)}")
            
            # Manual FHIRPath-like extraction
            logger.info("Basic FHIRPath-like extractions:")
            logger.info(f"  resource.id: {resource.get('id')}")
            logger.info(f"  resource.name[0].family: {names[0].get('family') if names else None}")
        
        logger.info("Test completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error processing bundle: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 