"""
Patient Bronze transform for Epic FHIR integration.

This module provides a transform for ingesting Patient resources from the Epic API
and writing them to a Bronze dataset in Foundry.
"""

from transforms.api import transform_df, incremental, Output, Config
import pyspark.sql.functions as F

from epic_fhir_integration.api_clients.fhir_client import create_fhir_client
from epic_fhir_integration.bronze.extractor import extract_patient_resources, resources_to_spark_df, last_watermark
from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


@incremental(snapshot_inputs=True)
@transform_df(
    Output("datasets.Patient_Raw_Bronze"),
    Config("max_pages", 50),
    Config("batch_size", 1000),
)
def compute(ctx, output, max_pages, batch_size):
    """Extract Patient resources from Epic FHIR API and write to Bronze dataset.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        max_pages: Maximum number of pages to retrieve.
        batch_size: Batch size for API requests.
    """
    # Get last watermark for incremental load
    watermark = last_watermark(ctx)
    logger.info("Starting Patient bronze extraction", watermark=watermark)
    
    # Create FHIR client
    client = create_fhir_client()
    
    # Extract Patient resources
    patients = extract_patient_resources(
        client=client,
        params={"_count": batch_size},
        max_pages=max_pages,
        last_updated_since=watermark,
    )
    
    # Convert to Spark DataFrame
    spark = ctx.spark_session
    patients_df = resources_to_spark_df(patients, spark)
    
    # Find the latest update timestamp for the next watermark
    if patients:
        # Extract meta.lastUpdated from each resource
        update_times = []
        for patient in patients:
            meta = patient.get("meta", {})
            last_updated = meta.get("lastUpdated")
            if last_updated:
                update_times.append(last_updated)
        
        if update_times:
            # Set the next watermark to the latest update time
            next_watermark = max(update_times)
            logger.info("Setting next watermark", watermark=next_watermark)
            ctx.set_next_watermark(next_watermark)
    
    # Write to output with partitioning
    logger.info("Writing Patient bronze dataset", count=patients_df.count())
    patients_df.write.partitionBy("ingest_date").format("json").mode("append").save(output.uri) 