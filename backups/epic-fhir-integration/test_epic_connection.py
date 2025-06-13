#!/usr/bin/env python3
"""
Test Epic FHIR API connection by fetching a token and making a simple request.
This script verifies the authentication setup and API connectivity.
"""

import os
import sys
import json
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

try:
    from epic_fhir_integration.auth.get_token import get_access_token, get_auth_headers
    import requests
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the required packages are installed:")
    print("pip install -e .")
    sys.exit(1)

# Default test patient ID
DEFAULT_PATIENT_ID = "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
# Default Epic FHIR API base URL
DEFAULT_FHIR_BASE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"

def test_auth():
    """Test authentication by obtaining an access token."""
    print("\n1. Testing authentication...")
    
    token_data = get_access_token(verbose=True)
    
    if token_data and "access_token" in token_data:
        print(f"✅ Successfully obtained access token!")
        print(f"   Token type: {token_data.get('token_type', 'Bearer')}")
        print(f"   Expires in: {token_data.get('expires_in')} seconds")
        return True
    else:
        print("❌ Failed to obtain access token")
        return False

def test_api_connection(base_url=DEFAULT_FHIR_BASE_URL):
    """Test connection to the FHIR API by fetching metadata."""
    print("\n2. Testing API connection...")
    
    try:
        # Get authentication headers
        headers = get_auth_headers()
        
        # Add FHIR-specific headers
        headers.update({
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        })
        
        # Make request to metadata endpoint
        metadata_url = f"{base_url}/metadata"
        print(f"   Requesting: {metadata_url}")
        
        response = requests.get(metadata_url, headers=headers)
        
        if response.ok:
            metadata = response.json()
            print(f"✅ Successfully connected to FHIR API")
            print(f"   Server name: {metadata.get('publisher', 'Unknown')}")
            print(f"   FHIR version: {metadata.get('fhirVersion', 'Unknown')}")
            return True
        else:
            print(f"❌ Failed to connect to FHIR API: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to FHIR API: {str(e)}")
        return False

def test_patient_access(patient_id=DEFAULT_PATIENT_ID, base_url=DEFAULT_FHIR_BASE_URL):
    """Test access to a specific patient."""
    print(f"\n3. Testing access to patient {patient_id}...")
    
    try:
        # Get authentication headers
        headers = get_auth_headers()
        
        # Add FHIR-specific headers
        headers.update({
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        })
        
        # Make request to patient endpoint
        patient_url = f"{base_url}/Patient/{patient_id}"
        print(f"   Requesting: {patient_url}")
        
        response = requests.get(patient_url, headers=headers)
        
        if response.ok:
            patient = response.json()
            print(f"✅ Successfully accessed patient data")
            # Print some basic info about the patient if available
            if "name" in patient and patient["name"]:
                name = patient["name"][0]
                given = " ".join(name.get("given", ["Unknown"]))
                family = name.get("family", "")
                print(f"   Patient name: {given} {family}")
            return True
        else:
            print(f"❌ Failed to access patient: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing patient: {str(e)}")
        return False

def load_config(config_path="config/live_epic_auth.json"):
    """Load configuration from file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return {}

def main():
    """Run all connection tests."""
    print("=== Epic FHIR API Connection Test ===")
    
    # Load configuration
    config = load_config()
    fhir_base_url = config.get("epic_base_url", DEFAULT_FHIR_BASE_URL)
    patient_id = config.get("test_patient_id", DEFAULT_PATIENT_ID)
    
    # Run tests
    auth_success = test_auth()
    
    if auth_success:
        api_success = test_api_connection(fhir_base_url)
        
        if api_success:
            patient_success = test_patient_access(patient_id, fhir_base_url)
            
            if patient_success:
                print("\n🎉 All tests passed successfully! The Epic FHIR API connection is working.")
                return 0
    
    print("\n❌ Some tests failed. Please check the error messages above.")
    return 1

if __name__ == "__main__":
    sys.exit(main()) 