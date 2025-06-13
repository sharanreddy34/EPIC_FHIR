#!/usr/bin/env python3
"""
Test script for FHIR API integration.

This script tests the FHIR integration functionality with real API calls,
including data extraction, validation, and transformation.
"""

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add the parent directory to the path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from epic_fhir_integration.auth.jwt_auth import get_token_with_retry
from epic_fhir_integration.config.loader import get_config, load_config_file
from epic_fhir_integration.io.epic_fhir_client import EpicFHIRClient, create_epic_fhir_client
from epic_fhir_integration.utils.fhir_validator import FHIRValidator
from epic_fhir_integration.utils.terminology_validator import TerminologyValidator
from epic_fhir_integration.utils.auto_correction import correct_resource
from epic_fhir_integration.utils.fhirpath_extractor import extract_patient_demographics, extract_observation_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_OUTPUT_DIR = Path("test_output")


def setup_output_dir(output_dir: Path) -> Path:
    """
    Set up the output directory.
    
    Args:
        output_dir: Directory to save output files
        
    Returns:
        Path to the output directory
    """
    # Create the output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for different output types
    (output_dir / "raw").mkdir(exist_ok=True)
    (output_dir / "validated").mkdir(exist_ok=True)
    (output_dir / "transformed").mkdir(exist_ok=True)
    
    return output_dir


def test_fhir_client(client: EpicFHIRClient, output_dir: Path) -> Dict[str, Path]:
    """
    Test the FHIR client functionality.
    
    Args:
        client: FHIR client to test
        output_dir: Directory to save output files
        
    Returns:
        Dictionary mapping resource types to output file paths
    """
    logger.info("Testing FHIR client functionality...")
    
    # Test patient search
    logger.info("Searching for patients...")
    patients_file = output_dir / "raw" / "patients.json"
    
    patients = list(client.search_resources(
        resource_type="Patient",
        params={"_count": "10"},
        page_limit=1
    ))
    
    logger.info(f"Found {len(patients)} patients")
    
    # Save the patients to a file
    with open(patients_file, "w") as f:
        json.dump(patients, f, indent=2)
    
    # Test other resource types if we have at least one patient
    output_files = {"Patient": patients_file}
    
    if patients:
        patient_id = patients[0].get("id")
        logger.info(f"Using patient ID: {patient_id}")
        
        # Test retrieving observations for a patient
        logger.info(f"Retrieving observations for patient {patient_id}...")
        observations = list(client.search_resources(
            resource_type="Observation",
            params={"patient": patient_id, "_count": "10"},
            page_limit=1
        ))
        
        if observations:
            observations_file = output_dir / "raw" / "observations.json"
            with open(observations_file, "w") as f:
                json.dump(observations, f, indent=2)
            
            output_files["Observation"] = observations_file
            logger.info(f"Found {len(observations)} observations")
        else:
            logger.warning("No observations found for the patient")
        
        # Test retrieving encounters for a patient
        logger.info(f"Retrieving encounters for patient {patient_id}...")
        encounters = list(client.search_resources(
            resource_type="Encounter",
            params={"patient": patient_id, "_count": "10"},
            page_limit=1
        ))
        
        if encounters:
            encounters_file = output_dir / "raw" / "encounters.json"
            with open(encounters_file, "w") as f:
                json.dump(encounters, f, indent=2)
            
            output_files["Encounter"] = encounters_file
            logger.info(f"Found {len(encounters)} encounters")
        else:
            logger.warning("No encounters found for the patient")
        
        # Test $everything operation if the client supports it
        try:
            logger.info(f"Testing $everything operation for patient {patient_id}...")
            everything = client.get_patient_everything(patient_id)
            
            if everything.get("entry"):
                everything_file = output_dir / "raw" / "patient_everything.json"
                with open(everything_file, "w") as f:
                    json.dump(everything, f, indent=2)
                
                output_files["PatientEverything"] = everything_file
                logger.info(f"Retrieved {len(everything.get('entry', []))} resources with $everything")
            else:
                logger.warning("No resources found with $everything operation")
        except Exception as e:
            logger.error(f"Error using $everything operation: {e}")
    
    return output_files


def test_validation(validator: FHIRValidator, resources_files: Dict[str, Path], output_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Test validation of FHIR resources.
    
    Args:
        validator: FHIR validator to use
        resources_files: Dictionary mapping resource types to file paths
        output_dir: Directory to save validation results
        
    Returns:
        Dictionary mapping resource types to validation results
    """
    logger.info("Testing FHIR validation...")
    
    validation_results = {}
    
    for resource_type, file_path in resources_files.items():
        logger.info(f"Validating {resource_type} resources...")
        
        # Load resources from file
        with open(file_path, "r") as f:
            resources = json.load(f)
        
        # Validate each resource
        resource_results = []
        valid_count = 0
        if isinstance(resources, list):
            for i, resource in enumerate(resources):
                logger.info(f"Validating {resource_type} {i+1}/{len(resources)}...")
                
                # Apply automatic corrections if possible
                corrected_resource, corrections = correct_resource(resource)
                
                if corrections:
                    logger.info(f"Applied {len(corrections)} corrections to {resource_type} {i+1}")
                    for correction in corrections:
                        logger.info(f"  - {correction}")
                
                # Validate the corrected resource
                validation_result = validator.validate_resource(corrected_resource)
                resource_results.append({
                    "resource_id": resource.get("id", f"unknown-{i}"),
                    "valid": validation_result.valid,
                    "issues": validation_result.issues,
                    "corrections": corrections
                })
                
                if validation_result.valid:
                    valid_count += 1
        elif "entry" in resources:  # Handle bundles from $everything
            entries = resources.get("entry", [])
            for i, entry in enumerate(entries):
                resource = entry.get("resource", {})
                resource_type = resource.get("resourceType", "Unknown")
                
                logger.info(f"Validating {resource_type} {i+1}/{len(entries)}...")
                
                # Apply automatic corrections if possible
                corrected_resource, corrections = correct_resource(resource)
                
                if corrections:
                    logger.info(f"Applied {len(corrections)} corrections to {resource_type} {i+1}")
                    for correction in corrections:
                        logger.info(f"  - {correction}")
                
                # Validate the corrected resource
                validation_result = validator.validate_resource(corrected_resource)
                resource_results.append({
                    "resource_id": resource.get("id", f"unknown-{i}"),
                    "resource_type": resource_type,
                    "valid": validation_result.valid,
                    "issues": validation_result.issues,
                    "corrections": corrections
                })
                
                if validation_result.valid:
                    valid_count += 1
        
        # Calculate summary statistics
        total_resources = len(resource_results)
        if total_resources > 0:
            valid_percentage = (valid_count / total_resources) * 100
            logger.info(f"Validation results for {resource_type}: {valid_count}/{total_resources} ({valid_percentage:.1f}%) valid")
            
            # Save validation results
            results_file = output_dir / "validated" / f"{resource_type.lower()}_validation.json"
            with open(results_file, "w") as f:
                json.dump({
                    "resource_type": resource_type,
                    "total_resources": total_resources,
                    "valid_resources": valid_count,
                    "valid_percentage": valid_percentage,
                    "results": resource_results
                }, f, indent=2)
            
            validation_results[resource_type] = {
                "total": total_resources,
                "valid": valid_count,
                "percentage": valid_percentage,
                "file": str(results_file)
            }
    
    return validation_results


def test_terminology_validation(terminology_validator: TerminologyValidator, resources_files: Dict[str, Path], output_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Test validation of coded values in FHIR resources.
    
    Args:
        terminology_validator: Terminology validator to use
        resources_files: Dictionary mapping resource types to file paths
        output_dir: Directory to save validation results
        
    Returns:
        Dictionary mapping resource types to validation results
    """
    logger.info("Testing terminology validation...")
    
    validation_results = {}
    
    for resource_type, file_path in resources_files.items():
        if resource_type == "PatientEverything":
            continue  # Skip the $everything bundle to avoid duplicating validations
            
        logger.info(f"Validating terminology in {resource_type} resources...")
        
        # Load resources from file
        with open(file_path, "r") as f:
            resources = json.load(f)
        
        # Validate terminology in each resource
        resource_results = []
        valid_count = 0
        total_codings = 0
        
        if isinstance(resources, list):
            for i, resource in enumerate(resources):
                logger.info(f"Validating terminology in {resource_type} {i+1}/{len(resources)}...")
                
                # Validate all codings in the resource
                coding_results = terminology_validator.validate_resource_codings(resource)
                
                # Count valid codings
                valid_codings = 0
                coding_count = 0
                
                for path, results_list in coding_results.items():
                    for result in results_list:
                        coding_count += 1
                        if result.get("valid"):
                            valid_codings += 1
                
                resource_results.append({
                    "resource_id": resource.get("id", f"unknown-{i}"),
                    "codings_count": coding_count,
                    "valid_codings": valid_codings,
                    "results": coding_results
                })
                
                total_codings += coding_count
                valid_count += valid_codings
        
        # Calculate summary statistics
        if total_codings > 0:
            valid_percentage = (valid_count / total_codings) * 100
            logger.info(f"Terminology validation results for {resource_type}: {valid_count}/{total_codings} ({valid_percentage:.1f}%) valid")
            
            # Save validation results
            results_file = output_dir / "validated" / f"{resource_type.lower()}_terminology.json"
            with open(results_file, "w") as f:
                json.dump({
                    "resource_type": resource_type,
                    "total_codings": total_codings,
                    "valid_codings": valid_count,
                    "valid_percentage": valid_percentage,
                    "results": resource_results
                }, f, indent=2)
            
            validation_results[resource_type] = {
                "total": total_codings,
                "valid": valid_count,
                "percentage": valid_percentage,
                "file": str(results_file)
            }
    
    return validation_results


def test_fhirpath_extraction(resources_files: Dict[str, Path], output_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Test FHIRPath extraction from FHIR resources.
    
    Args:
        resources_files: Dictionary mapping resource types to file paths
        output_dir: Directory to save extraction results
        
    Returns:
        Dictionary mapping resource types to extraction results
    """
    logger.info("Testing FHIRPath extraction...")
    
    extraction_results = {}
    
    # Test patient demographics extraction
    if "Patient" in resources_files:
        logger.info("Extracting patient demographics...")
        
        # Load patients from file
        with open(resources_files["Patient"], "r") as f:
            patients = json.load(f)
        
        # Extract demographics from each patient
        patient_results = []
        
        for i, patient in enumerate(patients):
            logger.info(f"Extracting demographics from patient {i+1}/{len(patients)}...")
            
            # Extract demographics
            demographics = extract_patient_demographics(patient)
            
            patient_results.append({
                "patient_id": patient.get("id", f"unknown-{i}"),
                "demographics": demographics
            })
        
        # Save extraction results
        results_file = output_dir / "transformed" / "patient_demographics.json"
        with open(results_file, "w") as f:
            json.dump(patient_results, f, indent=2)
        
        extraction_results["Patient"] = {
            "count": len(patient_results),
            "file": str(results_file)
        }
        
        logger.info(f"Extracted demographics for {len(patient_results)} patients")
    
    # Test observation values extraction
    if "Observation" in resources_files:
        logger.info("Extracting observation values...")
        
        # Load observations from file
        with open(resources_files["Observation"], "r") as f:
            observations = json.load(f)
        
        # Extract values from each observation
        observation_results = []
        
        for i, observation in enumerate(observations):
            logger.info(f"Extracting values from observation {i+1}/{len(observations)}...")
            
            # Extract values
            values = extract_observation_values(observation)
            
            observation_results.append({
                "observation_id": observation.get("id", f"unknown-{i}"),
                "values": values
            })
        
        # Save extraction results
        results_file = output_dir / "transformed" / "observation_values.json"
        with open(results_file, "w") as f:
            json.dump(observation_results, f, indent=2)
        
        extraction_results["Observation"] = {
            "count": len(observation_results),
            "file": str(results_file)
        }
        
        logger.info(f"Extracted values from {len(observation_results)} observations")
    
    return extraction_results


def main():
    parser = argparse.ArgumentParser(description="Test FHIR API integration")
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default="config/config.json"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save output files",
        default=str(DEFAULT_OUTPUT_DIR)
    )
    parser.add_argument(
        "--skip-validation",
        help="Skip FHIR validation",
        action="store_true"
    )
    parser.add_argument(
        "--skip-terminology",
        help="Skip terminology validation",
        action="store_true"
    )
    parser.add_argument(
        "--resources-dir",
        help="Directory containing resource files (skips API calls if provided)",
    )
    
    args = parser.parse_args()
    
    # Set up output directory
    output_dir = Path(args.output_dir)
    output_dir = setup_output_dir(output_dir)
    
    # Load configuration
    if args.config:
        try:
            load_config_file(args.config)
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            sys.exit(1)
    
    # Get resources from files or API
    resources_files = {}
    
    if args.resources_dir:
        # Get resources from files
        resources_dir = Path(args.resources_dir)
        if not resources_dir.exists():
            logger.error(f"Resources directory not found: {resources_dir}")
            sys.exit(1)
        
        logger.info(f"Using resources from {resources_dir}")
        
        # Look for resource files
        for file_path in resources_dir.glob("*.json"):
            file_name = file_path.stem
            if file_name.lower() in ["patients", "patient"]:
                resources_files["Patient"] = file_path
            elif file_name.lower() in ["observations", "observation"]:
                resources_files["Observation"] = file_path
            elif file_name.lower() in ["encounters", "encounter"]:
                resources_files["Encounter"] = file_path
            elif file_name.lower() in ["conditions", "condition"]:
                resources_files["Condition"] = file_path
            elif file_name.lower() in ["patient_everything", "everything"]:
                resources_files["PatientEverything"] = file_path
        
        if not resources_files:
            logger.error(f"No resource files found in {resources_dir}")
            sys.exit(1)
        
        for resource_type, file_path in resources_files.items():
            logger.info(f"Found {resource_type} resources in {file_path}")
    else:
        # Get resources from API
        try:
            # Create FHIR client
            logger.info("Creating FHIR client...")
            client = create_epic_fhir_client()
            
            # Test FHIR client
            resources_files = test_fhir_client(client, output_dir)
            
            if not resources_files:
                logger.error("No resources found")
                sys.exit(1)
            
        except Exception as e:
            logger.error(f"Error testing FHIR client: {e}")
            sys.exit(1)
    
    # Test validation if not skipped
    if not args.skip_validation:
        try:
            # Create FHIR validator
            logger.info("Creating FHIR validator...")
            validator = FHIRValidator()
            
            # Test validation
            validation_results = test_validation(validator, resources_files, output_dir)
            
            # Print validation summary
            logger.info("Validation summary:")
            for resource_type, results in validation_results.items():
                logger.info(f"  {resource_type}: {results['valid']}/{results['total']} ({results['percentage']:.1f}%) valid")
        
        except Exception as e:
            logger.error(f"Error testing validation: {e}")
    
    # Test terminology validation if not skipped
    if not args.skip_terminology:
        try:
            # Create terminology validator
            logger.info("Creating terminology validator...")
            terminology_validator = TerminologyValidator()
            
            # Test terminology validation
            terminology_results = test_terminology_validation(terminology_validator, resources_files, output_dir)
            
            # Print terminology validation summary
            logger.info("Terminology validation summary:")
            for resource_type, results in terminology_results.items():
                logger.info(f"  {resource_type}: {results['valid']}/{results['total']} ({results['percentage']:.1f}%) valid")
        
        except Exception as e:
            logger.error(f"Error testing terminology validation: {e}")
    
    # Test FHIRPath extraction
    try:
        # Test extraction
        extraction_results = test_fhirpath_extraction(resources_files, output_dir)
        
        # Print extraction summary
        logger.info("Extraction summary:")
        for resource_type, results in extraction_results.items():
            logger.info(f"  {resource_type}: {results['count']} resources processed")
    
    except Exception as e:
        logger.error(f"Error testing extraction: {e}")
    
    logger.info(f"All tests completed. Results saved to {output_dir}")


if __name__ == "__main__":
    main() 