"""
Patient validation transform for Epic FHIR integration.

This module provides a transform for validating Patient resources
in the Bronze dataset.
"""

import json
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, udf
from pyspark.sql.types import ArrayType, StringType, StructType, StructField
from transforms.api import transform_df, Input, Output

from epic_fhir_integration.validation.validator import FHIRValidator
from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


# Define schema for validation results
VALIDATION_SCHEMA = StructType([
    StructField("resource_type", StringType(), True),
    StructField("resource_id", StringType(), True),
    StructField("level", StringType(), True),
    StructField("message", StringType(), True),
    StructField("location", StringType(), True),
])


@transform_df(
    Output("datasets.Patient_Validation_Silver"),
    Input("datasets.Patient_Raw_Bronze"),
)
def compute(ctx, output, patient_bronze):
    """Validate Patient resources in the Bronze dataset.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        patient_bronze: Input Bronze dataset.
    """
    logger.info("Starting Patient validation")
    
    # Read input dataset
    bronze_df = patient_bronze.dataframe()
    logger.info("Read bronze dataset", count=bronze_df.count())
    
    # Create validator
    validator = FHIRValidator()
    
    # Define validation UDF
    def validate_json(json_data):
        try:
            resource = json.loads(json_data)
            results = validator.validate(resource)
            return [result.to_dict() for result in results]
        except Exception as e:
            logger.error("Validation error", error=str(e))
            return []
    
    # Register UDF
    validate_json_udf = udf(validate_json, ArrayType(VALIDATION_SCHEMA))
    
    # Apply UDF to each row
    validation_df = bronze_df.select(
        col("json_data"),
        validate_json_udf(col("json_data")).alias("validation_results"),
        col("ingest_timestamp"),
        col("ingest_date")
    )
    
    # Explode the array of validation results
    from pyspark.sql.functions import explode_outer
    
    results_df = validation_df.select(
        explode_outer("validation_results").alias("result"),
        col("ingest_timestamp"),
        col("ingest_date")
    ).select(
        col("result.resource_type"),
        col("result.resource_id"),
        col("result.level"),
        col("result.message"),
        col("result.location"),
        col("ingest_timestamp"),
        col("ingest_date")
    )
    
    # Write to output
    logger.info("Writing Patient validation results", count=results_df.count())
    results_df.write.partitionBy("ingest_date").format("parquet").mode("overwrite").save(output.uri) 