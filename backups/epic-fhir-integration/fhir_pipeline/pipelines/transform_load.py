import os
import argparse
import logging
import glob
import json
import time
import traceback
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

from fhir_pipeline.transforms.registry import get_transformer
from fhir_pipeline.utils.logging import get_logger
from fhir_pipeline.utils.strict_mode import get_strict_mode, strict_mode_check

logger = get_logger("transform_load")

def validate_paths(input_path: str, output_path: str) -> Tuple[Path, Path]:
    """
    Validate and normalize input and output paths.
    
    Args:
        input_path: Path to input (bronze) data
        output_path: Path to output (silver) data
        
    Returns:
        Tuple of normalized paths (input_path, output_path)
        
    Raises:
        ValueError: If paths are invalid
    """
    # Convert to Path objects for better manipulation
    input_path_obj = Path(input_path)
    output_path_obj = Path(output_path)
    
    # Validate input path
    if not input_path_obj.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    
    # Check and fix common path errors
    if str(input_path_obj).endswith('/'):
        input_path_obj = input_path_obj.parent
        logger.warning(f"Removed trailing slash from input path: {input_path_obj}")
        
    # Make sure output directory exists
    os.makedirs(output_path_obj, exist_ok=True)
    
    return input_path_obj, output_path_obj

def diagnose_input_files(input_path: Path, resource_type: str) -> Dict[str, Any]:
    """
    Diagnose input files and provide helpful information about them.
    
    Args:
        input_path: Path to check
        resource_type: FHIR resource type
        
    Returns:
        Dictionary of diagnostic information
    """
    diagnostics = {
        "path": str(input_path),
        "resource_type": resource_type,
        "exists": input_path.exists(),
        "is_directory": input_path.is_dir() if input_path.exists() else False,
        "file_counts": {},
        "total_files": 0,
        "sample_files": [],
        "errors": []
    }
    
    if not diagnostics["exists"]:
        diagnostics["errors"].append(f"Input path does not exist: {input_path}")
        return diagnostics
    
    if not diagnostics["is_directory"]:
        diagnostics["errors"].append(f"Input path is not a directory: {input_path}")
        return diagnostics
    
    # Count files by type
    diagnostics["file_counts"] = {
        "json": len(list(input_path.glob("*.json"))),
        "parquet": len(list(input_path.glob("*.parquet"))),
        "delta": 1 if (input_path / "_delta_log").exists() else 0
    }
    
    diagnostics["total_files"] = sum(diagnostics["file_counts"].values())
    
    # Add sample file info
    json_files = list(input_path.glob("*.json"))
    if json_files:
        sample_file = json_files[0]
        try:
            with open(sample_file, 'r') as f:
                data = json.load(f)
                diagnostics["sample_files"].append({
                    "name": sample_file.name,
                    "size": sample_file.stat().st_size,
                    "modified": time.ctime(sample_file.stat().st_mtime),
                    "structure": "bundle" if "bundle" in data else "resource",
                    "entry_count": len(data.get("bundle", {}).get("entry", [])) if "bundle" in data else 1
                })
        except Exception as e:
            diagnostics["errors"].append(f"Error reading sample file {sample_file.name}: {str(e)}")
    
    return diagnostics

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
    start_time = time.time()
    logger.info(f"Transforming {resource_type} from {input_path} to {output_path}")
    
    # Set default options
    if options is None:
        options = {}
    
    try:
        # Validate and normalize paths
        input_path_obj, output_path_obj = validate_paths(input_path, output_path)
        
        # Diagnose input files
        diagnostics = diagnose_input_files(input_path_obj, resource_type)
        logger.info(f"Input path diagnostics: {json.dumps(diagnostics, indent=2)}")
        
        if diagnostics["errors"]:
            error_msg = f"Errors found in input path: {'; '.join(diagnostics['errors'])}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if diagnostics["total_files"] == 0:
            logger.warning(f"No files found for {resource_type} in {input_path}")
            
            # In strict mode, fail on missing data
            if get_strict_mode():
                strict_mode_check(f"No files found for {resource_type} - would need mock data")
                
            return
        
        # Determine the file format by checking file extensions
        json_files = glob.glob(f"{input_path_obj}/*.json")
        parquet_files = glob.glob(f"{input_path_obj}/*.parquet")
        delta_files = os.path.exists(f"{input_path_obj}/_delta_log")
        
        # Load resources based on the detected format
        if delta_files:
            logger.info(f"Detected Delta format files in {input_path_obj}")
            resources_df = spark.read.format("delta").load(str(input_path_obj))
        elif parquet_files:
            logger.info(f"Detected Parquet files in {input_path_obj}")
            resources_df = spark.read.parquet(str(input_path_obj))
        elif json_files:
            logger.info(f"Detected JSON files in {input_path_obj}")
            # Read JSON files with minimal schema inference
            # This handles the case where extraction saves data as JSON bundles
            try:
                bundles_df = spark.read.option("inferSchema", "false").json(f"{input_path_obj}/*.json")
                
                # Check if the dataframe contains expected data structure
                if "bundle" in bundles_df.columns:
                    # Extract resources from bundles following same logic as in 03_transform_load.py
                    from pyspark.sql.functions import explode
                    
                    # Extract all resources from the bundle entries
                    if "bundle.entry" in bundles_df.columns:
                        resources_df = bundles_df.select(
                            explode("bundle.entry.resource").alias("resource")
                        )
                    else:
                        logger.error(f"No entries found in bundle for {resource_type}")
                        raise ValueError(f"Invalid bundle structure: missing bundle.entry field")
                else:
                    # Try direct resource format (if not using bundle structure)
                    if "resourceType" in bundles_df.columns:
                        resources_df = bundles_df
                    else:
                        # In cases where we have raw FHIR JSON resources, try a different approach
                        try:
                            # Try reading each JSON file individually
                            from pyspark.sql.types import StructType
                            
                            # Create a simple schema
                            schema = StructType([])
                            
                            # Read all JSON files in the directory
                            resources_df = spark.read.option("multiline", "true").json(str(input_path_obj))
                            
                            # If that worked, check if we got resourceType field
                            if "resourceType" not in resources_df.columns:
                                logger.warning(f"JSON files for {resource_type} don't contain resourceType field")
                        except Exception as json_read_error:
                            logger.error(f"Failed to read JSON files without structure: {str(json_read_error)}")
                            raise ValueError(f"Cannot parse JSON files: neither bundle nor resourceType fields found")
            except Exception as e:
                logger.error(f"Error reading JSON files: {str(e)}")
                logger.error(f"Stack trace: {traceback.format_exc()}")
                raise ValueError(f"Failed to read JSON files for {resource_type}: {str(e)}")
        else:
            logger.error(f"No supported files found in {input_path_obj}")
            raise ValueError(f"No supported files (JSON, Parquet, or Delta) found in {input_path_obj}")
        
        # Log the resource count
        resource_count = resources_df.count()
        logger.info(f"Loaded {resource_count} {resource_type} resources from {input_path_obj}")
        
        if resource_count == 0:
            logger.warning(f"No resources found for {resource_type}")
            
            # In strict mode, fail on empty resources
            if get_strict_mode():
                strict_mode_check(f"No resources found for {resource_type} - would need mock data")
                
            return
        
        # Add source file information for debugging
        resources_df = resources_df.withColumn("_source_path", lit(str(input_path_obj)))
        resources_df = resources_df.withColumn("_processing_time", lit(time.time()))
        
        # Get the appropriate transformer for this resource type
        try:
            transformer = get_transformer(spark, resource_type)
        except Exception as e:
            logger.error(f"Failed to get transformer for {resource_type}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Transformer not found for resource type {resource_type}: {str(e)}")
        
        # Apply the transformation
        try:
            transformed_df = transformer.transform(resources_df)
        except Exception as e:
            logger.error(f"Transformation failed for {resource_type}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Additional diagnostics on schema
            logger.error(f"Resource DataFrame schema: {resources_df.schema.simpleString()}")
            
            # Log sample records that might be causing the issue
            try:
                logger.error("Sample of problematic records:")
                sample_records = resources_df.limit(2).toJSON().collect()
                for record in sample_records:
                    logger.error(f"Record: {record}")
            except:
                logger.error("Could not collect sample records")
                
            raise ValueError(f"Failed to transform {resource_type} resources: {str(e)}")
        
        # Apply partitioning if specified in transformer config
        partition_cols = []
        if hasattr(transformer, 'mapping_spec') and 'extras' in transformer.mapping_spec and 'partition_by' in transformer.mapping_spec['extras']:
            partition_cols = transformer.mapping_spec['extras']['partition_by']
        
        # Optimize write for large datasets
        if transformed_df.count() > 10000000:  # 10M rows
            transformed_df = transformed_df.repartition(200)
        
        # Write the output
        try:
            writer = transformed_df.write.format("delta").mode("overwrite")
            
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
                
            writer.save(str(output_path_obj))
            
            # Log final statistics
            end_time = time.time()
            elapsed = end_time - start_time
            output_count = transformed_df.count()
            logger.info(f"Wrote {output_count} rows to {output_path_obj}")
            logger.info(f"Transformation completed in {elapsed:.2f} seconds")
            
            # Log loss percentage
            if resource_count > 0:
                loss_pct = 100 * (resource_count - output_count) / resource_count
                logger.info(f"Resource loss: {loss_pct:.2f}% ({resource_count - output_count} records)")
        except Exception as e:
            logger.error(f"Failed to write transformed data for {resource_type}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to write transformed data to {output_path_obj}: {str(e)}")
    
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        logger.error(f"Ensure the input path {input_path} exists and contains {resource_type} data")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error transforming {resource_type}: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise ValueError(f"Failed to transform {resource_type}: {str(e)}")
    
    # Also write manifest file if appropriate
    try:
        _write_dataset_manifest(resource_type, str(output_path_obj))
    except Exception as e:
        logger.warning(f"Failed to write manifest for {resource_type}: {str(e)}")

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
    total_start_time = time.time()
    successful_resources = 0
    failed_resources = 0
    
    # Validate base paths
    bronze_base_path = os.path.normpath(bronze_base_path)
    silver_base_path = os.path.normpath(silver_base_path)
    
    if not os.path.exists(bronze_base_path):
        raise FileNotFoundError(f"Bronze base path does not exist: {bronze_base_path}")
    
    # Create silver base path if it doesn't exist
    os.makedirs(silver_base_path, exist_ok=True)
    
    logger.info(f"Starting transformation of {len(resource_types)} resources")
    logger.info(f"Bronze base path: {bronze_base_path}")
    logger.info(f"Silver base path: {silver_base_path}")
    
    # Process each resource type
    for resource_type in resource_types:
        # Normalize resource type (convert to lowercase for directory)
        resource_dir = resource_type.lower()
        
        # Check for case mismatch in directory name
        actual_dir = resource_type
        for item in os.listdir(bronze_base_path):
            if item.lower() == resource_dir:
                actual_dir = item
                break
        
        input_path = os.path.join(bronze_base_path, actual_dir)
        output_path = os.path.join(silver_base_path, resource_dir)
        
        logger.info(f"Processing resource type: {resource_type}")
        logger.info(f"  Input path: {input_path}")
        logger.info(f"  Output path: {output_path}")
        
        try:
            transform_resource(spark, resource_type, input_path, output_path, options)
            successful_resources += 1
        except Exception as e:
            logger.error(f"Error transforming {resource_type}: {e}")
            if options and options.get('fail_fast', False):
                logger.error("Failing fast due to error")
                raise
            failed_resources += 1
    
    # Log final summary
    total_time = time.time() - total_start_time
    logger.info(f"Transformation pipeline completed in {total_time:.2f} seconds")
    logger.info(f"Results: {successful_resources} resources transformed successfully, {failed_resources} failed")
    
    if failed_resources > 0:
        logger.warning(f"Some resources failed to transform ({failed_resources}/{len(resource_types)})")
    else:
        logger.info(f"All {successful_resources} resources transformed successfully")

def main():
    """Main entry point for the transform_load pipeline."""
    parser = argparse.ArgumentParser(description="Transform FHIR resources from Bronze to Silver")
    parser.add_argument("--resource-types", nargs="+", help="FHIR resource types to transform")
    parser.add_argument("--bronze-path", default="/bronze/fhir_raw", help="Base path for Bronze datasets")
    parser.add_argument("--silver-path", default="/silver/fhir_normalized", help="Base path for Silver datasets")
    parser.add_argument("--all", action="store_true", help="Transform all available resource types")
    parser.add_argument("--fail-fast", action="store_true", help="Fail immediately on any error")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (no mock data)")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger("fhir_pipeline").setLevel(logging.DEBUG)
        
    # Import and enable strict mode if requested
    if args.strict:
        from fhir_pipeline.utils.strict_mode import enable_strict_mode
        enable_strict_mode()
        logger.info("Strict mode enabled - no mock data will be used")
    
    # Create SparkSession
    spark = SparkSession.builder \
        .appName("FHIR-Transform-Load") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    options = {
        "fail_fast": args.fail_fast,
        "verbose": args.verbose,
        "strict_mode": args.strict
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
        
        if os.path.exists(mappings_dir):
            resource_types = [
                os.path.splitext(f)[0] for f in os.listdir(mappings_dir)
                if f.endswith(".yaml")
            ]
        else:
            logger.error(f"Mappings directory not found: {mappings_dir}")
            logger.error("Cannot auto-discover resource types")
            return 1
        
    if not resource_types:
        logger.error("No resource types specified. Use --resource-types or --all")
        return 1
        
    logger.info(f"Processing resource types: {', '.join(resource_types)}")
    
    # Run the pipeline
    try:
        run_pipeline(
            spark,
            resource_types,
            args.bronze_path,
            args.silver_path,
            options
        )
        return 0
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit(main()) 