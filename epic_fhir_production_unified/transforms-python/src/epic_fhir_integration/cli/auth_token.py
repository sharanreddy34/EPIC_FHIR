"""
Command-line interface for getting Epic FHIR API authentication tokens.

This module provides a command-line interface for generating and retrieving
JWT authentication tokens for the Epic FHIR API.
"""

import argparse
import json
import sys

from epic_fhir_integration.api_clients.jwt_auth import (
    build_jwt, exchange_for_access_token, get_or_refresh_token
)
from epic_fhir_integration.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


def main():
    """Main entry point for the auth token CLI."""
    parser = argparse.ArgumentParser(description="Get Epic FHIR API authentication token")
    
    parser.add_argument(
        "--jwt-only",
        help="Only output the JWT, don't exchange for access token",
        action="store_true"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output format (json or text)",
        choices=["json", "text"],
        default="text"
    )
    
    args = parser.parse_args()
    
    try:
        # Get JWT
        jwt_token = build_jwt()
        
        if args.jwt_only:
            # Only output JWT
            if args.output == "json":
                print(json.dumps({"jwt": jwt_token}))
            else:
                print(jwt_token)
            return 0
        
        # Exchange for access token
        token_data = exchange_for_access_token(jwt_token)
        
        # Output token data
        if args.output == "json":
            print(json.dumps(token_data, indent=2))
        else:
            print(f"Access Token: {token_data['access_token']}")
            print(f"Token Type: {token_data.get('token_type', 'Bearer')}")
            print(f"Expires In: {token_data.get('expires_in', 'Unknown')} seconds")
            
            # Print additional fields if present
            for key, value in token_data.items():
                if key not in ["access_token", "token_type", "expires_in", "expiration_timestamp"]:
                    print(f"{key}: {value}")
        
        return 0
        
    except Exception as e:
        logger.error("Failed to get auth token", error=str(e), exc_info=True)
        
        if args.output == "json":
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        
        return 1


if __name__ == "__main__":
    sys.exit(main()) 