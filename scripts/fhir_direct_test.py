#!/usr/bin/env python3
"""
Direct EPIC FHIR API Test Script

This script performs direct API calls to the EPIC FHIR API using
a pre-generated token from epic_token.json.
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test patient ID
TEST_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"

# Resource types to extract
RESOURCE_TYPES = ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest", 
                 "Procedure", "Immunization", "AllergyIntolerance"]

class DirectFHIRTest:
    """Direct FHIR API test with real API calls."""
    
    def __init__(self, patient_id: str, debug: bool = False, output_dir: str = "fhir_output"):
        """
        Initialize the Direct FHIR test.
        
        Args:
            patient_id: Patient ID to test
            debug: Whether to enable debug logging
            output_dir: Output directory for test results
        """
        self.patient_id = patient_id
        self.debug = debug
        self.output_dir = output_dir
        
        # Set up logging
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        logger.info(f"Initializing Direct FHIR test for patient ID: {patient_id}")
        
        # Load EPIC token
        self.token = self._load_token()
        
        # Configure API URL
        self.base_url = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def _load_token(self) -> str:
        """
        Load EPIC access token from epic_token.json file.
        
        Returns:
            Access token string
        """
        try:
            with open("epic_token.json", "r") as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 0)
                
                if not access_token:
                    logger.error("No access_token found in epic_token.json")
                    logger.info("Attempting to refresh token...")
                    self._refresh_token()
                    # Try loading again
                    with open("epic_token.json", "r") as f:
                        token_data = json.load(f)
                        access_token = token_data.get("access_token")
                        if not access_token:
                            logger.error("Still no access_token after refresh")
                            sys.exit(1)
                
                logger.info(f"Loaded token expiring in {expires_in} seconds")
                return access_token
        except FileNotFoundError:
            logger.error("epic_token.json not found")
            logger.info("Attempting to create a new token...")
            self._refresh_token()
            # Try loading again
            return self._load_token()
        except Exception as e:
            logger.error(f"Error loading token: {str(e)}")
            sys.exit(1)
            
    def _refresh_token(self):
        """
        Refresh the EPIC access token.
        """
        try:
            logger.info("Refreshing EPIC token...")
            
            # Try to use the auth module
            try:
                from auth.setup_epic_auth import refresh_token
                token_data = refresh_token()
                if token_data:
                    logger.info("Token refreshed successfully")
                    return
            except ImportError:
                logger.warning("Could not import auth.setup_epic_auth, using simple_token_refresh.py")
                
            # Fall back to using the script directly
            result = os.system("python simple_token_refresh.py")
            if result != 0:
                logger.error("Failed to refresh token")
                sys.exit(1)
            logger.info("Token refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            sys.exit(1)
    
    def make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the FHIR API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        
        logger.debug(f"Making request to {url}")
        logger.debug(f"Parameters: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if self.debug:
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Check status
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return {"error": True, "status": response.status_code, "body": response.text}
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": True, "message": str(e)}
    
    def get_patient(self) -> Dict:
        """
        Get patient information.
        
        Returns:
            Patient resource
        """
        logger.info(f"Getting patient {self.patient_id}")
        return self.make_api_request(f"Patient/{self.patient_id}")
    
    def get_resource_for_patient(self, resource_type: str) -> Dict:
        """
        Get resources of a specific type for the patient.
        
        Args:
            resource_type: FHIR resource type
            
        Returns:
            Bundle containing resources
        """
        logger.info(f"Getting {resource_type} resources for patient {self.patient_id}")
        
        # Prepare parameters
        params = {"patient": self.patient_id}
        
        # For Observation resource, we need to add the required category parameter
        if resource_type == "Observation":
            params["category"] = "laboratory"
            
        return self.make_api_request(resource_type, params)
    
    def run_test(self) -> None:
        """
        Run the test for all resource types.
        """
        results = {}
        
        # First, get the patient
        patient_data = self.get_patient()
        self._save_result("Patient", patient_data)
        results["Patient"] = {"status": "success" if "resourceType" in patient_data else "error"}
        
        # Then get other resources for the patient
        for resource_type in RESOURCE_TYPES[1:]:  # Skip Patient
            resource_data = self.get_resource_for_patient(resource_type)
            self._save_result(resource_type, resource_data)
            
            if "error" in resource_data:
                results[resource_type] = {"status": "error", "message": resource_data.get("message", "")}
            else:
                # Count resources in bundle
                entry_count = len(resource_data.get("entry", []))
                results[resource_type] = {"status": "success", "count": entry_count}
        
        # Print summary
        self._print_summary(results)
    
    def _save_result(self, resource_type: str, data: Dict) -> None:
        """
        Save API response to a file.
        
        Args:
            resource_type: Resource type name
            data: Data to save
        """
        output_path = os.path.join(self.output_dir, f"{resource_type}.json")
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {resource_type} result to {output_path}")
    
    def _print_summary(self, results: Dict) -> None:
        """
        Print test results summary.
        
        Args:
            results: Test results by resource type
        """
        print("\n" + "="*80)
        print(f"SUMMARY OF DIRECT FHIR API TEST FOR PATIENT {self.patient_id}")
        print("="*80)
        
        for resource_type, result in results.items():
            status = result["status"]
            if status == "success":
                count = result.get("count", 1)  # Default to 1 for single resources like Patient
                print(f"{resource_type}: SUCCESS - {count} resources")
            else:
                print(f"{resource_type}: ERROR - {result.get('message', 'Unknown error')}")
        
        print("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Direct EPIC FHIR API test script")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--patient-id", default=TEST_PATIENT_ID, help="Patient ID to test")
    parser.add_argument("--output-dir", default="fhir_output", help="Output directory")
    args = parser.parse_args()
    
    # Run the test
    test = DirectFHIRTest(
        patient_id=args.patient_id,
        debug=args.debug,
        output_dir=args.output_dir
    )
    test.run_test()


if __name__ == "__main__":
    main() 