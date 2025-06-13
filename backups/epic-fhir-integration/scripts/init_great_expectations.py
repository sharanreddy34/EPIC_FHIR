#!/usr/bin/env python
"""
Initialize Great Expectations and create expectation suites for FHIR resources.
This script sets up the Great Expectations framework for the epic-fhir-integration project.
"""

import os
import sys
import logging
import great_expectations as ge
from great_expectations.core import ExpectationSuite, ExpectationConfiguration
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gx_init")

# Resource types that need expectation suites
RESOURCE_TYPES = ["Patient", "Observation", "Condition", "Encounter"]

# Data tiers
DATA_TIERS = ["bronze", "silver", "gold"]

def init_great_expectations():
    """Initialize Great Expectations in the project directory."""
    # Determine the project root directory
    project_dir = Path(os.path.abspath(__file__)).parent.parent
    logger.info(f"Project directory: {project_dir}")
    
    # Create GX directory if it doesn't exist
    gx_dir = project_dir / "gx"
    if not gx_dir.exists():
        gx_dir.mkdir(parents=True)
        logger.info(f"Created GX directory: {gx_dir}")
    
    # Initialize Great Expectations
    context = ge.get_context()
    expectations_dir = gx_dir / "expectations"
    if not expectations_dir.exists():
        expectations_dir.mkdir(parents=True)
    
    # Create expectation suites for each resource type and data tier
    for resource_type in RESOURCE_TYPES:
        for tier in DATA_TIERS:
            suite_name = f"{resource_type.lower()}_{tier}_expectations"
            create_expectation_suite(context, suite_name, expectations_dir, resource_type, tier)
    
    logger.info("Great Expectations initialization complete")
    return True

def create_expectation_suite(context, suite_name, expectations_dir, resource_type, tier):
    """Create an expectation suite for a specific resource type and tier."""
    try:
        # Try to get the suite if it exists
        try:
            suite = context.get_expectation_suite(suite_name)
            logger.info(f"Expectation suite {suite_name} already exists")
        except Exception:
            # Create a new suite
            suite = ExpectationSuite(expectation_suite_name=suite_name)
            logger.info(f"Created new expectation suite: {suite_name}")
        
        # Add basic expectations based on the resource type
        add_common_expectations(suite, resource_type, tier)
        
        # Save the suite to disk
        suite_path = expectations_dir / f"{suite_name}.json"
        context.add_expectation_suite(suite)
        context.save_expectation_suite(suite, suite_name)
        logger.info(f"Saved expectation suite to {suite_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating expectation suite {suite_name}: {str(e)}")
        return False

def add_common_expectations(suite, resource_type, tier):
    """Add common expectations for a specific resource type and tier."""
    
    # Basic expectations for all resource types
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "resourceType"}
    ))
    
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "resourceType", "value_set": [resource_type]}
    ))
    
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "id"}
    ))
    
    # Resource-specific expectations
    if resource_type == "Patient":
        add_patient_expectations(suite, tier)
    elif resource_type == "Observation":
        add_observation_expectations(suite, tier)
    elif resource_type == "Condition":
        add_condition_expectations(suite, tier)
    elif resource_type == "Encounter":
        add_encounter_expectations(suite, tier)

def add_patient_expectations(suite, tier):
    """Add Patient-specific expectations."""
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "name"}
    ))
    
    if tier in ["silver", "gold"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_to_exist",
            kwargs={"column": "gender"}
        ))
        
    if tier == "gold":
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_in_set",
            kwargs={"column": "gender", "value_set": ["male", "female", "other", "unknown"]}
        ))

def add_observation_expectations(suite, tier):
    """Add Observation-specific expectations."""
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "status"}
    ))
    
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "code"}
    ))
    
    if tier in ["silver", "gold"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_to_exist",
            kwargs={"column": "subject"}
        ))

def add_condition_expectations(suite, tier):
    """Add Condition-specific expectations."""
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "code"}
    ))
    
    if tier in ["silver", "gold"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_to_exist",
            kwargs={"column": "subject"}
        ))

def add_encounter_expectations(suite, tier):
    """Add Encounter-specific expectations."""
    suite.add_expectation(ExpectationConfiguration(
        expectation_type="expect_column_to_exist",
        kwargs={"column": "status"}
    ))
    
    if tier in ["silver", "gold"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type="expect_column_to_exist",
            kwargs={"column": "subject"}
        ))

if __name__ == "__main__":
    success = init_great_expectations()
    sys.exit(0 if success else 1) 