"""
Generic FHIR Silver transform for Palantir Foundry.

This module provides a configurable transform for cleaning and conforming FHIR resources
from Bronze datasets using Pathling extract specifications.
"""

import os
from pathlib import Path
from typing import Optional

from pyspark.sql import DataFrame
from transforms.api import transform_df, incremental, Input, Output, Config

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


@incremental(snapshot_inputs=True)
@transform_df(
    Output("datasets.{resource_type}_Clean_Silver"),
    Input("datasets.{resource_type}_Raw_Bronze"),
    Config("resource_type", ""),
    Config("extract_spec", ""),
)
def compute(ctx, output, raw_bronze, resource_type, extract_spec):
    """Transform FHIR resources from Bronze to Silver using Pathling.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        raw_bronze: Input Bronze dataset.
        resource_type: FHIR resource type.
        extract_spec: Path to extract specification YAML file.
    """
    if not resource_type:
        raise ValueError("resource_type config parameter is required")
    
    logger.info(f"Starting {resource_type} silver transformation",
                resource_type=resource_type)
    
    # Import here to avoid initialization overhead if not needed
    from pathling import PathlingContext
    
    # Create Pathling context
    ctx_pathling = PathlingContext.create()
    
    # Read the Bronze dataset
    bronze_df = raw_bronze.dataframe()
    logger.info(f"Read {resource_type} bronze dataset", 
                resource_type=resource_type,
                count=bronze_df.count())
    
    # Convert JSON to FHIR resources using Pathling
    fhir_df = ctx_pathling.read.fhir(resource_type).json(bronze_df, column="json_data")
    
    # Determine the extract spec path
    if not extract_spec:
        # Default to package-relative path
        package_path = Path(__file__).parent
        default_spec = package_path / f"extract_specs/{resource_type}.yaml"
        extract_spec = str(default_spec)
    
    logger.info(f"Using extract specification", spec_path=extract_spec)
    
    # Extract data using the specification
    try:
        clean_df = ctx_pathling.extract_from_yaml(fhir_df, extract_spec)
        
        # Add ingest metadata columns from bronze
        if "ingest_timestamp" in bronze_df.columns and "ingest_date" in bronze_df.columns:
            # Join back to bronze to get the metadata columns
            clean_df = clean_df.join(
                bronze_df.select("json_data", "ingest_timestamp", "ingest_date"),
                clean_df["_fhir_source_row_id"] == bronze_df["_fhir_source_row_id"],
                "left"
            )
        
        # Write to output
        logger.info(f"Writing {resource_type} silver dataset", 
                    resource_type=resource_type,
                    count=clean_df.count())
        
        clean_df.write.format("delta").partitionBy("ingest_date").mode("overwrite").save(output.uri)
    except Exception as e:
        logger.error(f"Error extracting {resource_type} data", 
                     resource_type=resource_type,
                     error=str(e))
        raise 