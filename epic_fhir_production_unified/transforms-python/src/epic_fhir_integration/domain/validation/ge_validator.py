"""
Great Expectations validator for FHIR resources.

This module provides validation capabilities for FHIR resources using Great Expectations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import great_expectations as gx
from great_expectations.dataset import SparkDFDataset
from pyspark.sql import DataFrame, SparkSession
from transforms.api import transform_df, Input, Output, Config

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


def load_expectations(resource_type: str) -> List[Dict[str, Any]]:
    """Load expectations for a resource type from JSON file.
    
    Args:
        resource_type: FHIR resource type.
        
    Returns:
        List of expectations.
    """
    # Get the path to the expectations file
    current_dir = Path(__file__).parent
    expectations_path = current_dir / f"expectations/{resource_type.lower()}.json"
    
    try:
        with open(expectations_path, "r") as f:
            expectations_json = json.load(f)
            return expectations_json.get("expectations", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load expectations for {resource_type}", 
                      resource_type=resource_type,
                      error=str(e))
        return []


def validate_with_great_expectations(
    df: DataFrame,
    resource_type: str,
    spark: Optional[SparkSession] = None,
) -> Dict[str, Any]:
    """Validate a DataFrame with Great Expectations.
    
    Args:
        df: DataFrame to validate.
        resource_type: FHIR resource type.
        spark: Optional SparkSession.
        
    Returns:
        Validation results.
    """
    # Convert to SparkDFDataset
    gx_df = SparkDFDataset(df)
    
    # Load expectations
    expectations = load_expectations(resource_type)
    
    # Apply each expectation
    for expectation in expectations:
        expectation_type = expectation.get("expectation_type")
        kwargs = expectation.get("kwargs", {})
        
        try:
            method = getattr(gx_df, expectation_type)
            method(**kwargs)
        except (AttributeError, TypeError) as e:
            logger.warning(f"Failed to apply expectation {expectation_type}",
                          expectation_type=expectation_type,
                          error=str(e))
    
    # Validate and return results
    validation_result = gx_df.validate()
    
    return validation_result


@transform_df(
    Output("datasets.{resource_type}_GE_Results"),
    Input("datasets.{resource_type}_Clean_Silver"),
    Config("resource_type", ""),
)
def compute(ctx, output, clean_silver, resource_type):
    """Validate FHIR resources with Great Expectations and write results.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        clean_silver: Input Silver dataset.
        resource_type: FHIR resource type.
    """
    if not resource_type:
        raise ValueError("resource_type config parameter is required")
    
    logger.info(f"Starting {resource_type} validation with Great Expectations",
                resource_type=resource_type)
    
    # Read the Silver dataset
    silver_df = clean_silver.dataframe()
    row_count = silver_df.count()
    logger.info(f"Read {resource_type} silver dataset", 
                resource_type=resource_type,
                count=row_count)
    
    # Skip validation if no data
    if row_count == 0:
        logger.warning(f"No data to validate for {resource_type}", 
                      resource_type=resource_type)
        empty_result = {
            "success": True,
            "statistics": {"evaluated_expectations": 0, "successful_expectations": 0},
            "meta": {"great_expectations_version": gx.__version__},
            "results": []
        }
        # Write empty result
        ctx.write_dataframe(output, ctx.dataframe_from_json([empty_result]))
        return
    
    # Validate with Great Expectations
    try:
        validation_result = validate_with_great_expectations(
            df=silver_df,
            resource_type=resource_type,
            spark=ctx.spark_session,
        )
        
        # Check if validation passed
        success = validation_result.get("success", False)
        evaluated = validation_result.get("statistics", {}).get("evaluated_expectations", 0)
        successful = validation_result.get("statistics", {}).get("successful_expectations", 0)
        
        logger.info(f"Validation completed for {resource_type}",
                   resource_type=resource_type,
                   success=success,
                   evaluated_expectations=evaluated,
                   successful_expectations=successful)
        
        # Convert validation_result to JSON
        result_json = validation_result.to_json_dict()
        
        # Write results to output
        ctx.write_dataframe(output, ctx.dataframe_from_json([result_json]))
    except Exception as e:
        logger.error(f"Error validating {resource_type}",
                    resource_type=resource_type,
                    error=str(e))
        raise 