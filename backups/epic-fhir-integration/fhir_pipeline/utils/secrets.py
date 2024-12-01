import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Check if running in Foundry
IN_FOUNDRY = "FOUNDRY_PROJECT" in os.environ

def get_jwt_private_key(key_name: str = "epic_private_key") -> Optional[str]:
    """
    Get a JWT private key from the appropriate location.
    
    In Foundry, retrieves from the secret store.
    In local development, tries to load from file.
    
    Args:
        key_name: Name of the key in the secret store
        
    Returns:
        Private key as string or None if not found
    """
    # In Foundry environment, use Foundry secret APIs
    if IN_FOUNDRY:
        return _get_foundry_secret(key_name)
    
    # In local development, look for file-based keys
    return _get_local_private_key(key_name)

def _get_foundry_secret(secret_name: str) -> Optional[str]:
    """
    Get a secret from Foundry's secret store.
    
    Args:
        secret_name: Name of the secret
        
    Returns:
        Secret value or None if not found
    """
    if not IN_FOUNDRY:
        logger.warning("Attempted to access Foundry secret store outside of Foundry")
        return None
        
    try:
        # Import Foundry-specific modules only when in Foundry
        try:
            from foundry_dev_tools.utils.secrets import get_secret
            # This is a placeholder - the actual function might be different
            # depending on Foundry's Python SDK
            secret_value = get_secret(secret_name)
            if secret_value:
                logger.info(f"Retrieved secret {secret_name} from Foundry store")
                return secret_value
            else:
                logger.error(f"Secret {secret_name} not found in Foundry store")
                return None
        except ImportError:
            logger.error("Foundry dev tools not available")
            return None
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {e}")
        return None

def _get_local_private_key(key_name: str) -> Optional[str]:
    """
    Get a private key from a local file.
    
    For development environments only.
    Looks for keys in:
    1. Environment variable EPIC_PRIVATE_KEY
    2. File referenced by EPIC_PRIVATE_KEY_FILE
    3. Default location auth/private_key.pem
    
    Args:
        key_name: Identifier for the key
        
    Returns:
        Private key as string or None if not found
    """
    # First check if key is directly in environment
    if "EPIC_PRIVATE_KEY" in os.environ:
        logger.info("Using private key from EPIC_PRIVATE_KEY environment variable")
        return os.environ["EPIC_PRIVATE_KEY"]
    
    # Next try file path from environment
    if "EPIC_PRIVATE_KEY_FILE" in os.environ:
        key_file = os.environ["EPIC_PRIVATE_KEY_FILE"]
        if os.path.exists(key_file):
            logger.info(f"Loading private key from {key_file}")
            try:
                with open(key_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading key file {key_file}: {e}")
                return None
    
    # Finally try default locations
    default_locations = [
        "auth/private_key.pem",
        "private_key.pem",
        os.path.expanduser("~/.fhir/private_key.pem")
    ]
    
    for loc in default_locations:
        if os.path.exists(loc):
            logger.info(f"Loading private key from {loc}")
            try:
                with open(loc, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading key file {loc}: {e}")
                continue
    
    logger.error("No private key found")
    return None

def get_client_credentials() -> Dict[str, str]:
    """
    Get client credentials for API authentication.
    
    Returns:
        Dictionary with client_id and private_key
    """
    credentials = {}
    
    # Get client ID
    if IN_FOUNDRY:
        # In Foundry, get from secret store
        client_id = _get_foundry_secret("epic_client_id")
    else:
        # In development, get from environment
        client_id = os.environ.get("EPIC_CLIENT_ID")
    
    if not client_id:
        logger.error("No client ID found")
    
    credentials["client_id"] = client_id
    
    # Get private key
    private_key = get_jwt_private_key()
    if not private_key:
        logger.error("No private key found")
    
    credentials["private_key"] = private_key
    
    return credentials 