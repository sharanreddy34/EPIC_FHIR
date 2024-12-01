#!/usr/bin/env python
"""
Silver to Gold Transformation CLI.

This module provides a command-line interface for transforming FHIR resources
from the Silver layer to the Gold layer.
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from pyspark.sql import SparkSession

from epic_fhir_integration.constants import SILVER, GOLD
from epic_fhir_integration.transform.silver_to_gold import (
    transform_all_silver_to_gold,
    validate_schemas,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_gold.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Transform FHIR resources from Silver to Gold")
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
        "--silver-dir",
        help="Base directory for Silver input (defaults to DATA_ROOT/silver)",
        default=str(SILVER),
    )
    parser.add_argument(
        "--gold-dir",
        help="Base directory for Gold output (defaults to DATA_ROOT/gold)",
        default=str(GOLD),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate Gold layer schemas after transformation",
    )
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
    """Run the Silver to Gold transformation process.
    
    Args:
        args: Command-line arguments.
    """
    # Map alias parameters if provided
    if args.input_uri:
        args.silver_dir = args.input_uri
    if args.output_uri:
        args.gold_dir = args.output_uri

    Path(args.gold_dir).mkdir(parents=True, exist_ok=True)

    # Load configuration
    config = load_config(args.config)
    
    # Default resources if not specified
    resource_types = args.resources or config.get("resources", ["Patient", "Observation", "Encounter"])
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("FHIR Silver to Gold") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    # Run transformation
    logger.info(f"Transforming resources from Silver to Gold: {', '.join(resource_types)}")
    output_paths = transform_all_silver_to_gold(
        resource_types=resource_types,
        silver_base_path=args.silver_dir,
        gold_base_path=args.gold_dir,
        spark=spark,
    )
    
    # Validate schemas if requested
    if args.validate:
        logger.info("Validating Gold layer schemas...")
        validation_results = validate_schemas(output_paths, spark)
        
        # Log validation results
        all_valid = True
        for resource_type, is_valid in validation_results.items():
            status = "VALID" if is_valid else "INVALID"
            logger.info(f"Schema validation for {resource_type}: {status}")
            if not is_valid:
                all_valid = False
        
        if not all_valid:
            logger.warning("Some schema validations failed")
    
    # Log output paths
    for resource_type, path in output_paths.items():
        logger.info(f"Transformed {resource_type} from Silver to Gold: {path}")


def main() -> None:
    """Main entry point for the Silver to Gold transformation CLI."""
    try:
        args = parse_args()
        run_transformation(args)
        logger.info("Silver to Gold transformation completed successfully")
    except Exception as e:
        logger.error(f"Error during Silver to Gold transformation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 