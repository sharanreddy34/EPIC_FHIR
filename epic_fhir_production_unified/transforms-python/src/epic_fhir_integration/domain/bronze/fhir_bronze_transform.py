"""
Generic FHIR Bronze transform for Palantir Foundry.

This module provides a configurable transform for ingesting any FHIR resource type 
from the Epic API and writing it to a Bronze dataset in Foundry.

NOTE: This transform is not meant to be used directly, but through the resource-specific
wrapper modules that provide static Output paths.
"""

from transforms.api import transform_df, incremental, Output, Config
import pyspark.sql.functions as F
import os

from epic_fhir_integration.api_clients.fhir_client import create_fhir_client
from epic_fhir_integration.bronze.resource_extractor import (
    extract_resource, resources_to_spark_df, last_watermark, find_max_updated_time
)
from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


@incremental(snapshot_inputs=True)
@transform_df(
    Output(""),  # Will be overridden by resource-specific wrappers
    Config("resource_type", ""),
    Config("max_pages", 50),
    Config("batch_size", 100),
)
def compute(ctx, output, resource_type, max_pages, batch_size):
    """Extract FHIR resources from Epic API and write to Bronze dataset.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        resource_type: FHIR resource type to extract.
        max_pages: Maximum number of pages to retrieve.
        batch_size: Batch size for API requests.
    """
    if not resource_type:
        raise ValueError("resource_type config parameter is required")
    
    # Get last watermark for incremental load
    watermark = last_watermark(ctx)
    logger.info(f"Starting {resource_type} bronze extraction", 
               resource_type=resource_type,
               watermark=watermark)
    
    # Create FHIR client - now using Foundry secret manager if available
    client = create_fhir_client()
    
    # Extract resources
    resources = extract_resource(
        client=client,
        resource_type=resource_type,
        params={"_count": batch_size},
        max_pages=max_pages,
        last_updated_since=watermark,
    )
    
    # Convert to Spark DataFrame
    spark = ctx.spark_session
    resources_df = resources_to_spark_df(resources, spark)
    
    # Find the latest update timestamp for the next watermark
    if resources:
        next_watermark = find_max_updated_time(resources)
        if next_watermark:
            logger.info("Setting next watermark", watermark=next_watermark)
            ctx.set_next_watermark(next_watermark)
    
    # Write to output with partitioning
    logger.info(f"Writing {resource_type} bronze dataset", 
               resource_type=resource_type,
               count=resources_df.count())
    
    resources_df.write.partitionBy("ingest_date").format("delta").mode("append").save(output.uri) 