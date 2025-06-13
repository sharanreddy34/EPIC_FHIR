#!/usr/bin/env python
"""
Full FHIR Pipeline CLI.

This module provides a command-line interface for running the full FHIR pipeline,
including extraction, Bronze to Silver, and Silver to Gold transformations.
"""

import argparse
import logging
import sys
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional

from pyspark.sql import SparkSession

from epic_fhir_integration.extract.extractor import extract_resources
from epic_fhir_integration.transform.bronze_to_silver import transform_all_bronze_to_silver
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
        logging.FileHandler("debug_pipeline.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Run the full FHIR pipeline")
    parser.add_argument(
        "--resources",
        nargs="+",
        help="FHIR resource types to process (e.g., Patient Observation)",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--output-dir",
        help="Base directory for output",
        default="output",
    )
    parser.add_argument(
        "--start-step",
        choices=["extract", "bronze", "silver"],
        default="extract",
        help="Start the pipeline from this step",
    )
    parser.add_argument(
        "--end-step",
        choices=["extract", "bronze", "silver", "gold"],
        default="gold",
        help="End the pipeline at this step",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate schemas after transformations",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of calling the API",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    
    return parser.parse_args()


def load_config(config_path: Optional[str]) -> Dict:
    """Load pipeline configuration from a YAML file.
    
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


def run_extract(
    resource_types: List[str],
    output_dir: str,
    resource_params: Dict,
    mock: bool = False,
) -> Dict[str, Path]:
    """Run the FHIR resource extraction step.
    
    Args:
        resource_types: List of FHIR resource types to extract.
        output_dir: Base directory for output.
        resource_params: Parameters for each resource type.
        mock: Whether to use mock data instead of calling the API.
        
    Returns:
        Dictionary mapping resource types to output file paths.
    """
    logger.info("Starting FHIR resource extraction step")
    
    if mock:
        logger.info("Using mock data instead of calling the API")
        # In a real implementation, this would generate mock data files
        # For now, just return empty dict
        return {}
    
    # Extract resources
    output_files = extract_resources(
        resource_types=resource_types,
        output_base_dir=output_dir,
        params=resource_params,
    )
    
    logger.info("FHIR resource extraction step completed")
    return output_files


def run_bronze_to_silver(
    resource_types: List[str],
    output_dir: str,
    spark: SparkSession,
) -> Dict[str, Path]:
    """Run the Bronze to Silver transformation step.
    
    Args:
        resource_types: List of FHIR resource types to transform.
        output_dir: Base directory for output.
        spark: Spark session.
        
    Returns:
        Dictionary mapping resource types to output paths.
    """
    logger.info("Starting Bronze to Silver transformation step")
    
    # Transform resources
    output_paths = transform_all_bronze_to_silver(
        resource_types=resource_types,
        bronze_base_path=output_dir,
        silver_base_path=output_dir,
        spark=spark,
    )
    
    logger.info("Bronze to Silver transformation step completed")
    return output_paths


def run_silver_to_gold(
    resource_types: List[str],
    output_dir: str,
    spark: SparkSession,
    validate: bool = False,
) -> Dict[str, Path]:
    """Run the Silver to Gold transformation step.
    
    Args:
        resource_types: List of FHIR resource types to transform.
        output_dir: Base directory for output.
        spark: Spark session.
        validate: Whether to validate schemas after transformation.
        
    Returns:
        Dictionary mapping resource types to output paths.
    """
    logger.info("Starting Silver to Gold transformation step")
    
    # Transform resources
    output_paths = transform_all_silver_to_gold(
        resource_types=resource_types,
        silver_base_path=output_dir,
        gold_base_path=output_dir,
        spark=spark,
    )
    
    # Validate schemas if requested
    if validate:
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
    
    logger.info("Silver to Gold transformation step completed")
    return output_paths


def run_pipeline(args: argparse.Namespace) -> None:
    """Run the full FHIR pipeline.
    
    Args:
        args: Command-line arguments.
    """
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    resource_params = config.get("resource_params", {})
    
    # Default resources if not specified
    resource_types = args.resources or config.get("resources", ["Patient", "Observation", "Encounter"])
    
    # Create Spark session if needed
    spark = None
    if args.start_step in ["bronze", "silver"] or args.end_step in ["bronze", "silver", "gold"]:
        spark = SparkSession.builder \
            .appName("FHIR Pipeline") \
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
            .getOrCreate()
    
    # Track pipeline start time
    start_time = time.time()
    
    try:
        # Run extraction step if needed
        if args.start_step == "extract" and args.end_step in ["extract", "bronze", "silver", "gold"]:
            bronze_paths = run_extract(
                resource_types=resource_types,
                output_dir=args.output_dir,
                resource_params=resource_params,
                mock=args.mock,
            )
        
        # Run Bronze to Silver step if needed
        if args.start_step in ["extract", "bronze"] and args.end_step in ["bronze", "silver", "gold"]:
            silver_paths = run_bronze_to_silver(
                resource_types=resource_types,
                output_dir=args.output_dir,
                spark=spark,
            )
        
        # Run Silver to Gold step if needed
        if args.start_step in ["extract", "bronze", "silver"] and args.end_step in ["silver", "gold"]:
            gold_paths = run_silver_to_gold(
                resource_types=resource_types,
                output_dir=args.output_dir,
                spark=spark,
                validate=args.validate,
            )
        
        # Calculate and log pipeline duration
        duration = time.time() - start_time
        logger.info(f"Full FHIR pipeline completed successfully in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error during FHIR pipeline: {e}")
        raise


def main() -> None:
    """Main entry point for the full FHIR pipeline CLI."""
    try:
        args = parse_args()
        run_pipeline(args)
    except Exception as e:
        logger.error(f"FHIR pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 