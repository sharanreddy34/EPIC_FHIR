"""
Command-line interface for running the Epic FHIR pipeline.

This module provides a command-line interface for running the full Epic FHIR
pipeline, from data extraction to validation.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from epic_fhir_integration.api_clients.fhir_client import create_fhir_client
from epic_fhir_integration.api_clients.jwt_auth import get_or_refresh_token
from epic_fhir_integration.bronze.resource_extractor import extract_all_resources
from epic_fhir_integration.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


def run_bronze_extraction(resource_types=None, max_pages=50):
    """Run bronze layer extraction for the specified resource types.
    
    Args:
        resource_types: List of resource types to extract. If None, uses defaults.
        max_pages: Maximum number of pages to extract per resource type.
        
    Returns:
        Dict mapping resource types to lists of resources.
    """
    logger.info("Starting Bronze extraction", resource_types=resource_types, max_pages=max_pages)
    
    # Create FHIR client
    client = create_fhir_client()
    
    # Extract resources
    start_time = time.time()
    resources = extract_all_resources(
        client=client,
        resource_types=resource_types,
        max_pages=max_pages,
    )
    
    duration = time.time() - start_time
    total_resources = sum(len(res_list) for res_list in resources.values())
    
    logger.info("Completed Bronze extraction",
               duration=f"{duration:.2f}s",
               resource_count=total_resources)
    
    # Report counts by resource type
    for resource_type, res_list in resources.items():
        logger.info(f"Extracted {resource_type}", count=len(res_list))
    
    return resources


def main():
    """Main entry point for the pipeline CLI."""
    parser = argparse.ArgumentParser(description="Run the Epic FHIR pipeline")
    
    parser.add_argument(
        "--resources", "-r",
        help="Comma-separated list of FHIR resource types to extract",
        default="Patient,Encounter,Condition,Observation,MedicationRequest"
    )
    
    parser.add_argument(
        "--max-pages", "-m",
        help="Maximum number of pages to extract per resource type",
        type=int,
        default=50
    )
    
    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose logging",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger("epic_fhir_integration").setLevel(logging.DEBUG)
    
    # Parse resource types
    resource_types = [r.strip() for r in args.resources.split(",") if r.strip()]
    
    try:
        # Run bronze extraction
        resources = run_bronze_extraction(
            resource_types=resource_types,
            max_pages=args.max_pages
        )
        
        # Success
        logger.info("Pipeline completed successfully")
        return 0
        
    except Exception as e:
        logger.error("Pipeline failed", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 