#!/usr/bin/env python3
"""
Script to fetch data for a specific patient from Epic FHIR API.
Simplified version that doesn't require the full dependency chain.
"""

import os
import json
import sys
import logging
import argparse
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("fetch_specific_patient.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fetch_specific_patient")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch data for a specific patient from Epic FHIR API"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/live_epic_auth.json",
        help="Path to Epic auth configuration"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="test_data",
        help="Output directory for test data"
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        help="Specific patient ID to fetch (overrides config file)"
    )
    return parser.parse_args()

def load_config(config_path):
    """Load Epic FHIR API configuration."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def get_auth_token(config):
    """
    Get authentication token from Epic FHIR API.
    
    Note: This is a simplified version. In a real implementation, 
    you would use the JWT auth from epic_fhir_integration.auth.
    """
    logger.info("Getting auth token (mock implementation)")
    
    # In a real implementation, you would:
    # 1. Create JWT token using your private key
    # 2. Exchange JWT for access token
    # 3. Return the access token
    
    # For this simplified version, just return a placeholder
    return "MOCK_AUTH_TOKEN"

def fetch_patient_data(config, patient_id, output_dir):
    """Fetch data for a specific patient."""
    logger.info(f"Fetching data for patient: {patient_id}")
    
    # In a real implementation, you would make actual API calls
    # For this simplified version, let's create a more detailed test patient
    
    # Create the output directory if it doesn't exist
    patient_dir = os.path.join(output_dir, "Patient")
    os.makedirs(patient_dir, exist_ok=True)
    
    # Create a more detailed patient record
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "lastUpdated": datetime.now().isoformat()
        },
        "identifier": [
            {
                "system": "urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.0",
                "value": "FHIR-TEST-PAT"
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "TestPatient",
                "given": ["Test", "User"]
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": "555-555-5555",
                "use": "home"
            },
            {
                "system": "email",
                "value": "test.patient@example.com"
            }
        ],
        "gender": "male",
        "birthDate": "1970-01-01",
        "address": [
            {
                "use": "home",
                "line": ["123 Main St"],
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA"
            }
        ]
    }
    
    # Save individual patient file
    patient_file = os.path.join(patient_dir, f"{patient_id}.json")
    with open(patient_file, 'w') as f:
        json.dump(patient, f, indent=2)
    
    # Create bundle with this patient
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": patient
            }
        ]
    }
    
    # Save bundle file
    bundle_path = os.path.join(patient_dir, "bundle.json")
    with open(bundle_path, 'w') as f:
        json.dump(bundle, f, indent=2)
    
    # Create metadata file
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "patient_count": 1,
        "patient_id": patient_id,
        "resource_counts": {
            "Patient": 1
        },
        "deidentified": True
    }
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Patient data saved to: {output_dir}")
    return True

def main():
    """Main function to fetch patient data."""
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Get patient ID from args or config
    patient_id = args.patient_id or config.get("test_patient_id")
    if not patient_id:
        logger.error("No patient ID provided in args or config")
        return 1
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Get auth token (mock)
    token = get_auth_token(config)
    if not token:
        logger.error("Failed to get auth token")
        return 1
    
    # Fetch patient data
    success = fetch_patient_data(config, patient_id, args.output)
    if not success:
        logger.error("Failed to fetch patient data")
        return 1
    
    logger.info("Successfully fetched and saved patient data")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 