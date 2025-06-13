#!/usr/bin/env python3
"""
Command-line tool to get an Epic FHIR access token.
"""

import argparse
import logging
import sys
from pathlib import Path

from epic_fhir_integration.auth.custom_auth import get_access_token

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the token CLI."""
    parser = argparse.ArgumentParser(description="Get Epic FHIR access token")
    parser.add_argument("--key", help="Path to private key file")
    parser.add_argument("--client-id", help="Epic client ID")
    parser.add_argument("--token-url", help="Epic token endpoint URL")
    parser.add_argument("--scope", default="system/*.read", help="Requested scope")
    parser.add_argument("--output", help="Output file for the token")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    
    args = parser.parse_args()
    
    logger.info("Starting Epic FHIR token acquisition")
    
    # Use the provided key path or look for a key in the default location
    key_path = args.key
    if not key_path:
        # Check different potential locations
        potential_paths = [
            Path("epic_private_key.pem"),  # Current directory
            Path(Path.home(), ".config", "epic_fhir", "epic_private_key.pem"),  # User config
            Path(__file__).resolve().parent.parent.parent / "secrets" / "epic_private_key.pem",  # Package secrets
        ]
        
        for path in potential_paths:
            if path.exists():
                key_path = path
                logger.info(f"Using key from: {key_path}")
                break
    
    # Get the token
    try:
        token_data = get_access_token(
            private_key_path=key_path,
            client_id=args.client_id,
            token_url=args.token_url,
            scope=args.scope,
            verbose=args.verbose
        )
        
        if token_data:
            # If output file is specified, write the token to it
            if args.output:
                import json
                with open(args.output, "w") as f:
                    json.dump(token_data, f, indent=2)
                logger.info(f"Token written to {args.output}")
            
            # Print the token for use in scripts
            logger.info(f"Token type: {token_data.get('token_type', 'Bearer')}")
            logger.info(f"Token valid for {token_data.get('expires_in', 'unknown')} seconds")
            
            if args.verbose:
                logger.info(f"Access token: {token_data.get('access_token')[:30]}...")
            
            return 0
        else:
            logger.error("Failed to obtain token")
            return 1
    except Exception as e:
        logger.error(f"Error obtaining token: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 