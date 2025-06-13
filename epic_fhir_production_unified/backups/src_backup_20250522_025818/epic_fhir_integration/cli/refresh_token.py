#!/usr/bin/env python
"""
Epic FHIR Token Refresh CLI.

This module provides a command-line interface for refreshing the Epic FHIR API access token.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from epic_fhir_integration.auth.jwt_auth import get_or_refresh_token, get_token_with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Refresh Epic FHIR API access token")
    parser.add_argument(
        "--token-file",
        help="Name of the token file in the secrets directory",
        default="epic_token.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force token refresh even if current token is still valid",
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Use the retry mechanism with exponential backoff",
    )
    
    return parser.parse_args()


def run_token_refresh(args: argparse.Namespace) -> None:
    """Run the token refresh process.
    
    Args:
        args: Command-line arguments.
    """
    logger.info("Starting Epic FHIR token refresh")
    
    try:
        if args.retry:
            # Use the retry mechanism
            token = get_token_with_retry()
            logger.info("Successfully refreshed token with retry mechanism")
        else:
            # Use the standard refresh mechanism
            # When force=True, it will create a new token regardless of current token validity
            if args.force:
                # Simulate token_data with expired timestamp to force refresh
                from epic_fhir_integration.security.secret_store import save_secret
                save_secret(args.token_file, {"expiration_timestamp": 0})
            
            token = get_or_refresh_token(args.token_file)
            logger.info("Successfully refreshed token")
        
        # Only print first few characters for security
        if token:
            token_preview = token[:10] + "..." if len(token) > 10 else token
            logger.info(f"Token preview: {token_preview}")
    
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the token refresh CLI."""
    try:
        args = parse_args()
        run_token_refresh(args)
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 