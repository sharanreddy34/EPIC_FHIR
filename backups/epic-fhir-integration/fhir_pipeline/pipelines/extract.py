"""
FHIR Extract Pipeline

This module provides the FHIRExtractPipeline class for extracting data from a FHIR API
and saving it to a local or distributed storage system.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, MapType

from fhir_pipeline.io.fhir_client import FHIRClient
from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.auth.token_manager import TokenManager

logger = logging.getLogger(__name__)

class FHIRExtractPipeline:
    """
    A pipeline for extracting FHIR resources from an API and saving them to 
    a Spark DataFrame and/or local files.
    """
    
    def __init__(
        self,
        spark: SparkSession,
        fhir_client: Optional[FHIRClient] = None,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        private_key: Optional[str] = None,
        output_dir: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize the FHIR extraction pipeline.
        
        Args:
            spark: SparkSession for creating DataFrames
            fhir_client: Optional FHIRClient instance
            base_url: FHIR API base URL (required if fhir_client not provided)
            client_id: JWT client ID (required if fhir_client not provided)
            private_key: JWT private key (required if fhir_client not provided)
            output_dir: Directory to save extracted resources to
            max_retries: Maximum number of retries for failed requests
            timeout: Timeout in seconds for API requests
        """
        self.spark = spark
        self.output_dir = output_dir
        
        if fhir_client:
            self.fhir_client = fhir_client
        elif base_url and client_id and private_key:
            # Create JWT client
            jwt_client = JWTClient(client_id=client_id, private_key=private_key)
            
            # Create token manager
            token_manager = TokenManager(jwt_client)
            
            # Create FHIR client
            self.fhir_client = FHIRClient(
                base_url=base_url,
                token_manager=token_manager,
                max_retries=max_retries,
                timeout=timeout
            )
        else:
            raise ValueError("Either fhir_client or (base_url, client_id, private_key) must be provided")
        
        # Create output directory if needed
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
    def extract_resource(self, resource_type: str, search_params: Dict[str, str] = None) -> DataFrame:
        """
        Extract resources of a specific type from the FHIR API.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            search_params: Additional search parameters
            
        Returns:
            DataFrame containing the extracted resources
        """
        logger.info(f"Extracting {resource_type} resources")
        start_time = datetime.now()
        
        # Initialize search parameters
        params = search_params or {}
        
        # Get resources using search_resource method instead of get_bundle
        resources = []
        for bundle in self.fhir_client.search_resource(resource_type, params):
            if "entry" in bundle:
                for entry in bundle["entry"]:
                    if "resource" in entry:
                        resources.append(entry["resource"])
        
        # Create DataFrame from resources
        if resources:
            # Convert resources to JSON strings
            json_rdd = self.spark.sparkContext.parallelize([json.dumps(r) for r in resources])
            
            # Create DataFrame from JSON
            df = self.spark.read.json(json_rdd)
            
            # Save to disk if output directory is specified
            if self.output_dir:
                output_path = os.path.join(self.output_dir, resource_type)
                os.makedirs(output_path, exist_ok=True)
                df.write.mode("overwrite").parquet(output_path)
                
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Extracted {len(resources)} {resource_type} resources in {elapsed:.2f} seconds")
            
            return df
        else:
            # Create empty DataFrame with appropriate schema
            df = self._create_empty_dataframe_for_resource(resource_type)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"No {resource_type} resources found. Execution time: {elapsed:.2f} seconds")
            
            return df
    
    def extract_resources(self, resource_types: List[str], search_params: Dict[str, str] = None) -> Dict[str, DataFrame]:
        """
        Extract multiple resource types from the FHIR API.
        
        Args:
            resource_types: List of FHIR resource types to extract
            search_params: Search parameters to apply to each resource type
            
        Returns:
            Dictionary mapping resource types to their respective DataFrames
        """
        results = {}
        
        for resource_type in resource_types:
            results[resource_type] = self.extract_resource(resource_type, search_params)
            
        return results
    
    def _create_empty_dataframe_for_resource(self, resource_type: str) -> DataFrame:
        """
        Create an empty DataFrame with the appropriate schema for a given resource type.
        
        Args:
            resource_type: FHIR resource type
            
        Returns:
            Empty DataFrame with resource schema
        """
        # Define a basic schema that works for all FHIR resources
        schema = StructType([
            StructField("id", StringType(), True),
            StructField("resourceType", StringType(), True)
        ])
        
        # Add resource-specific fields if needed
        if resource_type == "Patient":
            schema.add(StructField("identifier", ArrayType(MapType(StringType(), StringType())), True))
            schema.add(StructField("name", ArrayType(MapType(StringType(), StringType())), True))
            schema.add(StructField("gender", StringType(), True))
            schema.add(StructField("birthDate", StringType(), True))
        elif resource_type == "Observation":
            schema.add(StructField("status", StringType(), True))
            schema.add(StructField("code", MapType(StringType(), StringType()), True))
            schema.add(StructField("subject", MapType(StringType(), StringType()), True))
            schema.add(StructField("valueQuantity", MapType(StringType(), StringType()), True))
            schema.add(StructField("effectiveDateTime", StringType(), True))
        
        # Create empty DataFrame with schema
        return self.spark.createDataFrame([], schema) 