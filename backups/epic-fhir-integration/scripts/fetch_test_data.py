#!/usr/bin/env python3
"""
Fetch test data from Epic FHIR API and save it locally.
This script fetches FHIR resources for a specific test patient
and saves them for offline testing.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import time
from datetime import datetime

# Add project root to path for importing modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from epic_fhir_integration.config.loader import load_config
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fetch_test_data")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch test data from Epic FHIR API")
    parser.add_argument(
        "--config",
        default="config/live_epic_auth.json",
        help="Path to Epic FHIR API configuration file"
    )
    parser.add_argument(
        "--output",
        default="test_data",
        help="Directory to save fetched FHIR resources"
    )
    parser.add_argument(
        "--patient-id",
        default="T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
        help="Patient ID to fetch"
    )
    parser.add_argument(
        "--deidentify",
        action="store_true",
        help="De-identify patient data before saving"
    )
    return parser.parse_args()

def ensure_dir(directory):
    """Ensure a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def save_resource(resource, resource_type, output_dir):
    """Save a FHIR resource to a file."""
    if not resource:
        logger.warning(f"Resource {resource_type} is empty, not saving")
        return
    
    resource_dir = os.path.join(output_dir, resource_type)
    ensure_dir(resource_dir)
    
    if isinstance(resource, dict) and "id" in resource:
        filename = os.path.join(resource_dir, f"{resource['id']}.json")
        with open(filename, "w") as f:
            json.dump(resource, f, indent=2)
        logger.info(f"Saved {resource_type}/{resource['id']}")
    elif isinstance(resource, dict) and "entry" in resource:
        # Handle Bundle resources
        bundle_dir = os.path.join(resource_dir, "bundle")
        ensure_dir(bundle_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(bundle_dir, f"{resource_type}_{timestamp}.json")
        with open(filename, "w") as f:
            json.dump(resource, f, indent=2)
        logger.info(f"Saved {resource_type} bundle with {len(resource.get('entry', []))} entries")
        
        # Extract and save individual resources from bundle
        for i, entry in enumerate(resource.get("entry", [])):
            if "resource" in entry:
                entry_resource = entry["resource"]
                entry_type = entry_resource.get("resourceType", "Unknown")
                
                # Save the individual resource
                save_resource(entry_resource, entry_type, output_dir)
                
                # Rate limiting for API calls
                if i > 0 and i % 10 == 0:
                    time.sleep(0.5)  # Sleep to avoid overwhelming the server
    else:
        logger.warning(f"Unsupported resource format for {resource_type}")

def de_identify_resource(resource):
    """
    De-identify a FHIR resource by removing or masking identifiable information.
    This is a simple implementation that should be enhanced for production use.
    """
    if not isinstance(resource, dict):
        return resource
    
    # Make a copy to avoid modifying the original
    resource = resource.copy()
    
    # Handle different resource types
    resource_type = resource.get("resourceType", "")
    
    if resource_type == "Patient":
        # Mask names
        if "name" in resource:
            for name in resource["name"]:
                if "given" in name:
                    name["given"] = ["XXXXX" for _ in name["given"]]
                if "family" in name:
                    name["family"] = "XXXXX"
        
        # Mask identifiers
        if "identifier" in resource:
            for identifier in resource["identifier"]:
                if "value" in identifier:
                    identifier["value"] = "XXXXX"
        
        # Mask contact info
        for field in ["telecom", "address"]:
            if field in resource:
                resource[field] = []
    
    # Common fields across resource types
    if "text" in resource and "div" in resource["text"]:
        resource["text"]["div"] = "<div>De-identified</div>"
    
    return resource

def fetch_patient_data(client, patient_id, output_dir, deidentify=False):
    """Fetch all relevant data for a patient and save it."""
    logger.info(f"Fetching data for patient: {patient_id}")
    
    # Fetch and save patient demographics
    patient = client.get_patient(patient_id)
    if deidentify:
        patient = de_identify_resource(patient)
    save_resource(patient, "Patient", output_dir)
    
    # Fetch and save encounters
    encounters = client.get_patient_encounters(patient_id)
    if deidentify:
        if "entry" in encounters:
            for entry in encounters["entry"]:
                if "resource" in entry:
                    entry["resource"] = de_identify_resource(entry["resource"])
    save_resource(encounters, "Encounter", output_dir)
    
    # Fetch and save observations
    observations = client.get_patient_observations(patient_id)
    if deidentify:
        if "entry" in observations:
            for entry in observations["entry"]:
                if "resource" in entry:
                    entry["resource"] = de_identify_resource(entry["resource"])
    save_resource(observations, "Observation", output_dir)
    
    # Fetch and save conditions
    conditions = client.get_patient_conditions(patient_id)
    if deidentify:
        if "entry" in conditions:
            for entry in conditions["entry"]:
                if "resource" in entry:
                    entry["resource"] = de_identify_resource(entry["resource"])
    save_resource(conditions, "Condition", output_dir)
    
    # Fetch and save medications
    medications = client.get_patient_medications(patient_id)
    if deidentify:
        if "entry" in medications:
            for entry in medications["entry"]:
                if "resource" in entry:
                    entry["resource"] = de_identify_resource(entry["resource"])
    save_resource(medications, "MedicationRequest", output_dir)
    
    # Fetch and save procedures
    procedures = client.get_patient_procedures(patient_id)
    if deidentify:
        if "entry" in procedures:
            for entry in procedures["entry"]:
                if "resource" in entry:
                    entry["resource"] = de_identify_resource(entry["resource"])
    save_resource(procedures, "Procedure", output_dir)
    
    logger.info(f"Completed fetching data for patient: {patient_id}")

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create output directory
    ensure_dir(args.output)
    
    # Initialize FHIR client
    client = EpicFHIRClient(config)
    
    # Fetch data for specified patient
    try:
        fetch_patient_data(client, args.patient_id, args.output, args.deidentify)
    except Exception as e:
        logger.error(f"Error fetching patient data: {e}")
        sys.exit(1)
    
    logger.info(f"Test data successfully saved to {args.output}")

if __name__ == "__main__":
    main() 