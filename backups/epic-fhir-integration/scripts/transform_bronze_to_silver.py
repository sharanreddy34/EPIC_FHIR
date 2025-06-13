#!/usr/bin/env python3
"""
Transform Bronze to Silver Layer

This script transforms raw FHIR data from the bronze layer into normalized
data in the silver layer.

It reads the JSON-format FHIR bundles, extracts the resources, and writes
them to Parquet files for efficient processing.
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent dir to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_debug_logging(enable_debug: bool):
    """Configure debug logging."""
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        # Log to file
        debug_file = Path("debug_transform.log")
        file_handler = logging.FileHandler(debug_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled")

def read_bronze_resources(bronze_dir: Path, resource_type: str) -> List[Dict]:
    """
    Read all resource bundles of a given type from the bronze layer.
    
    Args:
        bronze_dir: Path to the bronze layer
        resource_type: Resource type to read
        
    Returns:
        List of extracted resources
    """
    logger.info(f"Reading {resource_type} resources from bronze layer")
    
    # Find resource directory
    resource_dir = bronze_dir / resource_type
    
    if not resource_dir.exists():
        logger.warning(f"No {resource_type} directory found in bronze layer")
        return []
    
    resources = []
    bundle_files = list(resource_dir.glob("*.json"))
    
    if not bundle_files:
        logger.warning(f"No {resource_type} bundles found")
        return []
    
    logger.debug(f"Found {len(bundle_files)} {resource_type} bundle files")
    
    # Process each bundle file
    for bundle_file in bundle_files:
        try:
            with open(bundle_file, 'r') as f:
                bundle_data = json.load(f)
                
            # Check if this is a valid bundle with metadata
            if "bundle" not in bundle_data or "entry" not in bundle_data["bundle"]:
                logger.warning(f"Invalid bundle in {bundle_file}")
                continue
                
            # Extract resources from bundle entries
            for entry in bundle_data["bundle"]["entry"]:
                if "resource" in entry and "resourceType" in entry["resource"]:
                    resources.append(entry["resource"])
                    
            logger.debug(f"Extracted {len(bundle_data['bundle']['entry'])} resources from {bundle_file}")
                    
        except Exception as e:
            logger.error(f"Error processing {bundle_file}: {str(e)}")
            if logger.level <= logging.DEBUG:
                import traceback
                logger.debug(f"Error details: {traceback.format_exc()}")
    
    logger.info(f"Extracted {len(resources)} {resource_type} resources")
    return resources

def flatten_resource(resource: Dict, prefix: str = "") -> Dict:
    """
    Flatten a nested FHIR resource for easier tabular storage.
    
    Args:
        resource: FHIR resource dictionary
        prefix: Prefix for nested keys
        
    Returns:
        Flattened dictionary
    """
    flattened = {}
    
    # Add fields to flattened dictionary
    for key, value in resource.items():
        # Add prefix to key
        flat_key = f"{prefix}{key}"
        
        # Handle different value types
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            nested = flatten_resource(value, f"{flat_key}.")
            flattened.update(nested)
        elif isinstance(value, list):
            # For lists, we take first item only for simplicity
            # Production code would handle arrays better
            if value and isinstance(value[0], dict):
                # Flatten first object in list
                nested = flatten_resource(value[0], f"{flat_key}.")
                flattened.update(nested)
            else:
                # For simple lists, join values
                flattened[flat_key] = ",".join(str(v) for v in value)
        else:
            # Simple value
            flattened[flat_key] = value
    
    return flattened

def transform_resources(resources: List[Dict]) -> pd.DataFrame:
    """
    Transform a list of resources into a pandas DataFrame.
    
    Args:
        resources: List of FHIR resources
        
    Returns:
        DataFrame of transformed resources
    """
    if not resources:
        logger.warning("No resources to transform")
        return pd.DataFrame()
    
    # Simple approach - flatten all resources
    flattened_resources = []
    
    for resource in resources:
        # Keep original resource as JSON
        flattened = {"resource_raw": json.dumps(resource)}
        
        # Add essential fields
        for key in ["id", "resourceType"]:
            if key in resource:
                flattened[key] = resource[key]
        
        # Add flattened fields
        flattened.update(flatten_resource(resource))
        flattened_resources.append(flattened)
    
    # Create DataFrame
    df = pd.DataFrame(flattened_resources)
    
    logger.info(f"Transformed {len(df)} resources into DataFrame with {len(df.columns)} columns")
    return df

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Transform bronze FHIR data to silver")
    parser.add_argument("--bronze-dir", required=True, help="Bronze layer directory")
    parser.add_argument("--silver-dir", required=True, help="Silver layer output directory")
    parser.add_argument("--resource-types", default="all", help="Comma-separated resource types or 'all'")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup debug logging if requested
    setup_debug_logging(args.debug)
    
    # Configure input/output directories
    bronze_dir = Path(args.bronze_dir)
    silver_dir = Path(args.silver_dir)
    
    # Make sure directories exist
    if not bronze_dir.exists() or not bronze_dir.is_dir():
        logger.error(f"Bronze directory {bronze_dir} does not exist")
        return 1
    
    silver_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine resource types to process
    if args.resource_types.lower() == 'all':
        # Look for all subdirectories in bronze layer
        bronze_fhir_dir = bronze_dir / "fhir_raw" if (bronze_dir / "fhir_raw").exists() else bronze_dir
        resource_types = [d.name for d in bronze_fhir_dir.iterdir() if d.is_dir()]
        logger.info(f"Found {len(resource_types)} resource types in bronze layer: {', '.join(resource_types)}")
    else:
        resource_types = args.resource_types.split(',')
        logger.info(f"Processing resource types: {', '.join(resource_types)}")
    
    # Process each resource type
    for resource_type in resource_types:
        bronze_fhir_dir = bronze_dir / "fhir_raw" if (bronze_dir / "fhir_raw").exists() else bronze_dir
        resources = read_bronze_resources(bronze_fhir_dir, resource_type)
        
        if not resources:
            logger.warning(f"No {resource_type} resources found to transform")
            continue
        
        # Transform resources to DataFrame
        df = transform_resources(resources)
        
        if df.empty:
            logger.warning(f"No {resource_type} resources transformed")
            continue
        
        # Create output directory
        silver_output_dir = silver_dir / "fhir_normalized"
        silver_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to Parquet
        silver_output_file = silver_output_dir / f"{resource_type.lower()}.parquet"
        df.to_parquet(silver_output_file, index=False)
        
        logger.info(f"Wrote {len(df)} {resource_type} resources to {silver_output_file}")
    
    logger.info("Bronze to Silver transformation complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 