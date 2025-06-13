from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional

import pyspark.sql
from pyspark.sql import DataFrame

from fhir_pipeline.transforms.yaml_mappers import apply_mapping


class BaseTransformer(ABC):
    """
    Abstract base class for FHIR resource transformers.
    
    Provides hooks for pre/post-normalization steps and applies
    YAML-driven mapping to flatten FHIR resources in a standardized way.
    """
    
    def __init__(self, spark: pyspark.sql.SparkSession, resource_type: str, mapping_spec: Dict[str, Any]):
        """
        Initialize the transformer.
        
        Args:
            spark: Active SparkSession
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            mapping_spec: Dictionary containing column mapping specifications loaded from YAML
        """
        self.spark = spark
        self.resource_type = resource_type
        self.mapping_spec = mapping_spec
        self.logger = logging.getLogger(f"transformer.{resource_type.lower()}")
    
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Transform a DataFrame containing FHIR resources into a normalized format.
        
        Args:
            df: DataFrame containing FHIR resources in the 'resource' column
            
        Returns:
            DataFrame with flattened, normalized structure
        """
        self.logger.info(f"Transforming {self.resource_type} resources")
        
        # Record input count for data loss tracking
        input_count = df.count()
        self.logger.info(f"Input record count: {input_count}")
        
        # Apply pre-normalization hooks
        df = self.pre_normalize(df)
        
        # Apply the mapping from YAML spec
        df = self._apply_mapping(df)
        
        # Apply post-normalization hooks
        df = self.post_normalize(df)
        
        # Calculate data loss metrics
        output_count = df.count()
        loss_pct = 0 if input_count == 0 else (input_count - output_count) / input_count * 100
        
        self.logger.info(f"Output record count: {output_count}")
        self.logger.info(f"Loss percentage: {loss_pct:.2f}%")
        
        # Fail if loss exceeds threshold (5%)
        if loss_pct > 5:
            self.logger.error(f"Data loss exceeds threshold: {loss_pct:.2f}%")
            raise ValueError(f"Data loss threshold exceeded: {loss_pct:.2f}% (threshold: 5%)")
            
        return df
    
    def pre_normalize(self, df: DataFrame) -> DataFrame:
        """
        Hook for operations to be performed before applying mapping.
        Override this method to add custom preprocessing logic.
        
        Args:
            df: Input DataFrame with raw FHIR resources
            
        Returns:
            Preprocessed DataFrame
        """
        return df
    
    def post_normalize(self, df: DataFrame) -> DataFrame:
        """
        Hook for operations to be performed after applying mapping.
        Override this method to add custom postprocessing logic.
        
        Args:
            df: DataFrame after applying YAML mapping
            
        Returns:
            Postprocessed DataFrame
        """
        # Run validation if configured
        if self.mapping_spec.get("validate", True):
            from fhir_pipeline.validation.core import ValidationContext
            validation_context = ValidationContext(self.resource_type, df)
            df = validation_context.validate()
            
        return df
    
    def _apply_mapping(self, df: DataFrame) -> DataFrame:
        """
        Apply the mapping specification from YAML to the DataFrame.
        
        Args:
            df: DataFrame with raw FHIR resources
            
        Returns:
            DataFrame with columns based on the mapping specification
        """
        return apply_mapping(df, self.mapping_spec) 