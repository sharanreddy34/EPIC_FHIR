"""
Multi-resource FHIR extractor for Bronze layer.

This module provides a framework for extracting multiple FHIR resource types
from the Epic API and writing them to Bronze datasets in Foundry.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DateType

from epic_fhir_integration.api_clients.fhir_client import FHIRClient, create_fhir_client
from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)

# Default resources to extract if not specified in environment
DEFAULT_RESOURCES = "Patient,Encounter,Observation,Condition,MedicationRequest"


def get_resource_list() -> List[str]:
    """Get the list of resources to extract from environment variable.
    
    Returns:
        List of resource types to extract.
    """
    resources_env = os.getenv("INGEST_RESOURCES", DEFAULT_RESOURCES)
    return [r.strip() for r in resources_env.split(",") if r.strip()]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def extract_resource(
    client: FHIRClient,
    resource_type: str,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
    last_updated_since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract resources of specified type from the Epic API.
    
    Args:
        client: FHIR client to use.
        resource_type: FHIR resource type (e.g., "Patient", "Observation").
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve.
        last_updated_since: Optional timestamp to fetch only resources updated since.
        
    Returns:
        List of FHIR resources.
    """
    # Default params
    params = params or {}
    
    # Add last updated parameter if provided
    if last_updated_since:
        params["_lastUpdated"] = f"gt{last_updated_since}"
    
    logger.info(f"Extracting {resource_type} resources", 
               resource_type=resource_type, 
               params=params)
    
    # Extract resources
    try:
        resources = client.get_all_resources(
            resource_type=resource_type,
            params=params,
            max_pages=max_pages,
        )
        
        logger.info(f"Extracted {resource_type} resources", 
                  resource_type=resource_type, 
                  count=len(resources))
        return resources
    except Exception as e:
        logger.error(f"Error extracting {resource_type} resources", 
                    resource_type=resource_type,
                    error=str(e))
        # Reraise to trigger retry if applicable
        raise


def resources_to_spark_df(
    resources: List[Dict[str, Any]], 
    spark: Optional[SparkSession] = None
) -> DataFrame:
    """Convert a list of FHIR resources to a Spark DataFrame.
    
    Args:
        resources: List of FHIR resources.
        spark: Optional SparkSession. If not provided, a new one will be created.
        
    Returns:
        Spark DataFrame containing the resources.
    """
    # Create SparkSession if not provided
    if spark is None:
        spark = SparkSession.builder.getOrCreate()
    
    # Create schema with required fields
    schema = StructType([
        StructField("json_data", StringType(), True),
        StructField("ingest_timestamp", TimestampType(), True),
        StructField("ingest_date", DateType(), True),
        StructField("resource_type", StringType(), True),
        StructField("resource_id", StringType(), True),
        StructField("last_updated", StringType(), True),
    ])
    
    if not resources:
        # Return empty DataFrame with schema
        return spark.createDataFrame([], schema)
    
    # Convert resources to rows with metadata
    rows = []
    current_time = datetime.now()
    current_date = current_time.date()
    
    for resource in resources:
        # Extract key fields
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "")
        last_updated = resource.get("meta", {}).get("lastUpdated", "")
        
        # Create row
        rows.append((
            json.dumps(resource),
            current_time,
            current_date,
            resource_type,
            resource_id,
            last_updated
        ))
    
    # Create DataFrame
    df = spark.createDataFrame(rows, schema)
    
    # Try to add FHIR metadata column using Pathling if available
    try:
        # Import Pathling
        from pathling.functions import to_fhir

        # Add the FHIR metadata column using Pathling
        df = df.withColumn("fhir", to_fhir("json_data"))
        logger.info("Added Pathling FHIR column")
    except ImportError:
        logger.warning("Pathling not available, skipping FHIR column")
    except Exception as e:
        logger.warning(f"Error adding Pathling FHIR column: {str(e)}")
    
    return df


def last_watermark(ctx, default="1900-01-01T00:00:00Z"):
    """Get the last watermark from the transform context.
    
    Args:
        ctx: Transform context.
        default: Default watermark if none is found.
        
    Returns:
        Watermark string in ISO 8601 format.
    """
    return ctx.get_last_watermark() or default


def find_max_updated_time(resources: List[Dict[str, Any]]) -> Optional[str]:
    """Find the maximum lastUpdated value from a list of resources.
    
    Args:
        resources: List of FHIR resources.
        
    Returns:
        Maximum lastUpdated value, or None if not found.
    """
    update_times = []
    for resource in resources:
        meta = resource.get("meta", {})
        last_updated = meta.get("lastUpdated")
        if last_updated:
            update_times.append(last_updated)
    
    if update_times:
        return max(update_times)
    return None


def extract_all_resources(
    client: Optional[FHIRClient] = None,
    resource_types: Optional[List[str]] = None,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
    last_updated_since: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Extract multiple FHIR resource types from the Epic API.
    
    Args:
        client: Optional FHIR client. If not provided, a new one will be created.
        resource_types: List of resource types to extract. If not provided, uses environment variable.
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve per resource type.
        last_updated_since: Optional timestamp to fetch only resources updated since.
        
    Returns:
        Dictionary mapping resource types to lists of resources.
    """
    # Create client if not provided
    if client is None:
        client = create_fhir_client()
    
    # Use provided resource types or get from environment
    if resource_types is None:
        resource_types = get_resource_list()
    
    # Default params
    params = params or {}
    
    # Extract resources for each type
    result = {}
    for resource_type in resource_types:
        try:
            resources = extract_resource(
                client=client,
                resource_type=resource_type,
                params=params,
                max_pages=max_pages,
                last_updated_since=last_updated_since,
            )
            result[resource_type] = resources
        except Exception as e:
            logger.error(f"Failed to extract {resource_type}", error=str(e))
            result[resource_type] = []
    
    return result 