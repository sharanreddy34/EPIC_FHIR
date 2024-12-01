#!/usr/bin/env python3
"""
Fetch patient data from Epic FHIR API and save it locally.

This script fetches FHIR resources for a specific patient and saves them for use in testing.
It uses the authentication module to obtain access tokens and properly handles dates for serialization.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import Epic FHIR integration modules
try:
    from epic_fhir_integration.auth.get_token import get_access_token, get_auth_headers
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the epic-fhir-integration package is installed:")
    print("pip install -e .")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("fetch_patient_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fetch_patient_data")

# Default test patient ID as specified in documentation
DEFAULT_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"


# Custom JSON encoder to handle date objects
class FHIRJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for FHIR resources that handles date objects."""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch patient data from Epic FHIR API")
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
        default=DEFAULT_PATIENT_ID,
        help=f"Patient ID to fetch (default: {DEFAULT_PATIENT_ID})"
    )
    parser.add_argument(
        "--deidentify",
        action="store_true",
        help="De-identify patient data before saving"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip resources that already exist in the output directory"
    )
    return parser.parse_args()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}


def de_identify_resource(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    De-identify a FHIR resource by removing or masking PHI.
    
    Args:
        resource: FHIR resource dictionary
        
    Returns:
        De-identified resource
    """
    # Make a copy to avoid modifying the original
    resource = resource.copy()
    
    # Mask specific PHI fields based on resource type
    if resource.get("resourceType") == "Patient":
        # Replace name with generic placeholder
        if "name" in resource:
            for name in resource["name"]:
                if "given" in name:
                    name["given"] = ["DEIDENTIFIED"]
                if "family" in name:
                    name["family"] = "USER"
        
        # Remove or mask other PHI
        resource.pop("telecom", None)
        resource.pop("address", None)
        resource.pop("photo", None)
        
        # Generalize birthDate to year only if present
        if "birthDate" in resource:
            try:
                year = resource["birthDate"].split("-")[0]
                resource["birthDate"] = f"{year}-01-01"
            except (IndexError, AttributeError):
                resource.pop("birthDate", None)
    
    # For other resources that might contain patient info
    for elem in ["contained", "entry"]:
        if elem in resource and isinstance(resource[elem], list):
            for i, item in enumerate(resource[elem]):
                # Handle bundle entries
                if "resource" in item:
                    resource[elem][i]["resource"] = de_identify_resource(item["resource"])
                # Handle contained resources
                else:
                    resource[elem][i] = de_identify_resource(item)
    
    return resource


def save_resource(resource: Dict[str, Any], resource_type: str, output_dir: str) -> None:
    """
    Save a FHIR resource to file.
    
    Args:
        resource: FHIR resource as a dictionary
        resource_type: Type of resource
        output_dir: Base directory to save resources
    """
    # Create resource directory
    resource_dir = os.path.join(output_dir, resource_type)
    os.makedirs(resource_dir, exist_ok=True)
    
    # Handle bundles differently
    if resource_type != resource.get("resourceType"):
        # This is a bundle or collection of resources
        if "entry" in resource:
            # Save bundle
            bundle_path = os.path.join(resource_dir, "bundle.json")
            with open(bundle_path, 'w') as f:
                json.dump(resource, f, indent=2, cls=FHIRJSONEncoder)
            
            # Extract and save individual resources
            for entry in resource.get("entry", []):
                if "resource" in entry:
                    entry_resource = entry["resource"]
                    entry_type = entry_resource.get("resourceType")
                    entry_id = entry_resource.get("id")
                    
                    if entry_type and entry_id:
                        # Create type directory if it doesn't exist
                        entry_dir = os.path.join(output_dir, entry_type)
                        os.makedirs(entry_dir, exist_ok=True)
                        
                        # Save individual resource
                        entry_path = os.path.join(entry_dir, f"{entry_id}.json")
                        with open(entry_path, 'w') as f:
                            json.dump(entry_resource, f, indent=2, cls=FHIRJSONEncoder)
        else:
            # Just save the resource with provided type
            resource_path = os.path.join(resource_dir, "resource.json")
            with open(resource_path, 'w') as f:
                json.dump(resource, f, indent=2, cls=FHIRJSONEncoder)
    else:
        # Single resource with ID
        resource_id = resource.get("id", "resource")
        resource_path = os.path.join(resource_dir, f"{resource_id}.json")
        with open(resource_path, 'w') as f:
            json.dump(resource, f, indent=2, cls=FHIRJSONEncoder)
    
    logger.info(f"Saved {resource_type} resource to {resource_dir}")


def fetch_resource(base_url: str, 
                   resource_type: str, 
                   patient_id: str = None, 
                   resource_id: str = None,
                   params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fetch a FHIR resource from the Epic API.
    
    Args:
        base_url: FHIR API base URL
        resource_type: Type of resource to fetch
        patient_id: Patient ID for patient-specific resources
        resource_id: Resource ID for fetching a specific resource
        params: Additional query parameters
        
    Returns:
        FHIR resource as a dictionary
    """
    import requests
    
    # Get auth headers
    headers = get_auth_headers()
    headers.update({
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json"
    })
    
    # Build URL
    url = f"{base_url}/{resource_type}"
    if resource_id:
        url = f"{url}/{resource_id}"
    
    # Prepare parameters
    query_params = params.copy() if params else {}
    
    # Add patient reference for patient-specific resources
    if patient_id and resource_type != "Patient":
        query_params["patient"] = patient_id
    elif patient_id and resource_type == "Patient":
        query_params["_id"] = patient_id
    
    # Make the request
    logger.info(f"Fetching {resource_type} from {url}")
    response = requests.get(url, headers=headers, params=query_params)
    
    # Handle rate limiting
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 5))
        logger.warning(f"Rate limited. Waiting {retry_after} seconds")
        time.sleep(retry_after)
        return fetch_resource(base_url, resource_type, patient_id, resource_id, params)
    
    # Check for successful response
    response.raise_for_status()
    
    # Return raw JSON response as dictionary
    return response.json()


def fetch_patient_data(fhir_base_url: str, patient_id: str, output_dir: str, deidentify: bool = False) -> bool:
    """
    Fetch all relevant data for a patient and save it.
    
    Args:
        fhir_base_url: Base URL for the FHIR API
        patient_id: Patient ID to fetch
        output_dir: Directory to save data
        deidentify: Whether to de-identify the data
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Fetching data for patient: {patient_id}")
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Fetch and save patient demographics
        patient = fetch_resource(fhir_base_url, "Patient", patient_id)
        if deidentify:
            patient = de_identify_resource(patient)
        save_resource(patient, "Patient", output_dir)
        
        # Fetch and save encounters
        encounters = fetch_resource(fhir_base_url, "Encounter", patient_id, params={"_count": 50})
        if deidentify:
            encounters = de_identify_resource(encounters)
        save_resource(encounters, "Encounter", output_dir)
        
        # Fetch and save observations (vital signs)
        vitals = fetch_resource(fhir_base_url, "Observation", patient_id, 
                              params={"category": "vital-signs", "_count": 50})
        if deidentify:
            vitals = de_identify_resource(vitals)
        save_resource(vitals, "Observation_VitalSigns", output_dir)
        
        # Fetch and save observations (lab results)
        labs = fetch_resource(fhir_base_url, "Observation", patient_id, 
                             params={"category": "laboratory", "_count": 50})
        if deidentify:
            labs = de_identify_resource(labs)
        save_resource(labs, "Observation_Laboratory", output_dir)
        
        # Fetch and save conditions
        conditions = fetch_resource(fhir_base_url, "Condition", patient_id, params={"_count": 50})
        if deidentify:
            conditions = de_identify_resource(conditions)
        save_resource(conditions, "Condition", output_dir)
        
        # Fetch and save medications
        medications = fetch_resource(fhir_base_url, "MedicationRequest", patient_id, params={"_count": 50})
        if deidentify:
            medications = de_identify_resource(medications)
        save_resource(medications, "MedicationRequest", output_dir)
        
        # Fetch and save procedures
        procedures = fetch_resource(fhir_base_url, "Procedure", patient_id, params={"_count": 50})
        if deidentify:
            procedures = de_identify_resource(procedures)
        save_resource(procedures, "Procedure", output_dir)
        
        # Create metadata file
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "patient_id": patient_id,
            "deidentified": deidentify,
            "api_base": fhir_base_url,
            "resources_fetched": [
                "Patient", "Encounter", "Observation", "Condition", 
                "MedicationRequest", "Procedure"
            ]
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, cls=FHIRJSONEncoder)
        
        logger.info(f"Completed fetching data for patient: {patient_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error fetching patient data: {str(e)}", exc_info=True)
        return False


def main():
    """Main function to run the script."""
    args = parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    
    # Get FHIR base URL from config
    fhir_base_url = config.get("epic_base_url", "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4")
    
    # Get patient ID from args or config
    patient_id = args.patient_id or config.get("test_patient_id", DEFAULT_PATIENT_ID)
    
    # Create output directory path
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch patient data
    success = fetch_patient_data(
        fhir_base_url=fhir_base_url,
        patient_id=patient_id,
        output_dir=output_dir,
        deidentify=args.deidentify
    )
    
    if success:
        logger.info(f"Successfully fetched and saved patient data to {output_dir}")
        return 0
    else:
        logger.error("Failed to fetch patient data")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 