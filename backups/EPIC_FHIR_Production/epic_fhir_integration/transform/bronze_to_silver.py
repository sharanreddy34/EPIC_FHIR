"""
Bronze to Silver Transformation for FHIR Resources.

This module transforms raw FHIR resources from the Bronze layer to the Silver layer.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from pyspark.sql import SparkSession, DataFrame
import pyspark.sql.functions as F

logger = logging.getLogger(__name__)

def transform_all_bronze_to_silver(
    resource_types: List[str],
    bronze_base_path: str,
    silver_base_path: str,
    spark: SparkSession,
) -> Dict[str, str]:
    """Transform FHIR resources from Bronze to Silver.
    
    Args:
        resource_types: List of FHIR resource types to transform.
        bronze_base_path: Base path for Bronze data.
        silver_base_path: Base path for Silver output.
        spark: Spark session.
        
    Returns:
        Dictionary mapping resource types to output paths.
    """
    output_paths = {}
    
    for resource_type in resource_types:
        logger.info(f"Transforming {resource_type} from Bronze to Silver")
        
        # Create resource-specific output directory
        silver_path = f"{silver_base_path}/{resource_type}"
        Path(silver_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Read bronze data
        bronze_path = f"{bronze_base_path}/{resource_type}"
        
        try:
            # Read NDJSON files from bronze path
            bronze_df = spark.read.json(f"{bronze_path}/*.ndjson")
            
            # Apply transformations (simplified example)
            silver_df = transform_resource_to_silver(bronze_df, resource_type)
            
            # Write to silver path
            silver_df.write.mode("overwrite").parquet(silver_path)
            
            output_paths[resource_type] = silver_path
            logger.info(f"Transformed {resource_type} from Bronze to Silver: {silver_path}")
            
        except Exception as e:
            logger.error(f"Error transforming {resource_type} from Bronze to Silver: {e}")
    
    return output_paths


def transform_resource_to_silver(df: DataFrame, resource_type: str) -> DataFrame:
    """Transform a resource DataFrame from Bronze to Silver.
    
    Args:
        df: Bronze DataFrame.
        resource_type: FHIR resource type.
        
    Returns:
        Transformed Silver DataFrame.
    """
    # Basic transformations common to all resource types
    result_df = df.withColumn("processing_time", F.current_timestamp())
    
    # Resource-specific transformations
    if resource_type == "Patient":
        # Extract and flatten Patient-specific fields
        if "name" in df.columns and "birthDate" in df.columns:
            result_df = result_df \
                .withColumn("given_name", F.col("name").getItem(0).getField("given").getItem(0)) \
                .withColumn("family_name", F.col("name").getItem(0).getField("family")) \
                .withColumn("birth_date", F.col("birthDate"))
                
    elif resource_type == "Observation":
        # Extract and flatten Observation-specific fields
        if "code" in df.columns and "valueQuantity" in df.columns:
            result_df = result_df \
                .withColumn("code", F.col("code").getField("coding").getItem(0).getField("code")) \
                .withColumn("value", F.col("valueQuantity").getField("value")) \
                .withColumn("unit", F.col("valueQuantity").getField("unit"))
                
    elif resource_type == "Encounter":
        # Extract and flatten Encounter-specific fields
        if "status" in df.columns and "period" in df.columns:
            result_df = result_df \
                .withColumn("status", F.col("status")) \
                .withColumn("start_time", F.col("period").getField("start")) \
                .withColumn("end_time", F.col("period").getField("end"))
    
    return result_df 