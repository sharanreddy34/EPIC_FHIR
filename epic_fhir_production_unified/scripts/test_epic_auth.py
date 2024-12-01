#!/usr/bin/env python3
"""
Epic FHIR API Authentication Test Script

This script tests the Epic FHIR API authentication setup
by attempting to get a token and making a simple API call.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
import requests
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("epic_auth_test")

# Add project root to path to ensure imports work
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import our authentication module
from epic_fhir_integration.auth.epic_auth import (
    get_token, 
    get_token_with_retry, 
    get_auth_headers,
    _load_private_key,
    _get_token_cache_path
)

def test_config():
    """Test that configuration is correctly set up."""
    from epic_fhir_integration.config.loader import get_config
    
    logger.info("Testing configuration...")
    
    # Get auth config
    auth_config = get_config("auth")
    
    # Check required fields
    required_fields = ["client_id", "jwt_issuer", "epic_base_url"]
    missing_fields = [field for field in required_fields if field not in auth_config]
    
    if missing_fields:
        logger.error(f"Missing required configuration: {', '.join(missing_fields)}")
        return False
    
    logger.info(f"Configuration loaded successfully:")
    logger.info(f"  client_id: {auth_config.get('client_id')}")
    logger.info(f"  jwt_issuer: {auth_config.get('jwt_issuer')}")
    logger.info(f"  epic_base_url: {auth_config.get('epic_base_url')}")
    
    return True

def test_private_key():
    """Test that the private key can be loaded."""
    logger.info("Testing private key loading...")
    
    try:
        private_key = _load_private_key()
        if private_key:
            logger.info("Private key loaded successfully")
            lines = private_key.count('\n') + 1
            logger.info(f"Private key is {len(private_key)} characters, {lines} lines")
            return True
    except Exception as e:
        logger.error(f"Error loading private key: {e}")
    
    return False

def test_token():
    """Test getting a token."""
    logger.info("Testing token acquisition...")
    
    try:
        token_data = get_token_with_retry()
        
        if not token_data or 'access_token' not in token_data:
            logger.error("Failed to get access token")
            return False
            
        logger.info("Token acquired successfully!")
        logger.info(f"Token type: {token_data.get('token_type', 'unknown')}")
        logger.info(f"Expires in: {token_data.get('expires_in', 'unknown')} seconds")
        
        # Log token prefix (first 10 chars) for verification
        token = token_data['access_token']
        logger.info(f"Token start: {token[:10]}...")
        
        # Check if token was cached
        cache_path = _get_token_cache_path()
        if cache_path.exists():
            logger.info(f"Token cached to: {cache_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error getting token: {e}")
        return False

def test_api_call():
    """Test making a simple API call."""
    logger.info("Testing API call with token...")
    
    try:
        # Get auth headers
        headers = get_auth_headers()
        
        # Construct FHIR API URL for metadata (no authorization required)
        from epic_fhir_integration.config.loader import get_config
        fhir_config = get_config("fhir")
        base_url = fhir_config.get("base_url", "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4")
        metadata_url = f"{base_url}/metadata"
        
        # Make request
        logger.info(f"Making request to {metadata_url}")
        response = requests.get(
            metadata_url,
            headers=headers,
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            logger.info(f"API call successful (status {response.status_code})")
            
            # Parse response
            data = response.json()
            
            # Check FHIR version
            if 'fhirVersion' in data:
                logger.info(f"FHIR Version: {data['fhirVersion']}")
            
            return True
        else:
            logger.error(f"API call failed with status {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        logger.error(f"Error making API call: {e}")
        return False

def main():
    """Run the authentication test."""
    print("\n==== Epic FHIR API Authentication Test ====\n")
    
    # Test configuration
    config_ok = test_config()
    print(f"\nConfiguration test: {'PASSED' if config_ok else 'FAILED'}\n")
    
    # Test private key
    key_ok = test_private_key()
    print(f"\nPrivate key test: {'PASSED' if key_ok else 'FAILED'}\n")
    
    # Test token
    token_ok = test_token()
    print(f"\nToken acquisition test: {'PASSED' if token_ok else 'FAILED'}\n")
    
    # Test API call
    api_ok = test_api_call() if token_ok else False
    print(f"\nAPI call test: {'PASSED' if api_ok else 'FAILED'}\n")
    
    # Overall result
    all_passed = config_ok and key_ok and token_ok and api_ok
    
    print("\n==== Test Summary ====")
    print(f"Configuration test: {'PASSED' if config_ok else 'FAILED'}")
    print(f"Private key test: {'PASSED' if key_ok else 'FAILED'}")
    print(f"Token acquisition test: {'PASSED' if token_ok else 'FAILED'}")
    print(f"API call test: {'PASSED' if api_ok else 'FAILED'}")
    print(f"\nOverall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 