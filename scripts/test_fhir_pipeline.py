#!/usr/bin/env python3
"""
FHIR Pipeline Test Script

This script tests the FHIR pipeline with a specific patient ID.
It runs various components of the pipeline and checks their output.

Usage:
    python test_fhir_pipeline.py [--debug] [--strict]

Example:
    python test_fhir_pipeline.py --strict
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add script directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from scripts.run_local_fhir_pipeline (which should be copied to the scripts directory)
from scripts.run_local_fhir_pipeline import (
    create_dataset_structure,
    run_extract_resources,
    run_transform_resources,
    get_spark_session,
    setup_debug_logging,
    load_config_files,
    summarize_results
)

# Import strict mode utilities
from fhir_pipeline.utils.strict_mode import enable_strict_mode, get_strict_mode, strict_mode_check, no_mocks

# Test patient ID
TEST_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

# Resource types to test
TEST_RESOURCE_TYPES = ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest"]

@no_mocks("create_mock_resources")
def create_mock_resources(output_dir: Path, patient_id: str, mock_mode: bool = False) -> bool:
    """
    Create mock FHIR resources directly in the bronze layer to bypass API calls.
    
    In strict mode, this function will raise an error due to the @no_mocks decorator.
    
    Args:
        output_dir: Base output directory
        patient_id: Patient ID to use in resources
        mock_mode: Whether mock mode is enabled
        
    Returns:
        Success status
    """
    # This will fail in strict mode
    logger.info("Creating mock FHIR resources directly")
    bronze_dir = output_dir / "bronze" / "fhir_raw"
    
    try:
        # Create mock data for each resource type
        for resource_type in TEST_RESOURCE_TYPES:
            resource_dir = bronze_dir / resource_type
            resource_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created resource directory: {resource_dir}")
            
            # Create mock bundle
            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 5,
                "entry": []
            }
            
            # Add mock entries
            for i in range(5):
                entry = {
                    "resource": {
                        "resourceType": resource_type,
                        "id": f"mock-{resource_type.lower()}-{i}",
                        "meta": {
                            "lastUpdated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                        }
                    }
                }
                
                # Add patient reference for non-patient resources
                if resource_type != "Patient":
                    entry["resource"]["subject"] = {"reference": f"Patient/{patient_id}"}
                else:
                    entry["resource"]["id"] = patient_id
                
                # Add resource-specific fields
                if resource_type == "Patient":
                    entry["resource"]["name"] = [{"family": "Test", "given": ["Patient"]}]
                    entry["resource"]["gender"] = "unknown"
                    entry["resource"]["birthDate"] = "1970-01-01"
                elif resource_type == "Observation":
                    entry["resource"]["status"] = "final"
                    # Add proper code with coding array
                    entry["resource"]["code"] = {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": f"test-code-{i}",
                                "display": f"Test Observation {i}"
                            }
                        ],
                        "text": f"Test Observation {i}"
                    }
                    # Add required category element
                    entry["resource"]["category"] = [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "laboratory",
                                    "display": "Laboratory"
                                }
                            ]
                        }
                    ]
                    entry["resource"]["valueQuantity"] = {"value": 100 + i, "unit": "mg/dL"}
                elif resource_type == "Condition":
                    entry["resource"]["clinicalStatus"] = {"text": "active"}
                    entry["resource"]["code"] = {"text": f"Test Condition {i}"}
                
                bundle["entry"].append(entry)
            
            # Save bundle with metadata
            bundle_with_metadata = {
                "metadata": {
                    "patient_id": patient_id,
                    "resource_type": resource_type,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                },
                "bundle": bundle
            }
            
            # Write to file
            timestamp = time.strftime("%Y%m%d%H%M%S")
            filename = resource_dir / f"{timestamp}_bundle.json"
            with open(filename, 'w') as f:
                json.dump(bundle_with_metadata, f, indent=2)
            
            logger.info(f"Created mock data file: {filename}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating mock resources: {str(e)}")
        return False

def list_directory_contents(directory: Path, max_depth: int = 3, current_depth: int = 0) -> List[str]:
    """
    List contents of a directory recursively up to a maximum depth.
    
    Args:
        directory: Directory to list
        max_depth: Maximum recursion depth
        current_depth: Current depth (for internal use)
        
    Returns:
        List of paths found
    """
    result = []
    try:
        for item in directory.iterdir():
            result.append(f"{'  ' * current_depth}{'[dir]' if item.is_dir() else '[file]'} {item.name}")
            if item.is_dir() and current_depth < max_depth:
                result.extend(list_directory_contents(item, max_depth, current_depth + 1))
    except Exception as e:
        result.append(f"{'  ' * current_depth}Error: {str(e)}")
    
    return result

def test_pipeline(debug: bool = True, strict_mode: bool = False) -> bool:
    """
    Test the FHIR pipeline with the test patient ID.
    
    Args:
        debug: Whether to enable debug logging
        strict_mode: Whether to run in strict mode with no mock data
    
    Returns:
        Success status
    """
    # Setup debug logging
    setup_debug_logging(debug)
    logger.info(f"Starting pipeline test with patient ID: {TEST_PATIENT_ID}")
    
    # Enable strict mode if requested
    if strict_mode:
        enable_strict_mode()
        logger.info("STRICT MODE ENABLED - No mock data will be used")
    
    # Configure output directory
    output_dir = Path("./test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using output directory: {output_dir}")
    
    # Create datasets structure
    base_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    logger.info(f"Base directory: {base_dir}")
    datasets = create_dataset_structure(output_dir)
    logger.info(f"Created {len(datasets)} dataset structures")
    
    # Copy config files
    config = load_config_files(base_dir)
    if not config:
        logger.error("Failed to load configuration files")
        return False
    logger.info("Configuration files loaded successfully")
    
    # If in strict mode, run real extraction instead of creating mock resources
    if get_strict_mode():
        logger.info("Strict mode is enabled - running real extraction")
        extraction_success = run_extract_resources(
            base_dir, datasets, TEST_PATIENT_ID, resource_type=None, mock_mode=False
        )
        if not extraction_success:
            logger.error("Real extraction failed in strict mode")
            return False
    else:
        # Create mock FHIR resources directly
        logger.info("Creating mock FHIR resources directly (strict mode disabled)")
        if not create_mock_resources(output_dir, TEST_PATIENT_ID):
            logger.error("Failed to create mock resources")
            return False
    
    # List bronze directory contents
    bronze_dir = output_dir / "bronze" / "fhir_raw"
    logger.info("Bronze directory contents:")
    for line in list_directory_contents(bronze_dir):
        logger.info(line)
    
    # Run transformation
    logger.info("Running transformation")
    transform_success = run_transform_resources(
        base_dir, datasets, resource_type=None, mock_mode=not get_strict_mode()
    )
    
    if not transform_success:
        logger.error("Transformation failed")
        return False
    logger.info("Transformation completed successfully")
    
    # List silver directory contents
    silver_dir = output_dir / "silver" / "fhir_normalized"
    logger.info("Silver directory contents:")
    for line in list_directory_contents(silver_dir):
        logger.info(line)
    
    # Summarize results
    logger.info("Summarizing results")
    summarize_results(output_dir, TEST_PATIENT_ID, mock_mode=not get_strict_mode())
    
    logger.info("Pipeline test completed successfully")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test FHIR pipeline with specific patient ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (no mock data)")
    args = parser.parse_args()
    
    success = test_pipeline(debug=args.debug, strict_mode=args.strict)
    sys.exit(0 if success else 1) 