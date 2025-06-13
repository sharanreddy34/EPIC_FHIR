#!/usr/bin/env python3
"""
EPIC FHIR Token Refresh Script

This script generates a new access token for the EPIC FHIR API using the JWT client
credentials flow and saves it to epic_token.json.
"""

import sys
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to refresh the EPIC access token"""
    parser = argparse.ArgumentParser(description="Refresh EPIC FHIR API access token")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        # Use the new auth module
        from auth.setup_epic_auth import refresh_token
        
        logger.info("Requesting access token")
        token_data = refresh_token()
        
        if token_data:
            logger.info(f"Successfully obtained token: expires in {token_data.get('expires_in', 'unknown')} seconds")
            logger.info("Token saved to epic_token.json")
            return 0
        else:
            logger.error("Failed to obtain a valid token")
            return 1
            
    except ImportError:
        logger.error("Could not import auth.setup_epic_auth module")
        logger.error("Please ensure the auth/setup_epic_auth.py file exists")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 