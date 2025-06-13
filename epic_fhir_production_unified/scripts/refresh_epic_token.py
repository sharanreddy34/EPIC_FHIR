#!/usr/bin/env python3
"""
Epic FHIR API Token Refresh Script

This script refreshes the Epic FHIR API access token using JWT authentication.
It uses the same authentication mechanism as the main FHIR pipeline.

Usage:
    python refresh_epic_token.py [--debug] [--token-file TOKEN_FILE]

Example:
    python refresh_epic_token.py --debug
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the token refresher
from fhir_pipeline.auth.token_refresher import TokenRefresher

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
        # Also set debug level for other modules
        logging.getLogger("fhir_pipeline").setLevel(logging.DEBUG)


def main():
    """Main entry point for token refresh."""
    parser = argparse.ArgumentParser(description="Refresh Epic FHIR API Token")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--token-file", default="epic_token.json", help="Path to save token")
    parser.add_argument("--token-url", default="https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token", 
                     help="EPIC token endpoint URL")
    parser.add_argument("--jwks-url", default="https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json",
                     help="URL to JWKS file")
    parser.add_argument("--client-id", help="Override client ID from environment")
    parser.add_argument("--private-key-file", help="Path to private key file")
    
    args = parser.parse_args()
    
    # Configure logging
    setup_debug_logging(args.debug)
    
    # Load private key from file if specified
    private_key = None
    if args.private_key_file:
        try:
            with open(args.private_key_file, 'r') as f:
                private_key = f.read()
            logger.info(f"Loaded private key from {args.private_key_file}")
        except Exception as e:
            logger.error(f"Error loading private key from {args.private_key_file}: {e}")
            return 1
    
    # Create token refresher
    logger.info("Initializing token refresher")
    token_refresher = TokenRefresher(
        client_id=args.client_id,
        private_key=private_key,
        token_url=args.token_url,
        jwks_url=args.jwks_url,
        debug_mode=args.debug,
        token_file_path=args.token_file
    )
    
    # Get access token
    try:
        logger.info("Requesting access token")
        access_token = token_refresher.get_access_token()
        logger.info(f"Successfully obtained access token")
        
        # Get token data
        token_data = token_refresher.token_data
        if token_data:
            # Print token information
            token_type = token_data.get("token_type", "unknown")
            expires_in = token_data.get("expires_in", "unknown")
            scope = token_data.get("scope", "unknown")
            
            logger.info(f"Token type: {token_type}")
            logger.info(f"Expires in: {expires_in} seconds")
            logger.info(f"Scope: {scope}")
            logger.info(f"Token saved to: {args.token_file}")
            
            # Print the first part of the token for verification
            if args.debug and access_token:
                token_preview = access_token[:20] + "..." if len(access_token) > 20 else access_token
                logger.debug(f"Token preview: {token_preview}")
            
            return 0
        else:
            logger.error("Failed to obtain token data")
            return 1
            
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        if args.debug:
            import traceback
            logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main()) 