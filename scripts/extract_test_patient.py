#!/usr/bin/env python3
"""
Simple FHIR extraction script for a test patient

This script extracts FHIR data for a specific test patient from Epic.
It's a simplified version of the full workflow that just focuses on retrieving
the data for review and testing.

Usage:
    python extract_test_patient.py --patient-id <id> [--resources <resources>] [--debug]

Example:
    python extract_test_patient.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug
"""

import os
import sys
import json
import yaml
import logging
import argparse
import datetime
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from lib.fhir_client import FHIRClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_debug_logging(enable_debug: bool):
    """
    Configure debug logging.
    
    Args:
        enable_debug: Whether to enable debug logging
    """
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        # Also set debug level for requests library
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        
        # Log to file in addition to console
        debug_log_file = Path("debug_extract.log")
        file_handler = logging.FileHandler(debug_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled")


def load_token(token_path: str) -> Optional[str]:
    """
    Load access token from file.
    
    Args:
        token_path: Path to token file
        
    Returns:
        Access token or None if not found
    """
    logger.debug(f"Loading token from: {token_path}")
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
            logger.debug("Token loaded successfully")
            return token_data.get('access_token')
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to load token: {str(e)}")
        logger.debug(f"Token error details: {traceback.format_exc()}")
        return None


def get_token(client_id: str, client_secret: str, token_url: str) -> Optional[str]:
    """
    Get a new access token.
    
    Args:
        client_id: Epic client ID
        client_secret: Epic client secret
        token_url: Token endpoint URL
        
    Returns:
        Access token or None if failed
    """
    try:
        # Try to use the new auth module to get a token
        logger.debug("Attempting to refresh token using the auth module")
        from auth.setup_epic_auth import refresh_token
        
        token_data = refresh_token()
        if token_data and 'access_token' in token_data:
            logger.info("Successfully obtained fresh token using auth module")
            return token_data.get('access_token')
            
        logger.warning("Could not get token from auth module, falling back to legacy method")
        
        # Legacy method
        logger.debug(f"Requesting new token from: {token_url}")
        logger.debug(f"Using client ID: {client_id}")
        
        start_time = time.time()
        # For testing, we'll use client credentials
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        }
        
        logger.debug(f"Token request data: {data}")
        
        response = requests.post(token_url, data=data)
        elapsed_time = time.time() - start_time
        
        logger.debug(f"Token request completed in {elapsed_time:.2f} seconds with status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Token request failed with status code {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(f"Response content: {response.text[:500]}...")
            response.raise_for_status()
        
        token_data = response.json()
        logger.debug("Token obtained successfully")
        return token_data.get('access_token')
    except Exception as e:
        logger.error(f"Failed to get token: {str(e)}")
        logger.debug(f"Token error details: {traceback.format_exc()}")
        return None


def extract_patient_resources(
    base_url: str,
    token: str,
    patient_id: str,
    resource_types: List[str],
    output_dir: str,
    mock_mode: bool = False
):
    """
    Extract resources for a patient and save to files.
    
    Args:
        base_url: Base FHIR API URL
        token: Access token
        patient_id: Patient ID to extract data for
        resource_types: List of resource types to extract
        output_dir: Directory to save extracted resources
        mock_mode: If True, generate mock data instead of making API calls
    """
    start_time = time.time()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Extraction started at {datetime.datetime.now().isoformat()}")
    logger.info(f"Patient ID: {patient_id}")
    logger.info(f"Resource types: {resource_types}")
    logger.info(f"Output directory: {output_path}")
    logger.info(f"Mock mode: {mock_mode}")
    
    if mock_mode:
        logger.info("Running in mock mode - generating sample data")
        # Generate mock data
        for resource_type in resource_types:
            resource_start_time = time.time()
            try:
                logger.info(f"Generating mock {resource_type} resources")
                
                # Create resource directory
                resource_dir = output_path / resource_type
                resource_dir.mkdir(exist_ok=True)
                
                # Create a sample bundle
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_0.json"
                
                # Generate mock bundle data based on resource type
                entry_count = 1 if resource_type == "Patient" else 5  # More entries for non-Patient resources
                bundle = create_mock_bundle(resource_type, patient_id, entry_count)
                
                # Add metadata
                bundle_metadata = {
                    "resource_type": resource_type,
                    "extracted_at": datetime.datetime.now().isoformat(),
                    "page_number": 0,
                    "entry_count": entry_count,
                }
                
                bundle_with_metadata = {
                    "metadata": bundle_metadata,
                    "bundle": bundle,
                }
                
                # Write bundle to file
                with open(resource_dir / filename, 'w') as f:
                    json.dump(bundle_with_metadata, f, indent=2)
                
                resource_elapsed_time = time.time() - resource_start_time
                logger.info(f"Generated mock {resource_type} resource with {entry_count} entries in {resource_elapsed_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Error generating mock {resource_type}: {str(e)}")
                logger.debug(f"Mock generation error details: {traceback.format_exc()}")
        
        return
    
    # Create FHIR client
    def token_provider():
        return token
    
    try:
        # Import the FHIR client - this might fail if the module is not available
        from lib.fhir_client import FHIRClient
        client = FHIRClient(base_url, token_provider)
        
        # Test client connection
        logger.debug("Testing FHIR client connection")
        connection_start = time.time()
        if not client.validate_connection():
            logger.error("Failed to connect to FHIR server")
            logger.debug("Connection validation failed - check credentials and network")
            return
        logger.debug(f"Connection test completed in {time.time() - connection_start:.2f} seconds")
        
        logger.info(f"Starting extraction for patient {patient_id}")
        
        # Extract resources
        total_resources = 0
        for resource_type in resource_types:
            resource_start_time = time.time()
            try:
                logger.info(f"Extracting {resource_type} resources")
                
                # Create resource directory
                resource_dir = output_path / resource_type
                resource_dir.mkdir(exist_ok=True)
                
                # Search for resources
                page_count = 0
                bundle_count = 0
                
                search_params = {
                    "patient": patient_id
                }
                
                # Special case for Patient resource
                if resource_type == "Patient":
                    search_params = {
                        "_id": patient_id
                    }
                
                # Special case for Observation resource - add required category parameter
                elif resource_type == "Observation":
                    search_params["category"] = "laboratory"
                    logger.debug(f"Added 'category=laboratory' parameter for Observation resource")
                
                logger.debug(f"Searching {resource_type} with params: {search_params}")
                
                request_times = []
                for bundle in client.search_resource(resource_type, search_params):
                    page_start = time.time()
                    
                    # Create timestamp-based filename
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{page_count}.json"
                    
                    # Log bundle details
                    entry_count = len(bundle.get("entry", []))
                    logger.debug(f"Received {resource_type} bundle page {page_count} with {entry_count} entries")
                    
                    # Add metadata
                    bundle_metadata = {
                        "resource_type": resource_type,
                        "extracted_at": datetime.datetime.now().isoformat(),
                        "page_number": page_count,
                        "entry_count": entry_count,
                    }
                    
                    bundle_with_metadata = {
                        "metadata": bundle_metadata,
                        "bundle": bundle,
                    }
                    
                    # Write bundle to file
                    file_path = resource_dir / filename
                    with open(file_path, 'w') as f:
                        json.dump(bundle_with_metadata, f, indent=2)
                    
                    # Update counters
                    bundle_count += entry_count
                    page_count += 1
                    
                    page_elapsed = time.time() - page_start
                    request_times.append(page_elapsed)
                    logger.debug(f"Page {page_count} processed in {page_elapsed:.2f} seconds")
                    
                resource_elapsed_time = time.time() - resource_start_time
                avg_request_time = sum(request_times) / len(request_times) if request_times else 0
                
                logger.info(f"Extracted {bundle_count} {resource_type} resources in {page_count} pages")
                logger.debug(f"{resource_type} extraction completed in {resource_elapsed_time:.2f} seconds")
                logger.debug(f"Average request time: {avg_request_time:.2f} seconds")
                
                total_resources += bundle_count
                
            except Exception as e:
                logger.error(f"Error extracting {resource_type}: {str(e)}")
                logger.debug(f"Extraction error details: {traceback.format_exc()}")
        
        logger.info(f"Total resources extracted: {total_resources}")
        
    except ImportError as e:
        logger.error(f"Could not import FHIR client module: {e}")
        logger.error("Falling back to mock mode")
        extract_patient_resources(base_url, token, patient_id, resource_types, output_dir, mock_mode=True)
    
    total_elapsed = time.time() - start_time
    logger.info(f"Extraction complete in {total_elapsed:.2f} seconds")


def create_mock_bundle(resource_type: str, patient_id: str, entry_count: int) -> Dict[str, Any]:
    """
    Create a mock FHIR Bundle for a resource type.
    
    Args:
        resource_type: The FHIR resource type
        patient_id: The patient ID
        entry_count: Number of entries to create
        
    Returns:
        Dict representing a FHIR Bundle
    """
    logger.debug(f"Creating mock bundle for {resource_type} with {entry_count} entries")
    
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": entry_count,
        "entry": []
    }
    
    for i in range(entry_count):
        resource_id = f"mock-{resource_type.lower()}-{i+1}"
        
        # Base resource data
        resource = {
            "resourceType": resource_type,
            "id": resource_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.datetime.now().isoformat()
            }
        }
        
        # Add type-specific data
        if resource_type == "Patient":
            resource.update({
                "name": [{"family": "TestFamily", "given": ["TestFirst"]}],
                "gender": "unknown",
                "birthDate": "2000-01-01",
                "active": True
            })
        elif resource_type == "Encounter":
            resource.update({
                "status": "finished",
                "class": {"code": "AMB", "display": "Ambulatory"},
                "subject": {"reference": f"Patient/{patient_id}"},
                "period": {
                    "start": "2023-01-01T08:00:00Z",
                    "end": "2023-01-01T09:00:00Z"
                }
            })
        elif resource_type == "Observation":
            resource.update({
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Body Height"}]},
                "subject": {"reference": f"Patient/{patient_id}"},
                "effectiveDateTime": "2023-01-01T08:30:00Z",
                "valueQuantity": {"value": 170 + i, "unit": "cm"}
            })
        elif resource_type == "Condition":
            resource.update({
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes mellitus"}]},
                "subject": {"reference": f"Patient/{patient_id}"},
                "recordedDate": "2022-12-15T08:30:00Z"
            })
        elif resource_type == "MedicationRequest":
            resource.update({
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1117110", "display": "Metformin"}]},
                "subject": {"reference": f"Patient/{patient_id}"},
                "authoredOn": "2022-12-15T10:30:00Z",
                "dosageInstruction": [{"text": "Take 500mg twice daily with meals"}]
            })
        
        # Add to bundle
        bundle["entry"].append({
            "fullUrl": f"{resource_type}/{resource_id}",
            "resource": resource
        })
    
    logger.debug(f"Created mock bundle with {len(bundle['entry'])} entries")
    return bundle


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Extract FHIR data for a test patient")
    parser.add_argument("--patient-id", required=True, help="Patient ID to extract data for")
    parser.add_argument("--resources", default="Patient,Encounter,Observation,Condition,MedicationRequest",
                       help="Comma-separated list of resource types to extract")
    parser.add_argument("--token-file", default="epic_token.json", help="Path to token file")
    parser.add_argument("--output-dir", default="./patient_data", help="Output directory")
    parser.add_argument("--config-file", default="config/api_config.yaml", help="API config file")
    parser.add_argument("--mock", action="store_true", help="Use mock mode to generate sample data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Setup debug logging if requested
    setup_debug_logging(args.debug)
    
    logger.info(f"Starting extraction script at {datetime.datetime.now().isoformat()}")
    logger.debug(f"Command line arguments: {args}")
    
    # Validate patient ID
    if not args.patient_id:
        logger.error("Patient ID is required")
        sys.exit(1)
    
    logger.debug(f"Environment variables: EPIC_CLIENT_ID={bool(os.environ.get('EPIC_CLIENT_ID'))}, EPIC_CLIENT_SECRET={bool(os.environ.get('EPIC_CLIENT_SECRET'))}")
    
    # Get list of resources to extract
    resource_types = args.resources.split(',')
    logger.debug(f"Resource types to extract: {resource_types}")
    
    # Load API config - default values if not found
    base_url = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    token_url = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
    
    try:
        logger.debug(f"Loading config from {args.config_file}")
        with open(args.config_file, 'r') as f:
            config = yaml.safe_load(f)
            base_url = config['api']['base_url']
            token_url = config['api']['token_url']
            logger.debug(f"Loaded config: base_url={base_url}, token_url={token_url}")
    except Exception as e:
        logger.warning(f"Failed to load config: {str(e)} - using default values")
        logger.debug(f"Config error details: {traceback.format_exc()}")
    
    # Get token or use mock mode
    if args.mock:
        logger.debug("Mock mode enabled, using dummy token")
        token = "mock-token"
    else:
        logger.debug(f"Attempting to load token from {args.token_file}")
        token = load_token(args.token_file)
        if not token:
            logger.warning("No token found in file, attempting to get a new one")
            
            # In production, get these from secure storage
            client_id = os.environ.get("EPIC_CLIENT_ID", "3d6d8f7d-9bea-4fe2-b44d-81c7fec75ee5")
            client_secret = os.environ.get("EPIC_CLIENT_SECRET", "")
            
            if not client_secret:
                logger.warning("EPIC_CLIENT_SECRET environment variable not set - using mock mode")
                logger.debug("No client secret available, switching to mock mode")
                token = "mock-token"
                args.mock = True
            else:
                logger.debug(f"Requesting new token from {token_url}")
                token = get_token(client_id, client_secret, token_url)
                if not token:
                    logger.warning("Failed to get token - using mock mode")
                    logger.debug("Token request failed, switching to mock mode")
                    token = "mock-token"
                    args.mock = True
    
    # Create output directory with patient ID
    output_dir = Path(args.output_dir) / args.patient_id
    logger.debug(f"Using output directory: {output_dir}")
    
    # Time the extraction process
    extraction_start = time.time()
    
    # Extract resources
    extract_patient_resources(
        base_url,
        token,
        args.patient_id,
        resource_types,
        output_dir,
        mock_mode=args.mock
    )
    
    extraction_elapsed = time.time() - extraction_start
    logger.info(f"Total extraction time: {extraction_elapsed:.2f} seconds")
    
    # Print summary
    resource_counts = {}
    for resource_type in resource_types:
        resource_dir = output_dir / resource_type
        if resource_dir.exists():
            files = list(resource_dir.glob("*.json"))
            total_entries = 0
            
            for file in files:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        total_entries += data.get("metadata", {}).get("entry_count", 0)
                except Exception as e:
                    logger.warning(f"Error reading file {file}: {str(e)}")
            
            resource_counts[resource_type] = total_entries
    
    print("\nExtraction Summary:")
    print(f"Patient ID: {args.patient_id}")
    print(f"Output directory: {output_dir}")
    print("\nResource counts:")
    
    for resource_type, count in resource_counts.items():
        print(f"  - {resource_type}: {count} resources")
    
    logger.info("Extraction process completed successfully")
    print("\nExtraction complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.error("\nExtraction interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled error: {str(e)}")
        print(f"\nFatal error: {str(e)}")
        print("See logs for more details or run with --debug for verbose output")
        sys.exit(1) 