import os
import argparse
import logging
from typing import List, Optional

from pyspark.sql import SparkSession

from fhir_pipeline.transforms.registry import get_transformer
from fhir_pipeline.utils.logging import get_logger

logger = get_logger("transform_load")

def transform_resource(
    spark: SparkSession, 
    resource_type: str, 
    input_path: str, 
    output_path: str,
    options: Optional[dict] = None
) -> None:
    """
    Transform FHIR resources from Bronze to Silver using the appropriate transformer.
    
    Args:
        spark: Active SparkSession
        resource_type: FHIR resource type to transform
        input_path: Path to input DataFrame (Bronze)
        output_path: Path to output DataFrame (Silver)
        options: Additional options for the transform
    """
    logger.info(f"Transforming {resource_type} from {input_path} to {output_path}")
    
    # Set default options
    if options is None:
        options = {}
    
    # Read input resources
    resources_df = spark.read.format("delta").load(input_path)
    logger.info(f"Loaded {resources_df.count()} {resource_type} resources from {input_path}")
    
    # Get the appropriate transformer for this resource type
    transformer = get_transformer(spark, resource_type)
    
    # Apply the transformation
    transformed_df = transformer.transform(resources_df)
    
    # Apply partitioning if specified in transformer config
    partition_cols = []
    if 'extras' in transformer.mapping_spec and 'partition_by' in transformer.mapping_spec['extras']:
        partition_cols = transformer.mapping_spec['extras']['partition_by']
    
    # Optimize write for large datasets
    if transformed_df.count() > 10000000:  # 10M rows
        transformed_df = transformed_df.repartition(200)
    
    # Write the output
    writer = transformed_df.write.format("delta").mode("overwrite")
    
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
        
    writer.save(output_path)
    
    logger.info(f"Wrote {transformed_df.count()} rows to {output_path}")
    
    # Also write manifest file if appropriate
    # This would create a Foundry dataset manifest file
    _write_dataset_manifest(resource_type, output_path)

def _write_dataset_manifest(resource_type: str, output_path: str) -> None:
    """Write a Foundry dataset manifest if in Foundry environment."""
    # Only write manifest in Foundry environment
    if 'FOUNDRY_PROJECT' not in os.environ:
        return
        
    # Simple manifest for now - could be enhanced based on Section 11.4
    manifest = {
        "name": f"fhir_normalized_{resource_type.lower()}",
        "format": "delta",
        "retention": {
            "expiration": "365d",
            "stage": "Silver"
        },
        "schemaEvolution": True
    }
    
    # The actual manifest writing would be implemented here
    # This is a placeholder since the actual implementation would depend on Foundry APIs
    logger.info(f"Would write manifest for {resource_type} to {output_path}")

def run_pipeline(
    spark: SparkSession,
    resource_types: List[str],
    bronze_base_path: str = "/bronze/fhir_raw",
    silver_base_path: str = "/silver/fhir_normalized",
    options: Optional[dict] = None
) -> None:
    """
    Run the transform pipeline for a list of resource types.
    
    Args:
        spark: Active SparkSession
        resource_types: List of FHIR resource types to transform
        bronze_base_path: Base path for Bronze datasets
        silver_base_path: Base path for Silver datasets
        options: Additional options for the transform
    """
    for resource_type in resource_types:
        input_path = f"{bronze_base_path}/{resource_type.lower()}"
        output_path = f"{silver_base_path}/{resource_type.lower()}"
        
        try:
            transform_resource(spark, resource_type, input_path, output_path, options)
        except Exception as e:
            logger.error(f"Error transforming {resource_type}: {e}", exc_info=True)
            if options and options.get('fail_fast', False):
                raise
                
    logger.info(f"Completed transformation of {len(resource_types)} resource types")

def main():
    """Main entry point for the transform_load pipeline."""
    parser = argparse.ArgumentParser(description="Transform FHIR resources from Bronze to Silver")
    parser.add_argument("--resource-types", nargs="+", help="FHIR resource types to transform")
    parser.add_argument("--bronze-path", default="/bronze/fhir_raw", help="Base path for Bronze datasets")
    parser.add_argument("--silver-path", default="/silver/fhir_normalized", help="Base path for Silver datasets")
    parser.add_argument("--all", action="store_true", help="Transform all available resource types")
    parser.add_argument("--fail-fast", action="store_true", help="Fail immediately on any error")
    
    args = parser.parse_args()
    
    # Create SparkSession
    spark = SparkSession.builder \
        .appName("FHIR-Transform-Load") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    options = {
        "fail_fast": args.fail_fast
    }
    
    # Determine resource types to process
    resource_types = args.resource_types
    if args.all:
        # Auto-discover all available mapping files
        config_dir = os.environ.get(
            "FHIR_CONFIG_DIR",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        )
        mappings_dir = os.path.join(config_dir, "generic_mappings")
        resource_types = [
            os.path.splitext(f)[0] for f in os.listdir(mappings_dir)
            if f.endswith(".yaml")
        ]
        
    if not resource_types:
        logger.error("No resource types specified. Use --resource-types or --all")
        return 1
        
    logger.info(f"Processing resource types: {', '.join(resource_types)}")
    
    # Run the pipeline
    run_pipeline(
        spark,
        resource_types,
        args.bronze_path,
        args.silver_path,
        options
    )
    
    return 0

if __name__ == "__main__":
    exit(main()) 