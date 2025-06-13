"""
Silver to Gold transformation module.

This module provides functions to transform FHIR data from the Silver layer
into the Gold layer with domain-specific structured formats.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from pyspark.sql import DataFrame, SparkSession

from epic_fhir_integration.transform.gold import (
    PatientSummary,
    ObservationSummary,
    EncounterSummary,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def transform_silver_to_gold(
    resource_type: str,
    silver_path: Union[str, Path],
    gold_path: Union[str, Path],
    spark: SparkSession,
) -> Path:
    """Transform a Silver layer resource into the Gold layer.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation").
        silver_path: Path to the Silver layer data.
        gold_path: Path to the Gold layer output.
        spark: Spark session.
        
    Returns:
        Path to the Gold layer output.
    """
    if isinstance(silver_path, str):
        silver_path = Path(silver_path)
    
    if isinstance(gold_path, str):
        gold_path = Path(gold_path)
    
    logger.info(f"Transforming {resource_type} from Silver to Gold")
    
    # Select the appropriate transformer
    if resource_type.lower() == "patient":
        transformer = PatientSummary(spark, silver_path, gold_path)
    elif resource_type.lower() == "observation":
        transformer = ObservationSummary(spark, silver_path, gold_path)
    elif resource_type.lower() == "encounter":
        transformer = EncounterSummary(spark, silver_path, gold_path)
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")
    
    # Execute the transformation
    transformer.execute()
    
    output_path = gold_path / resource_type.lower()
    return output_path


def transform_all_silver_to_gold(
    resource_types: List[str],
    silver_base_path: Union[str, Path],
    gold_base_path: Union[str, Path],
    spark: Optional[SparkSession] = None,
) -> Dict[str, Path]:
    """Transform multiple resource types from Silver to Gold.
    
    Args:
        resource_types: List of FHIR resource types to transform.
        silver_base_path: Base path for Silver layer data.
        gold_base_path: Base path for Gold layer output.
        spark: Optional Spark session. If not provided, a new one will be created.
        
    Returns:
        Dictionary mapping resource types to Gold layer output paths.
    """
    if isinstance(silver_base_path, str):
        silver_base_path = Path(silver_base_path)
    
    if isinstance(gold_base_path, str):
        gold_base_path = Path(gold_base_path)
    
    # Create Spark session if not provided
    if spark is None:
        spark = SparkSession.builder \
            .appName("FHIR Silver to Gold") \
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
            .getOrCreate()
    
    # Transform each resource type
    output_paths = {}
    for resource_type in resource_types:
        try:
            output_path = transform_silver_to_gold(
                resource_type, silver_base_path, gold_base_path, spark
            )
            output_paths[resource_type] = output_path
            logger.info(f"Successfully transformed {resource_type} to Gold")
        except Exception as e:
            logger.error(f"Error transforming {resource_type} from Silver to Gold: {e}")
            # Continue with the next resource type
    
    return output_paths


def validate_schemas(paths: Dict[str, Path], spark: SparkSession) -> Dict[str, bool]:
    """Validate the schemas of Gold layer datasets.
    
    Args:
        paths: Dictionary mapping resource types to Gold layer paths.
        spark: Spark session.
        
    Returns:
        Dictionary mapping resource types to validation results.
    """
    from epic_fhir_integration.schemas.gold import (
        patient_schema, observation_schema, encounter_schema
    )
    
    validation_results = {}
    
    # Define schema validation map
    schema_map = {
        "patient": patient_schema,
        "observation": observation_schema,
        "encounter": encounter_schema,
    }
    
    for resource_type, path in paths.items():
        resource_type_lower = resource_type.lower()
        
        # Skip if no schema defined for this resource type
        if resource_type_lower not in schema_map:
            logger.warning(f"No schema defined for {resource_type}, skipping validation")
            continue
        
        try:
            # Read the parquet file
            df = spark.read.parquet(str(path))
            
            # Get expected schema
            expected_schema = schema_map[resource_type_lower]
            
            # Compare schemas
            actual_fields = {f.name: f.dataType for f in df.schema.fields}
            expected_fields = {f.name: f.dataType for f in expected_schema.fields}
            
            # Check if all expected fields are present with correct types
            missing_fields = []
            type_mismatches = []
            
            for field_name, field_type in expected_fields.items():
                if field_name not in actual_fields:
                    missing_fields.append(field_name)
                elif str(actual_fields[field_name]) != str(field_type):
                    type_mismatches.append(
                        f"{field_name}: expected {field_type}, got {actual_fields[field_name]}"
                    )
            
            if missing_fields or type_mismatches:
                logger.error(f"Schema validation failed for {resource_type}:")
                if missing_fields:
                    logger.error(f"  Missing fields: {', '.join(missing_fields)}")
                if type_mismatches:
                    logger.error(f"  Type mismatches: {', '.join(type_mismatches)}")
                validation_results[resource_type] = False
            else:
                logger.info(f"Schema validation passed for {resource_type}")
                validation_results[resource_type] = True
                
        except Exception as e:
            logger.error(f"Error validating {resource_type} schema: {e}")
            validation_results[resource_type] = False
    
    return validation_results


def main():
    """Main entry point for Silver to Gold transformation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transform FHIR Silver to Gold")
    parser.add_argument(
        "--resources", nargs="+", help="FHIR resource types to transform"
    )
    parser.add_argument(
        "--silver-dir", help="Base directory for Silver input", default="output"
    )
    parser.add_argument(
        "--gold-dir", help="Base directory for Gold output", default="output"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate schema after transformation"
    )
    args = parser.parse_args()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("FHIR Silver to Gold") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    # Default resource types if not specified
    resource_types = args.resources or ["Patient", "Observation", "Encounter"]
    
    # Transform resources
    output_paths = transform_all_silver_to_gold(
        resource_types, args.silver_dir, args.gold_dir, spark
    )
    
    # Validate schemas if requested
    if args.validate:
        validation_results = validate_schemas(output_paths, spark)
        for resource_type, is_valid in validation_results.items():
            status = "VALID" if is_valid else "INVALID"
            logger.info(f"{resource_type} schema: {status}")
    
    for resource_type, path in output_paths.items():
        logger.info(f"Transformed {resource_type} to Gold: {path}")


if __name__ == "__main__":
    main() 