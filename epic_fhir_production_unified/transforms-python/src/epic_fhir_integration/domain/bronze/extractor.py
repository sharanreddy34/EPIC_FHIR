"""
FHIR resource extraction module for the bronze layer.

This module provides functions for extracting FHIR resources from the Epic API
and writing them to Bronze datasets in Foundry.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, TYPE_CHECKING

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, SparkSession

# Conditionally import Foundry-specific modules
# These will only be imported when actually used, not at module load time
try:
    from transforms.api import transform_df, incremental, Input, Output
    FOUNDRY_AVAILABLE = True
except ImportError:
    FOUNDRY_AVAILABLE = False
    # Create dummy types for type checking
    if TYPE_CHECKING:
        from typing import Callable
        def transform_df(*args, **kwargs): ...
        def incremental(*args, **kwargs): ...
        class Input: ...
        class Output: ...

# Type hints but with lazy loading
if TYPE_CHECKING:
    from epic_fhir_integration.api_clients.fhir_client import FHIRClient

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


def extract_resources(
    client: Optional["FHIRClient"] = None,
    resource_type: str = "Patient",
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
) -> List[Dict[str, Any]]:
    """Extract FHIR resources from the Epic API.
    
    Args:
        client: Optional FHIR client. If not provided, a new one will be created.
        resource_type: FHIR resource type (e.g., "Patient", "Observation").
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve.
        
    Returns:
        List of FHIR resources.
    """
    # Create client if not provided
    if client is None:
        # Import client only when needed to avoid circular imports
        from epic_fhir_integration.api_clients.fhir_client import create_fhir_client
        client = create_fhir_client()
    
    # Default params
    params = params or {}
    
    logger.info("Extracting FHIR resources", 
               resource_type=resource_type, 
               params=params)
    
    # Extract resources
    resources = client.get_all_resources(
        resource_type=resource_type,
        params=params,
        max_pages=max_pages,
    )
    
    logger.info("Extracted FHIR resources", 
               resource_type=resource_type, 
               count=len(resources))
    
    return resources


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
    
    # Convert resources to JSON strings
    json_strings = [json.dumps(resource) for resource in resources]
    
    # Create DataFrame with a single column
    df = spark.createDataFrame([(s,) for s in json_strings], ["json_data"])
    
    # Add metadata columns
    df = df.withColumn("ingest_timestamp", F.current_timestamp())
    df = df.withColumn("ingest_date", F.current_date())
    
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


def extract_patient_resources(
    client=None,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
    last_updated_since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract Patient resources from the Epic API.
    
    Args:
        client: Optional FHIR client. If not provided, a new one will be created.
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve.
        last_updated_since: Optional timestamp to fetch only resources updated since.
        
    Returns:
        List of Patient resources.
    """
    # Default params
    params = params or {}
    
    # Add last updated parameter if provided
    if last_updated_since:
        params["_lastUpdated"] = f"gt{last_updated_since}"
    
    return extract_resources(
        client=client,
        resource_type="Patient",
        params=params,
        max_pages=max_pages,
    )


def extract_observation_resources(
    client=None,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
    last_updated_since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract Observation resources from the Epic API.
    
    Args:
        client: Optional FHIR client. If not provided, a new one will be created.
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve.
        last_updated_since: Optional timestamp to fetch only resources updated since.
        
    Returns:
        List of Observation resources.
    """
    # Default params
    params = params or {}
    
    # Add last updated parameter if provided
    if last_updated_since:
        params["_lastUpdated"] = f"gt{last_updated_since}"
    
    return extract_resources(
        client=client,
        resource_type="Observation",
        params=params,
        max_pages=max_pages,
    )


def extract_encounter_resources(
    client=None,
    params: Optional[Dict[str, Any]] = None,
    max_pages: int = 50,
    last_updated_since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract Encounter resources from the Epic API.
    
    Args:
        client: Optional FHIR client. If not provided, a new one will be created.
        params: Optional search parameters.
        max_pages: Maximum number of pages to retrieve.
        last_updated_since: Optional timestamp to fetch only resources updated since.
        
    Returns:
        List of Encounter resources.
    """
    # Default params
    params = params or {}
    
    # Add last updated parameter if provided
    if last_updated_since:
        params["_lastUpdated"] = f"gt{last_updated_since}"
    
    return extract_resources(
        client=client,
        resource_type="Encounter",
        params=params,
        max_pages=max_pages,
    ) 