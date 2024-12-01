"""
Epic FHIR Resource Transformation Pipeline.

This pipeline transforms raw FHIR resources from the bronze layer 
into analytics-ready tables in the silver layer.
"""

import os
import yaml
import json
import logging
import datetime
import argparse
import traceback
import glob
from typing import Dict, Any, List, Optional, Tuple

# PySpark imports
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

# Local imports
from lib.transforms.common import explode_bundle
from fhir_pipeline.transforms.registry import get_transformer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def transform_resources(
    spark: SparkSession, 
    bronze_input, 
    resources_config,
    transform_metrics,
    silver_output,
    resource_type: Optional[str] = None,
) -> None:
    """
    Transform FHIR resources from bronze to silver layer.
    
    Args:
        spark: SparkSession
        bronze_input: Raw FHIR data
        resources_config: Resource configuration
        transform_metrics: Metrics output for monitoring
        silver_output: Output location for normalized data
        resource_type: Optional specific resource to transform
    """
    # Load resource config
    config_content = resources_config.read_file() if hasattr(resources_config, 'read_file') else None
    
    if config_content:
        resources_dict = yaml.safe_load(config_content)["resources"]
    else:
        # Fallback - read directly from the path attribute if available
        config_path = getattr(resources_config, 'path', None)
        if config_path:
            with open(config_path, 'r') as f:
                resources_dict = yaml.safe_load(f)["resources"]
        else:
            raise ValueError("Could not read resources configuration")
    
    # Setup quality metrics collection
    metrics = []
    transform_start_time = datetime.datetime.now()
    transform_timestamp = transform_start_time.strftime("%Y%m%d_%H%M%S")
    
    # Determine which resources to transform
    if resource_type:
        if resource_type not in resources_dict:
            raise ValueError(f"Unknown resource type: {resource_type}")
        resources_to_transform = {resource_type: resources_dict[resource_type]}
    else:
        # Filter to only enabled resources
        resources_to_transform = {k: v for k, v in resources_dict.items() if v.get("enabled", True)}
    
    total_resources = len(resources_to_transform)
    logger.info(f"Starting transformation of {total_resources} resource types")
    
    # Transform each resource
    for idx, (res_type, res_config) in enumerate(resources_to_transform.items(), 1):
        resource_start_time = datetime.datetime.now()
        resource_logger = logger.getChild(res_type)
        resource_logger.info(f"Transforming {res_type} resources ({idx}/{total_resources})")
        
        # Get the bronze path
        bronze_path = getattr(bronze_input, 'path', bronze_input)
        
        # Determine file path and format for this resource
        resource_dir = f"{bronze_path}/{res_type}"
        
        # Check file format by extension or directory structure
        json_files = glob.glob(f"{resource_dir}/*.json")
        parquet_files = glob.glob(f"{resource_dir}/*.parquet")
        delta_files = os.path.exists(f"{resource_dir}/_delta_log")
        
        # Log what format we found
        format_msg = []
        if json_files: format_msg.append(f"{len(json_files)} JSON files")
        if parquet_files: format_msg.append(f"{len(parquet_files)} Parquet files")
        if delta_files: format_msg.append("Delta format")
        
        if format_msg:
            resource_logger.info(f"Found {', '.join(format_msg)} in {resource_dir}")
        else:
            resource_logger.warning(f"No supported files found in {resource_dir}")
            metrics.append(create_transform_metric(
                res_type, "ERROR", 0, 0, 
                {"error": "No supported files found"}, 
                resource_start_time
            ))
            continue
        
        # Read bundles based on detected format
        try:
            if delta_files:
                # Delta format
                bundles_df = spark.read.format("delta").load(resource_dir)
            elif parquet_files:
                # Parquet format
                bundles_df = spark.read.parquet(resource_dir)
            else:
                # Default to JSON
                resource_path = f"{resource_dir}/*.json"
                bundles_df = spark.read.option("inferSchema", "false").json(resource_path)
            
            # Check if the dataframe contains expected data
            if "bundle" not in bundles_df.columns:
                # Try direct resource format
                if "resourceType" in bundles_df.columns:
                    resource_logger.info(f"Data has direct resource format (no bundle wrapper)")
                    resources_df = bundles_df
                else:
                    # Try one more approach for raw JSON files
                    try:
                        # Try re-reading with multiline option
                        resource_logger.info(f"Trying alternative JSON parsing for {res_type}")
                        alt_df = spark.read.option("multiline", "true").json(resource_path)
                        
                        if "resourceType" in alt_df.columns:
                            resource_logger.info(f"Successfully parsed {res_type} with alternative method")
                            resources_df = alt_df
                        else:
                            resource_logger.error(f"Missing expected columns in {res_type} files")
                            metrics.append(create_transform_metric(
                                res_type, "ERROR", 0, 0, 
                                {"error": "Invalid file format - missing required columns"}, 
                                resource_start_time
                            ))
                            continue
                    except Exception as json_error:
                        resource_logger.error(f"Error with alternative JSON parsing: {str(json_error)}")
                        resource_logger.error(f"Missing expected columns in {res_type} files")
                        metrics.append(create_transform_metric(
                            res_type, "ERROR", 0, 0, 
                            {"error": "Invalid file format - missing required columns"}, 
                            resource_start_time
                        ))
                        continue
            else:
                # Extract bundle entries
                resources_df = explode_bundle(bundles_df.select("bundle"))
            
            # Check if we got any resources - capture record counts
            input_count = resources_df.count()
            
            if input_count == 0:
                resource_logger.warning(f"No resources found in {res_type} bundles")
                metrics.append(create_transform_metric(
                    res_type, "WARNING", input_count, 0, 
                    {"warning": "No resources found in bundles"}, 
                    resource_start_time
                ))
                continue
                
            resource_logger.info(f"Found {input_count} {res_type} resources to transform")
            
            # Apply transformation using registry pattern
            try:
                # Get the appropriate transformer from registry
                transformer = get_transformer(spark, res_type)
                
                # Apply the transformation
                transformed_df = transformer.transform(resources_df)
                
                # Add metadata columns
                transformed_df = transformed_df.withColumn("_ingestion_timestamp", F.lit(transform_timestamp))
                transformed_df = transformed_df.withColumn("_source", F.lit("Epic FHIR API"))
                
                # Calculate output count
                output_count = transformed_df.count()
                
                # Get the silver output path
                silver_path = getattr(silver_output, 'path', silver_output)
                output_path = f"{silver_path}/{res_type.lower()}"
                
                # Create output directory if it doesn't exist
                os.makedirs(output_path, exist_ok=True)
                
                # Write out as parquet - for simplicity, just overwrite
                transformed_df.write.mode("overwrite").parquet(output_path)
                resource_logger.info(f"Wrote {output_count} {res_type} records to {output_path}")
                
                # Record successful transformation metrics
                metrics.append(create_transform_metric(
                    res_type, "SUCCESS", input_count, output_count, 
                    {"loss_pct": (100 * (input_count - output_count) / input_count) if input_count > 0 else 0}, 
                    resource_start_time
                ))
                
            except Exception as e:
                resource_logger.error(f"Error transforming {res_type}: {str(e)}")
                resource_logger.error(f"Traceback: {traceback.format_exc()}")
                metrics.append(create_transform_metric(
                    res_type, "ERROR", input_count, 0, 
                    {"error": str(e)}, 
                    resource_start_time
                ))
                
        except Exception as e:
            resource_logger.error(f"Error processing {res_type}: {str(e)}")
            resource_logger.error(f"Traceback: {traceback.format_exc()}")
            metrics.append(create_transform_metric(
                res_type, "ERROR", 0, 0, 
                {"error": str(e)}, 
                resource_start_time
            ))
    
    # Write metrics if output is available
    if hasattr(transform_metrics, 'write_dataframe'):
        logger.info(f"Writing transformation metrics")
        metrics_df = spark.createDataFrame(metrics)
        transform_metrics.write_dataframe(metrics_df)
    elif hasattr(transform_metrics, 'path'):
        # Write to path
        metrics_path = getattr(transform_metrics, 'path')
        logger.info(f"Writing transformation metrics to {metrics_path}")
        metrics_df = spark.createDataFrame(metrics)
        metrics_df.write.mode("overwrite").parquet(metrics_path)
    
    # Log overall completion
    total_time = (datetime.datetime.now() - transform_start_time).total_seconds()
    success_count = len([m for m in metrics if m["transform_status"] == "SUCCESS"])
    logger.info(f"Transformation completed: {success_count}/{total_resources} resources processed successfully in {total_time:.2f} seconds")


def create_transform_metric(
    resource_type: str, 
    status: str, 
    input_count: int, 
    output_count: int, 
    details: Dict[str, Any],
    start_time: datetime.datetime
) -> Dict[str, Any]:
    """
    Create a transform metric record.
    
    Args:
        resource_type: FHIR resource type
        status: Transform status (SUCCESS, ERROR, etc.)
        input_count: Number of input records
        output_count: Number of output records
        details: Additional details
        start_time: Start time of the transformation
        
    Returns:
        Dictionary with metric data
    """
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    return {
        "resource_type": resource_type,
        "transform_status": status,
        "input_record_count": input_count,
        "output_record_count": output_count,
        "transform_time_seconds": duration,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "details": json.dumps(details),
    }


# Allow command-line usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform FHIR resources")
    parser.add_argument("--resource", help="Specific resource type to transform")
    args = parser.parse_args()
    
    # When running locally, you would need to set up connections to Foundry datasets
    # This is just a sketch of how it would work
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("fhir_transform").getOrCreate()
    
    # In a real scenario, you would need to connect to Foundry datasets
    transform_resources(spark, None, None, None, None, args.resource)
