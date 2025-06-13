#!/usr/bin/env python
"""
Test script for Great Expectations validator with enhanced logging.

This script demonstrates the enhanced logging functionality added to the
Great Expectations validator. It creates sample FHIR resources and validates
them against expectation suites to show the logging output.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from epic_fhir_integration.metrics.great_expectations_validator import (
    GreatExpectationsValidator,
    create_patient_expectations,
    create_observation_expectations
)
from epic_fhir_integration.metrics.logging_utils import (
    configure_logging,
    TimingLogger,
    ProgressTracker,
    DEBUG_DETAILED,
    DEBUG_TRACE
)


def create_sample_patient(patient_id='test-patient-1', is_valid=True):
    """Create a sample Patient resource.
    
    Args:
        patient_id: ID for the patient resource
        is_valid: Whether to create a valid or invalid resource
        
    Returns:
        Dictionary representing a FHIR Patient resource
    """
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [
            {
                "family": "Smith",
                "given": ["John"]
            }
        ],
        "gender": "male",
        "birthDate": "1970-01-01"
    }
    
    if not is_valid:
        # Create an invalid patient by setting invalid gender
        patient["gender"] = "invalid-gender"
    
    return patient


def create_sample_observation(patient_id='test-patient-1', observation_id='test-obs-1', is_valid=True):
    """Create a sample Observation resource.
    
    Args:
        patient_id: ID for the referenced patient
        observation_id: ID for the observation resource
        is_valid: Whether to create a valid or invalid resource
        
    Returns:
        Dictionary representing a FHIR Observation resource
    """
    observation = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
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
        "valueQuantity": {
            "value": 120,
            "unit": "mm[Hg]",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
        }
    }
    
    if not is_valid:
        # Create an invalid observation by removing required status
        del observation["status"]
    
    return observation


def main():
    """Run the Great Expectations validator test with enhanced logging."""
    # Configure logging
    configure_logging(
        log_level=logging.DEBUG,
        detailed_level=True,
        log_file="logs/validator_test.log",
        log_format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        module_levels={
            "epic_fhir_integration.metrics.great_expectations_validator": DEBUG_DETAILED,
        }
    )
    
    logger = logging.getLogger("validator_test")
    logger.info("Starting Great Expectations validator test")
    
    # Get or create test directory for expectations
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    test_dir = os.path.join(project_root, "tests", "test_data")
    expectations_dir = os.path.join(test_dir, "expectations")
    
    # Create directories if they don't exist
    os.makedirs(expectations_dir, exist_ok=True)
    
    # Create a Great Expectations validator
    with TimingLogger(logger, "Validator initialization", level=logging.INFO):
        validator = GreatExpectationsValidator(
            context_root_dir=test_dir,
            expectation_suite_dir=expectations_dir,
            debug_level=DEBUG_DETAILED
        )
    
    # Create expectation suites
    with TimingLogger(logger, "Create expectation suites", level=logging.INFO):
        create_patient_expectations(validator, "patient_expectations")
        validator.save_expectation_suite("patient_expectations", expectations_dir)
        
        create_observation_expectations(validator, "observation_expectations")
        validator.save_expectation_suite("observation_expectations", expectations_dir)
    
    # Create test resources
    logger.info("Creating test resources")
    valid_patient = create_sample_patient(is_valid=True)
    invalid_patient = create_sample_patient(patient_id="test-patient-2", is_valid=False)
    
    valid_observation = create_sample_observation(is_valid=True)
    invalid_observation = create_sample_observation(
        patient_id="test-patient-2",
        observation_id="test-obs-2",
        is_valid=False
    )
    
    # Validate individual resources
    logger.info("Validating individual resources")
    
    with TimingLogger(logger, "Validate valid patient", level=logging.INFO):
        result = validator.validate_resource(
            resource=valid_patient,
            expectation_suite_name="patient_expectations",
            pipeline_stage="test"
        )
        logger.info(f"Valid patient validation result: {result['is_valid']}")
    
    with TimingLogger(logger, "Validate invalid patient", level=logging.INFO):
        result = validator.validate_resource(
            resource=invalid_patient,
            expectation_suite_name="patient_expectations",
            pipeline_stage="test"
        )
        logger.info(f"Invalid patient validation result: {result['is_valid']}")
        logger.info(f"Issues found: {len(result['issues'])}")
    
    # Validate batch of resources
    logger.info("Validating batch of resources")
    
    # Create a larger batch for better progress tracking
    batch_size = 20
    patient_batch = []
    
    # Create progress tracker for generating test data
    tracker = ProgressTracker(logger, "Generate test batch", batch_size)
    
    for i in range(batch_size):
        # Create mostly valid resources with some invalid ones
        is_valid = i % 5 != 0  # Make every 5th resource invalid
        patient = create_sample_patient(
            patient_id=f"test-patient-{i+3}",
            is_valid=is_valid
        )
        patient_batch.append(patient)
        
        # Update progress tracker
        tracker.update(
            items_processed=1,
            successful=1 if is_valid else 0,
            failed=0 if is_valid else 1,
            force_log=(i == 0 or i == batch_size-1)
        )
    
    # Complete tracking
    tracker.complete()
    
    # Validate the batch
    with TimingLogger(logger, "Validate patient batch", level=logging.INFO, batch_size=batch_size):
        batch_result = validator.validate_resources(
            resources=patient_batch,
            expectation_suite_name="patient_expectations",
            pipeline_stage="test"
        )
    
    # Report batch validation results
    logger.info(f"Batch validation summary:")
    logger.info(f"  Total resources: {batch_result['resources_total']}")
    logger.info(f"  Valid resources: {batch_result['resources_valid']}")
    logger.info(f"  Validation rate: {batch_result['validation_rate'] * 100:.1f}%")
    logger.info(f"  Total issues: {batch_result['total_issues']}")
    logger.info(f"  Issues per resource: {batch_result['issues_per_resource']:.2f}")
    
    logger.info("Test completed successfully")


if __name__ == "__main__":
    main() 