#!/usr/bin/env python
"""
Create Great Expectations expectation suites for FHIR resources.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gx_create")

# Resource types that need expectation suites
RESOURCE_TYPES = ["Patient", "Observation", "Condition", "Encounter", "MedicationRequest"]

# Data tiers
DATA_TIERS = ["bronze", "silver", "gold"]

def find_project_root():
    """
    Find the project root directory by looking for indicators like epic-fhir-integration directory.
    Returns absolute path to the project root.
    """
    # Start with the script's directory
    current_dir = Path(os.path.abspath(__file__)).parent
    
    # First, try going up one level (script -> project_root)
    project_root = current_dir.parent
    if project_root.name == "epic-fhir-integration":
        logger.info(f"Found project root at: {project_root}")
        return project_root
    
    # Try going up another level (script -> epic-fhir-integration -> project_root)
    if current_dir.parent.name == "scripts" and current_dir.parent.parent.name == "epic-fhir-integration":
        project_root = current_dir.parent.parent
        logger.info(f"Found project root at: {project_root}")
        return project_root
    
    # Look for epic-fhir-integration directory up to 3 levels up
    for i in range(3):
        potential_root = current_dir
        for _ in range(i + 1):
            potential_root = potential_root.parent
            
        # Check if this directory or its child is the project root
        if potential_root.name == "epic-fhir-integration":
            logger.info(f"Found project root at: {potential_root}")
            return potential_root
        
        epic_fhir_dir = potential_root / "epic-fhir-integration"
        if epic_fhir_dir.exists() and epic_fhir_dir.is_dir():
            logger.info(f"Found project root at: {epic_fhir_dir}")
            return epic_fhir_dir
    
    # Fallback - use parent directory of script
    logger.warning("Could not determine project root with certainty. Using script parent directory.")
    return current_dir.parent

def initialize_great_expectations(project_dir):
    """
    Initialize Great Expectations if not already initialized.
    """
    gx_dir = project_dir / "great_expectations"
    
    if gx_dir.exists():
        logger.info(f"Great Expectations directory already exists at {gx_dir}")
        return gx_dir
    
    logger.info(f"Initializing Great Expectations in {project_dir}")
    try:
        # Check if great_expectations is installed
        result = subprocess.run(
            ["pip", "list"], 
            capture_output=True,
            text=True
        )
        
        if "great-expectations" not in result.stdout:
            logger.error("Great Expectations not installed. Please install using: pip install great_expectations")
            return None
            
        # Change to project directory
        original_dir = os.getcwd()
        os.chdir(project_dir)
        
        try:
            # Run great_expectations init
            init_result = subprocess.run(
                ["great_expectations", "init"],
                capture_output=True,
                text=True
            )
            
            if init_result.returncode != 0:
                logger.error(f"Failed to initialize Great Expectations: {init_result.stderr}")
                return None
                
            logger.info("Great Expectations initialized successfully")
            
            # Create expectations directory if it doesn't exist
            expectations_dir = gx_dir / "expectations"
            expectations_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created expectations directory: {expectations_dir}")
            
            return gx_dir
        finally:
            # Return to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error initializing Great Expectations: {e}")
        return None

def create_expectation_suites(project_dir=None, overwrite=False):
    """
    Create expectation suites for each resource type and tier.
    
    Args:
        project_dir: Optional path to the project directory
        overwrite: Whether to overwrite existing expectation suites
        
    Returns:
        True if the expectations were created, False otherwise
    """
    # Determine the project root directory
    if project_dir:
        project_dir = Path(project_dir)
    else:
        project_dir = find_project_root()
    
    logger.info(f"Using project directory: {project_dir}")
    
    # Initialize or locate Great Expectations directory
    gx_dir = initialize_great_expectations(project_dir)
    if not gx_dir:
        logger.error("Failed to initialize or locate Great Expectations directory")
        return False
    
    expectations_dir = gx_dir / "expectations"
    if not expectations_dir.exists():
        expectations_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created expectations directory: {expectations_dir}")
    
    # Count how many suites we create or update
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    # Create expectation suites for each resource type and tier
    for resource_type in RESOURCE_TYPES:
        for tier in DATA_TIERS:
            suite_name = f"{resource_type.lower()}_{tier}_expectations"
            suite_path = expectations_dir / f"{suite_name}.json"
            
            if suite_path.exists() and not overwrite:
                logger.info(f"Expectation suite already exists: {suite_path}. Use --overwrite to update.")
                skipped_count += 1
                continue
                
            if create_expectation_suite(expectations_dir, suite_name, resource_type, tier):
                if suite_path.exists() and overwrite:
                    logger.info(f"Updated expectation suite: {suite_path}")
                    updated_count += 1
                else:
                    logger.info(f"Created expectation suite: {suite_path}")
                    created_count += 1
    
    logger.info(f"Expectation suite creation complete: {created_count} created, {updated_count} updated, {skipped_count} skipped")
    return True

def create_expectation_suite(expectations_dir, suite_name, resource_type, tier):
    """Create an expectation suite JSON file."""
    try:
        # Create the basic suite structure
        suite = {
            "expectation_suite_name": suite_name,
            "expectations": [],
            "meta": {
                "resource_type": resource_type,
                "tier": tier,
                "notes": {
                    "content": f"Expectations for {resource_type} in {tier} tier",
                    "format": "markdown"
                }
            }
        }
        
        # Add basic expectations for all resource types
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "resourceType"}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "resourceType", "value_set": [resource_type]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "id"}
        })
        
        # Add resource-specific expectations
        if resource_type == "Patient":
            add_patient_expectations(suite, tier)
        elif resource_type == "Observation":
            add_observation_expectations(suite, tier)
        elif resource_type == "Condition":
            add_condition_expectations(suite, tier)
        elif resource_type == "Encounter":
            add_encounter_expectations(suite, tier)
        elif resource_type == "MedicationRequest":
            add_medication_request_expectations(suite, tier)
        
        # Save the suite to a JSON file
        suite_path = expectations_dir / f"{suite_name}.json"
        with open(suite_path, 'w') as f:
            json.dump(suite, f, indent=2)
        
        logger.info(f"Created expectation suite: {suite_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating expectation suite {suite_name}: {str(e)}")
        return False

def add_patient_expectations(suite, tier):
    """Add Patient-specific expectations."""
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "name"}
    })
    
    if tier in ["silver", "gold"]:
        # Additional expectations for higher tiers
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "gender"}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "birthDate"}
        })
        
    if tier == "gold":
        # Gold tier has the strictest expectations
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "gender", "value_set": ["male", "female", "other", "unknown"]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "text.div"}
        })

def add_observation_expectations(suite, tier):
    """Add Observation-specific expectations."""
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "status"}
    })
    
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "code"}
    })
    
    if tier in ["silver", "gold"]:
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "subject"}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "category"}
        })
        
    if tier == "gold":
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "status", "value_set": [
                "registered", "preliminary", "final", "amended", "corrected", 
                "cancelled", "entered-in-error", "unknown"
            ]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "text.div"}
        })

def add_condition_expectations(suite, tier):
    """Add Condition-specific expectations."""
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "code"}
    })
    
    if tier in ["silver", "gold"]:
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "subject"}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "clinicalStatus"}
        })
        
    if tier == "gold":
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "text.div"}
        })

def add_encounter_expectations(suite, tier):
    """Add Encounter-specific expectations."""
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "status"}
    })
    
    if tier in ["silver", "gold"]:
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "subject"}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "class"}
        })
        
    if tier == "gold":
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "status", "value_set": [
                "planned", "arrived", "triaged", "in-progress", "onleave",
                "finished", "cancelled", "entered-in-error", "unknown"
            ]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "text.div"}
        })

def add_medication_request_expectations(suite, tier):
    """Add MedicationRequest-specific expectations."""
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "status"}
    })
    
    suite["expectations"].append({
        "expectation_type": "expect_column_to_exist",
        "kwargs": {"column": "intent"}
    })
    
    if tier in ["silver", "gold"]:
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "subject"}
        })
        
        # In silver and gold, require either medicationCodeableConcept or medicationReference
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "medication"}
        })
        
    if tier == "gold":
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "status", "value_set": [
                "active", "on-hold", "cancelled", "completed", "entered-in-error", 
                "stopped", "draft", "unknown"
            ]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_values_to_be_in_set",
            "kwargs": {"column": "intent", "value_set": [
                "proposal", "plan", "order", "original-order", "reflex-order",
                "filler-order", "instance-order", "option"
            ]}
        })
        
        suite["expectations"].append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": "text.div"}
        })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Great Expectations expectation suites for FHIR resources")
    parser.add_argument("--project-dir", help="Path to the project directory")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing expectation suites")
    
    args = parser.parse_args()
    
    success = create_expectation_suites(args.project_dir, args.overwrite)
    sys.exit(0 if success else 1) 