#!/usr/bin/env python3
"""
Run data validation using Great Expectations.

This script runs data validation on FHIR data using Great Expectations
expectation suites and generates validation reports.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ge_installation() -> bool:
    """
    Check if Great Expectations is installed.
    
    Returns:
        True if Great Expectations is installed, False otherwise
    """
    try:
        import great_expectations
        logger.info(f"Great Expectations version {great_expectations.__version__} is installed")
        return True
    except ImportError:
        logger.error("Great Expectations is not installed")
        return False

def run_validation(
    project_dir: Path,
    data_dir: Path,
    resource_types: List[str],
    layer: str = "gold",
    generate_docs: bool = True
) -> Dict[str, bool]:
    """
    Run validation on FHIR data.
    
    Args:
        project_dir: Path to the project directory
        data_dir: Path to the data directory
        resource_types: List of FHIR resource types to validate
        layer: Data layer to validate (bronze, silver, gold)
        generate_docs: Whether to generate data docs
        
    Returns:
        Dictionary mapping resource types to validation results
    """
    try:
        # Import Great Expectations
        import great_expectations as ge
        from great_expectations.data_context import DataContext
        from great_expectations.checkpoint import SimpleCheckpoint
        
        # Load the context
        context = DataContext(str(project_dir / "great_expectations"))
        
        # Define the datasource name
        datasource_name = f"{layer}_datasource"
        
        # Get available data assets
        available_assets = context.get_available_data_asset_names(datasource_name)
        
        logger.info(f"Available data assets for {datasource_name}: {available_assets}")
        
        # Initialize results dictionary
        results = {}
        
        # Run validation for each resource type
        for resource_type in resource_types:
            resource_type_lower = resource_type.lower()
            suite_name = f"{resource_type_lower}_suite"
            
            # Check if the expectation suite exists
            try:
                suite = context.get_expectation_suite(suite_name)
                logger.info(f"Found expectation suite: {suite_name}")
            except Exception as e:
                logger.warning(f"Expectation suite {suite_name} not found: {e}")
                results[resource_type] = False
                continue
            
            # Look for data assets matching the resource type
            matching_assets = []
            for connector_name, asset_names in available_assets.items():
                for asset_name in asset_names:
                    if resource_type_lower in asset_name.lower():
                        matching_assets.append((connector_name, asset_name))
            
            if not matching_assets:
                logger.warning(f"No data assets found for {resource_type}")
                results[resource_type] = False
                continue
            
            # Run validation for each matching asset
            resource_valid = True
            for connector_name, asset_name in matching_assets:
                batch_request = {
                    "datasource_name": datasource_name,
                    "data_connector_name": connector_name,
                    "data_asset_name": asset_name,
                    "batch_spec_passthrough": {
                        "reader_method": "read_parquet" if layer in ["silver", "gold"] else "read_json"
                    }
                }
                
                # Create a checkpoint for this validation
                checkpoint_name = f"{resource_type_lower}_{layer}_checkpoint"
                checkpoint_config = {
                    "name": checkpoint_name,
                    "config_version": 1.0,
                    "class_name": "SimpleCheckpoint",
                    "run_name_template": "%Y%m%d-%H%M%S-" + resource_type_lower,
                    "validations": [
                        {
                            "batch_request": batch_request,
                            "expectation_suite_name": suite_name
                        }
                    ]
                }
                
                # Try to run the checkpoint
                try:
                    checkpoint = SimpleCheckpoint(
                        name=checkpoint_name,
                        data_context=context,
                        **checkpoint_config
                    )
                    result = checkpoint.run()
                    
                    # Check if validation passed
                    validation_success = result.success
                    if not validation_success:
                        resource_valid = False
                        logger.warning(f"Validation failed for {asset_name}")
                    else:
                        logger.info(f"Validation passed for {asset_name}")
                    
                except Exception as e:
                    logger.error(f"Error running validation for {asset_name}: {e}")
                    resource_valid = False
            
            results[resource_type] = resource_valid
        
        # Generate data docs if requested
        if generate_docs:
            try:
                context.build_data_docs()
                site_urls = context.get_docs_sites_urls()
                logger.info(f"Data docs generated at: {site_urls}")
            except Exception as e:
                logger.error(f"Error generating data docs: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running validation: {e}")
        return {rt: False for rt in resource_types}

def main():
    parser = argparse.ArgumentParser(description="Run data validation on FHIR data")
    parser.add_argument(
        "--project-dir", 
        help="Project directory", 
        default="."
    )
    parser.add_argument(
        "--data-dir", 
        help="Data directory", 
        default="output"
    )
    parser.add_argument(
        "--resources", 
        nargs="+", 
        help="FHIR resource types to validate",
        default=["Patient", "Observation", "Encounter"]
    )
    parser.add_argument(
        "--layer", 
        help="Data layer to validate (bronze, silver, gold)",
        default="gold",
        choices=["bronze", "silver", "gold"]
    )
    parser.add_argument(
        "--no-docs", 
        action="store_true", 
        help="Do not generate data docs"
    )
    
    args = parser.parse_args()
    
    # Convert paths to absolute paths
    project_dir = Path(args.project_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    
    # Check if Great Expectations is installed
    if not check_ge_installation():
        logger.error("Great Expectations is not installed. Please install it first.")
        sys.exit(1)
    
    # Check if Great Expectations project exists
    ge_dir = project_dir / "great_expectations"
    if not ge_dir.exists():
        logger.error(
            f"Great Expectations project directory {ge_dir} not found. "
            "Please run setup_great_expectations.py first."
        )
        sys.exit(1)
    
    # Run validation
    results = run_validation(
        project_dir=project_dir,
        data_dir=data_dir,
        resource_types=args.resources,
        layer=args.layer,
        generate_docs=not args.no_docs
    )
    
    # Print validation results
    logger.info("Validation results:")
    for resource_type, is_valid in results.items():
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {resource_type}: {status}")
    
    # Set exit code based on validation results
    if all(results.values()):
        logger.info("All validations passed!")
        sys.exit(0)
    else:
        logger.error("Some validations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 