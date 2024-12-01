#!/usr/bin/env python
"""
FHIR Resource Extraction CLI.

This module provides a command-line interface for extracting FHIR resources
from the Epic FHIR API.
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from epic_fhir_integration.extract.extractor import extract_resources
from epic_fhir_integration.constants import BRONZE, DATA_ROOT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_extract.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Extract FHIR resources from Epic API")
    parser.add_argument(
        "--resources",
        nargs="+",
        help="FHIR resource types to extract (e.g., Patient Observation)",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file with resource-specific parameters",
    )
    parser.add_argument(
        "--output-dir",
        help="Base directory for output (defaults to DATA_ROOT/bronze)",
        default=str(BRONZE),
    )
    parser.add_argument(
        "--output-uri",
        help=argparse.SUPPRESS,  # Hidden alias to maintain back-compat with docs
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        help="Maximum number of pages to retrieve per resource type",
    )
    parser.add_argument(
        "--total-limit",
        type=int,
        help="Maximum total number of resources to retrieve per resource type",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of calling the API",
    )
    
    return parser.parse_args()


def load_config(config_path: Optional[str]) -> Dict:
    """Load resource extraction configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Dictionary containing the configuration.
    """
    if not config_path:
        return {}
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        return config or {}
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        return {}


def run_extraction(args: argparse.Namespace) -> None:
    """Run the FHIR resource extraction process.
    
    Args:
        args: Command-line arguments.
    """
    # Ensure output directory exists inside container / local FS
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Load resource parameters from config file
    config = load_config(args.config)
    resource_params = config.get("resource_params", {})
    
    # Default resources if not specified
    resource_types = args.resources or config.get("resources", ["Patient", "Observation", "Encounter"])
    
    # Extract resources
    logger.info(f"Extracting resources: {', '.join(resource_types)}")
    
    # Handle mock mode
    if args.mock:
        logger.info("Using mock data instead of calling the API")
        # In a real implementation, this would use mock data
        # For now, just log and return
        logger.info("Mock extraction completed")
        return
    
    # Run extraction
    output_files = extract_resources(
        resource_types=resource_types,
        output_base_dir=args.output_dir,
        params=resource_params,
        page_limit=args.page_limit,
        total_limit=args.total_limit,
    )
    
    # Log output files
    for resource_type, file_path in output_files.items():
        logger.info(f"Extracted {resource_type} to {file_path}")


def main() -> None:
    """Main entry point for the FHIR resource extraction CLI."""
    try:
        args = parse_args()
        if args.output_uri:
            args.output_dir = args.output_uri
        run_extraction(args)
        logger.info("FHIR resource extraction completed successfully")
    except Exception as e:
        logger.error(f"Error during FHIR resource extraction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 