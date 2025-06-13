#!/usr/bin/env python3
"""
CLI entry point for FHIR pipeline.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from fhir_pipeline.utils.logging import get_logger
from fhir_pipeline.config import load_settings, Settings
from fhir_pipeline.io.fhir_client import FHIRClient
from fhir_pipeline.auth.jwt_auth import create_token_provider


def get_token_provider_for_settings(settings: Settings) -> Callable[[], str]:
    """
    Get a token provider function for the FHIR client based on settings.
    
    Args:
        settings: Settings object
        
    Returns:
        Token provider function
    """
    # If in mock mode, return a mock token provider
    if settings.use_mock:
        def mock_token_provider() -> str:
            return "mock-token"
        return mock_token_provider
    
    # For real API calls, use JWT authentication
    return create_token_provider(
        client_id=settings.api.client_id,
        environment=settings.api.environment,
        debug_mode=settings.pipeline.debug
    )


def extract_patient_data(
    patient_id: str,
    resource_types: List[str],
    settings: Settings,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Extract patient data using the FHIR client.
    
    Args:
        patient_id: Patient ID
        resource_types: Resource types to extract
        settings: Settings object
        output_dir: Output directory
        
    Returns:
        Dict of results
    """
    logger = get_logger("fhir_pipeline.extract", debug=settings.pipeline.debug)
    
    # Use the output directory from settings if not specified
    if output_dir is None:
        output_dir = settings.pipeline.patient_data_dir / patient_id
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting data for patient {patient_id} to {output_dir}")
    
    # Create FHIR client with JWT-based authentication
    client = FHIRClient(
        settings.api.base_url,
        get_token_provider_for_settings(settings),
        debug_mode=settings.pipeline.debug,
        verify_ssl=settings.api.verify_ssl,
        timeout=settings.api.timeout
    )
    
    start_time = time.time()
    
    # Test connection
    logger.info(f"Testing FHIR connection to {settings.api.base_url}...")
    if not client.validate_connection():
        logger.error("Failed to connect to FHIR server")
        return {"success": False, "error": "Failed to connect to FHIR server"}
    
    logger.info(f"Connection successful in {time.time() - start_time:.2f}s")
    
    # Extract resources in parallel
    logger.info(f"Extracting {len(resource_types)} resource types in parallel: {', '.join(resource_types)}")
    
    extraction_start = time.time()
    results = client.extract_patient_resources_parallel(
        patient_id,
        resource_types
    )
    
    extraction_time = time.time() - extraction_start
    logger.info(f"Extracted all resources in {extraction_time:.2f}s")
    
    # Save results to files
    total_resources = 0
    total_bundles = 0
    
    for resource_type, bundles in results.items():
        if not bundles:
            logger.warning(f"No {resource_type} bundles received")
            continue
            
        # Create directory for this resource
        resource_dir = output_dir / resource_type
        resource_dir.mkdir(exist_ok=True)
        
        # Save each bundle
        bundle_count = len(bundles)
        entry_count = sum(len(bundle.get("entry", [])) for bundle in bundles)
        
        for i, bundle in enumerate(bundles):
            # Create filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{i}.json"
            
            # Add metadata
            bundle_metadata = {
                "resource_type": resource_type,
                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "page_number": i,
                "entry_count": len(bundle.get("entry", [])),
            }
            
            bundle_with_metadata = {
                "metadata": bundle_metadata,
                "bundle": bundle,
            }
            
            # Save to file
            file_path = resource_dir / filename
            with open(file_path, 'w') as f:
                json.dump(bundle_with_metadata, f, indent=2)
                
        logger.info(f"Saved {bundle_count} {resource_type} bundles with {entry_count} entries")
        total_resources += entry_count
        total_bundles += bundle_count
    
    total_time = time.time() - start_time
    
    # Return summary
    result = {
        "success": True,
        "patient_id": patient_id,
        "resources_extracted": total_resources,
        "bundles_extracted": total_bundles,
        "extraction_time_seconds": extraction_time,
        "total_time_seconds": total_time,
        "output_directory": str(output_dir),
        "api": {
            "environment": settings.api.environment,
            "base_url": settings.api.base_url,
            "client_id": settings.api.client_id,
        },
        "resource_types": {
            rt: {
                "bundles": len(bundles),
                "entries": sum(len(bundle.get("entry", [])) for bundle in bundles)
            }
            for rt, bundles in results.items() if bundles
        },
        "metrics": client.get_metrics()
    }
    
    # Write summary to file
    summary_path = output_dir / "extraction_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Extraction complete. Extracted {total_resources} resources in {total_bundles} bundles")
    logger.info(f"Total time: {total_time:.2f}s, Extraction time: {extraction_time:.2f}s")
    logger.info(f"Summary written to {summary_path}")
    
    return result


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="FHIR Pipeline Command Line Interface")
    
    # Global options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--mock", action="store_true", help="Use mock mode")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--environment", choices=["production", "non-production"], 
                       default="non-production", help="API environment to use")
    parser.add_argument("--private-key", help="Path to private key file for JWT authentication")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract patient data")
    extract_parser.add_argument("--patient-id", required=True, help="Patient ID to extract")
    extract_parser.add_argument("--resources", default="Patient,Encounter,Observation,Condition,MedicationRequest",
                              help="Comma-separated list of resource types to extract")
    
    # Parse args
    args = parser.parse_args()
    
    # No command specified
    if not args.command:
        parser.print_help()
        return
    
    # Load settings
    try:
        settings = load_settings(
            mock_mode=args.mock,
            debug=args.debug,
            output_dir=args.output_dir,
            environment=args.environment
        )
        
        # Override private key path if specified
        if args.private_key:
            os.environ["EPIC_PRIVATE_KEY_PATH"] = args.private_key
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        return 1
    
    # Execute command
    if args.command == "extract":
        # Split resources
        resource_types = args.resources.split(",")
        
        # Run extraction
        result = extract_patient_data(
            args.patient_id,
            resource_types,
            settings
        )
        
        if not result.get("success", False):
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 