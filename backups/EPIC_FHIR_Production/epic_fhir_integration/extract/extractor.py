"""
FHIR Resource Extractor for Epic API.

This module extracts FHIR resources from the Epic FHIR API.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

def get_auth_token() -> str:
    """Get authentication token for Epic FHIR API.
    
    Returns:
        Authentication token.
    """
    # In production, this would retrieve a token using SMART on FHIR OAuth
    # Here we just check for a client_id and client_secret in environment or secrets
    
    client_id = os.environ.get("EPIC_CLIENT_ID")
    client_secret = os.environ.get("EPIC_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        # Check if we have a secret from Foundry mounted at /var/run/secrets/epic-oauth-secret
        secret_path = Path("/var/run/secrets/epic-oauth-secret/epic-oauth-secret")
        if secret_path.exists():
            try:
                with open(secret_path, "r") as f:
                    secret_data = json.load(f)
                    client_id = secret_data.get("client_id")
                    client_secret = secret_data.get("client_secret")
            except Exception as e:
                logger.error(f"Error loading secret from {secret_path}: {e}")
    
    if not client_id or not client_secret:
        raise ValueError("Missing Epic API credentials. Set EPIC_CLIENT_ID and EPIC_CLIENT_SECRET or provide epic-oauth-secret.")
    
    # Return a dummy token for now - in production this would be a proper OAuth token
    return "dummy_token"


def extract_resources(
    resource_types: List[str],
    output_base_dir: str,
    params: Optional[Dict[str, Dict[str, Any]]] = None,
    page_limit: Optional[int] = None,
    total_limit: Optional[int] = None,
) -> Dict[str, str]:
    """Extract FHIR resources from Epic API.
    
    Args:
        resource_types: List of FHIR resource types to extract.
        output_base_dir: Base directory for output files.
        params: Resource-specific parameters for extraction.
        page_limit: Maximum number of pages to retrieve per resource type.
        total_limit: Maximum total number of resources to retrieve per resource type.
        
    Returns:
        Dictionary mapping resource types to output file paths.
    """
    base_url = os.environ.get("EPIC_BASE_URL", "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4")
    
    # Get authentication token
    token = get_auth_token()
    
    # Ensure output directory exists
    output_dir = Path(output_base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Track output files
    output_files = {}
    
    # Extract each resource type
    for resource_type in resource_types:
        logger.info(f"Extracting resource type: {resource_type}")
        
        # Create resource-specific output directory
        resource_output_dir = output_dir / resource_type
        resource_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = resource_output_dir / f"{resource_type}_{timestamp}.ndjson"
        
        # Get resource-specific parameters
        resource_params = params.get(resource_type, {}) if params else {}
        
        # Simulate extraction - in production this would make actual API calls
        with open(output_file, "w") as f:
            # Placeholder: Write 10 dummy resources
            for i in range(10):
                dummy_resource = {
                    "resourceType": resource_type,
                    "id": f"dummy-{resource_type}-{i}",
                    "meta": {
                        "lastUpdated": datetime.now().isoformat()
                    },
                    # Add more resource-specific fields here
                }
                f.write(json.dumps(dummy_resource) + "\n")
        
        output_files[resource_type] = str(output_file)
        logger.info(f"Extracted {resource_type} to {output_file}")
    
    return output_files 