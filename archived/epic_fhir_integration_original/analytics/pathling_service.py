"""
Pathling service for FHIR analytics.

This module provides a service for performing analytics on FHIR data using Pathling.
Pathling is a powerful FHIR analytics tool that supports aggregation, filtering,
and complex queries on FHIR data.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from fhir.resources.resource import Resource as FHIRResource

try:
    import pathling
    from pathling import PathlingContext
    PATHLING_AVAILABLE = True
except ImportError:
    PATHLING_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class PathlingService:
    """
    Service for performing analytics on FHIR data using Pathling.
    
    This service provides methods for:
    - Setting up a Pathling context
    - Loading FHIR resources into Pathling
    - Executing aggregate queries
    - Performing population-level analytics
    """
    
    def __init__(self, spark_session=None):
        """
        Initialize the Pathling service.
        
        Args:
            spark_session: Optional Spark session to use with Pathling
                If not provided, a local session will be created
        """
        if not PATHLING_AVAILABLE:
            raise ImportError(
                "Pathling is not available. Install it with 'pip install pathling>=6.3.0'"
            )
        
        # Initialize the Pathling context
        self.spark = spark_session
        self.context = self._create_pathling_context()
        self.resource_paths = {}  # Maps resource types to their locations
        
    def _create_pathling_context(self):
        """
        Create a Pathling context.
        
        Returns:
            PathlingContext: The Pathling context
        """
        try:
            if self.spark:
                # Use provided Spark session
                return PathlingContext.create(self.spark)
            else:
                # Create a local Pathling context
                return PathlingContext.create()
        except Exception as e:
            logger.error(f"Error creating Pathling context: {e}")
            raise
    
    def load_resources(self, 
                      resources: List[Union[Dict, FHIRResource]], 
                      resource_type: Optional[str] = None) -> str:
        """
        Load FHIR resources into Pathling.
        
        Args:
            resources: List of FHIR resources as dictionaries or FHIR resource models
            resource_type: Optional resource type if not inferrable from the resources
                
        Returns:
            str: Path to the loaded resources in Pathling
        """
        try:
            # Convert resources to dictionaries if needed
            resource_dicts = []
            for resource in resources:
                if hasattr(resource, "model_dump"):
                    resource_dicts.append(resource.model_dump())
                elif hasattr(resource, "dict"):
                    resource_dicts.append(resource.dict())
                else:
                    resource_dicts.append(resource)
            
            # Determine resource type if not provided
            if not resource_type and resource_dicts:
                resource_type = resource_dicts[0].get("resourceType")
                
            if not resource_type:
                raise ValueError("Resource type must be provided or inferrable from resources")
                
            # Create a temporary directory for the resources
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, f"{resource_type}.ndjson")
            
            # Write resources to the temporary directory as NDJSON
            with open(temp_path, "w") as f:
                for resource in resource_dicts:
                    f.write(f"{resource}\n")
                    
            # Load the resources into Pathling
            encoded_dataset = self.context.encode_bundle(temp_path)
            
            # Store the path to the resources
            self.resource_paths[resource_type] = encoded_dataset
            
            return encoded_dataset
            
        except Exception as e:
            logger.error(f"Error loading resources into Pathling: {e}")
            raise
    
    def aggregate(self, 
                 resource_type: str, 
                 aggregations: List[str], 
                 filters: Optional[List[str]] = None, 
                 groupings: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Perform an aggregate query on FHIR resources.
        
        Args:
            resource_type: Type of resource to query (e.g., "Patient", "Observation")
            aggregations: List of Pathling aggregation expressions
            filters: Optional list of Pathling filter expressions
            groupings: Optional list of Pathling grouping expressions
                
        Returns:
            pd.DataFrame: Results of the aggregate query
        """
        try:
            # Check if resources are loaded
            if resource_type not in self.resource_paths:
                raise ValueError(f"Resources of type {resource_type} not loaded")
                
            # Create the aggregate query
            query = self.context.aggregate(
                data_set=self.resource_paths[resource_type],
                aggregations=aggregations,
                filters=filters or [],
                groupings=groupings or []
            )
            
            # Execute the query and convert to DataFrame
            result = query.collect()
            return pd.DataFrame(result)
            
        except Exception as e:
            logger.error(f"Error executing aggregate query: {e}")
            raise
    
    def extract_dataset(self,
                       resource_type: str,
                       columns: List[str],
                       filters: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract a dataset from FHIR resources using Pathling's extract operation.
        
        Args:
            resource_type: Type of resource to extract from
            columns: List of FHIRPath expressions for columns to extract
            filters: Optional list of Pathling filter expressions
                
        Returns:
            pd.DataFrame: Extracted dataset
        """
        try:
            # Check if resources are loaded
            if resource_type not in self.resource_paths:
                raise ValueError(f"Resources of type {resource_type} not loaded")
                
            # Create the extract query
            query = self.context.extract(
                data_set=self.resource_paths[resource_type],
                columns=columns,
                filters=filters or []
            )
            
            # Execute the query and convert to DataFrame
            result = query.collect()
            return pd.DataFrame(result)
            
        except Exception as e:
            logger.error(f"Error executing extract query: {e}")
            raise
    
    def calculate_measure(self,
                         resource_type: str,
                         population_filters: Dict[str, str],
                         stratifiers: Optional[List[str]] = None) -> Dict:
        """
        Calculate a measure using Pathling.
        
        Args:
            resource_type: Type of resource to measure
            population_filters: Dictionary mapping population names to filter expressions
            stratifiers: Optional list of stratification expressions
                
        Returns:
            Dict: Measure calculation results
        """
        try:
            # Check if resources are loaded
            if resource_type not in self.resource_paths:
                raise ValueError(f"Resources of type {resource_type} not loaded")
                
            # Calculate the measure
            result = self.context.measure(
                data_set=self.resource_paths[resource_type],
                population_expressions=population_filters,
                stratifiers=stratifiers or []
            )
            
            return result.collect()
            
        except Exception as e:
            logger.error(f"Error calculating measure: {e}")
            raise
    
    def close(self):
        """
        Close the Pathling context and clean up resources.
        """
        try:
            if hasattr(self.context, "close"):
                self.context.close()
            
            # Clean up temporary directories
            for resource_path in self.resource_paths.values():
                if isinstance(resource_path, str) and os.path.exists(resource_path):
                    temp_dir = os.path.dirname(resource_path)
                    if os.path.exists(temp_dir):
                        try:
                            import shutil
                            shutil.rmtree(temp_dir)
                        except Exception as e:
                            logger.warning(f"Error cleaning up temporary directory: {e}")
        except Exception as e:
            logger.error(f"Error closing Pathling context: {e}") 