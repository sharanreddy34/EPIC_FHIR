#!/usr/bin/env python
"""
Bronze to Silver Transformation CLI.

This module provides a command-line interface for transforming FHIR resources
from the Bronze layer to the Silver layer.
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from pyspark.sql import SparkSession

from epic_fhir_integration.constants import BRONZE, SILVER
from epic_fhir_integration.transform.bronze_to_silver import transform_all_bronze_to_silver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_transform.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Transform FHIR resources from Bronze to Silver")
    parser.add_argument(
        "--resources",
        nargs="+",
        help="FHIR resource types to transform (e.g., Patient Observation)",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--bronze-dir",
        help="Base directory for Bronze input (defaults to DATA_ROOT/bronze)",
        default=str(BRONZE),
    )
    parser.add_argument(
        "--silver-dir",
        help="Base directory for Silver output (defaults to DATA_ROOT/silver)",
        default=str(SILVER),
    )
    # Hidden aliases to maintain compatibility with docs if they pass --input-uri / --output-uri
    parser.add_argument("--input-uri", help=argparse.SUPPRESS)
    parser.add_argument("--output-uri", help=argparse.SUPPRESS)
    
    return parser.parse_args()


def load_config(config_path: Optional[str]) -> Dict:
    """Load transformation configuration from a YAML file.
    
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


def run_transformation(args: argparse.Namespace) -> None:
    """Run the Bronze to Silver transformation process.
    
    Args:
        args: Command-line arguments.
    """
    # Map alias parameters if provided
    if args.input_uri:
        args.bronze_dir = args.input_uri
    if args.output_uri:
        args.silver_dir = args.output_uri

    # Ensure directories exist
    Path(args.silver_dir).mkdir(parents=True, exist_ok=True)

    # Load configuration
    config = load_config(args.config)
    
    # Default resources if not specified
    resource_types = args.resources or config.get("resources", ["Patient", "Observation", "Encounter"])
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("FHIR Bronze to Silver") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    # Run transformation
    logger.info(f"Transforming resources from Bronze to Silver: {', '.join(resource_types)}")
    output_paths = transform_all_bronze_to_silver(
        resource_types=resource_types,
        bronze_base_path=args.bronze_dir,
        silver_base_path=args.silver_dir,
        spark=spark,
    )
    
    # Log output paths
    for resource_type, path in output_paths.items():
        logger.info(f"Transformed {resource_type} from Bronze to Silver: {path}")


def main() -> None:
    """Main entry point for the Bronze to Silver transformation CLI."""
    try:
        args = parse_args()
        run_transformation(args)
        logger.info("Bronze to Silver transformation completed successfully")
    except Exception as e:
        logger.error(f"Error during Bronze to Silver transformation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 