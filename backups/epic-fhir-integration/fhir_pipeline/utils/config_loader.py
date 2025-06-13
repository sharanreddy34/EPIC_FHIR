"""
Configuration Loader Utilities for FHIR Pipeline

This module provides utilities for loading configuration values like client ID and private key
from various sources (environment variables, files, etc.)
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Default client ID if not specified elsewhere
DEFAULT_CLIENT_ID = "atlas-client-001"

def get_client_id() -> str:
    """
    Get the Epic FHIR API client ID from environment variables or defaults.
    
    Order of precedence:
    1. EPIC_CLIENT_ID environment variable
    2. Default client ID
    
    Returns:
        str: Client ID to use for API authentication
    """
    return os.environ.get("EPIC_CLIENT_ID", DEFAULT_CLIENT_ID)

def get_private_key() -> str:
    """
    Get the private key content from environment variables or files.
    
    Order of precedence:
    1. EPIC_PRIVATE_KEY environment variable
    2. Key file specified by EPIC_PRIVATE_KEY_PATH environment variable
    3. Standard key files: key.md, docs/key.md, etc.
    
    Returns:
        str: Private key content
    
    Raises:
        ValueError: If no private key can be found
    """
    # Check environment variable first
    if "EPIC_PRIVATE_KEY" in os.environ:
        logger.debug("Using private key from EPIC_PRIVATE_KEY environment variable")
        return os.environ["EPIC_PRIVATE_KEY"]
    
    # Check for key file path in environment
    key_path = os.environ.get("EPIC_PRIVATE_KEY_PATH")
    if key_path and Path(key_path).exists():
        logger.debug(f"Loading private key from {key_path}")
        with open(key_path, 'r') as f:
            return f.read()
    
    # Try standard locations
    standard_paths = [
        "key.md",
        "docs/key.md",
        "../docs/key.md",
        "../../docs/key.md",
        "auth/private_key.pem",
        "rsa_private.pem",
        "private_key.pem",
    ]
    
    # Get base directory
    base_dir = Path(__file__).parent.parent.parent.parent
    
    for rel_path in standard_paths:
        full_path = base_dir / rel_path
        if full_path.exists():
            logger.debug(f"Loading private key from {full_path}")
            with open(full_path, 'r') as f:
                return f.read()
    
    # If we get here, no key was found
    raise ValueError(
        "No private key found. Please set EPIC_PRIVATE_KEY environment variable, "
        "or EPIC_PRIVATE_KEY_PATH to a file path, or place key in a standard location."
    )

def load_epic_credentials() -> Tuple[str, str]:
    """
    Load Epic FHIR API credentials (client ID and private key).
    
    Returns:
        Tuple[str, str]: (client_id, private_key)
    """
    client_id = get_client_id()
    private_key = get_private_key()
    
    return client_id, private_key 