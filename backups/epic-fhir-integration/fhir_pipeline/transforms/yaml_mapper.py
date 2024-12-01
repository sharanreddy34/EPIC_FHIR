"""
YAML-based mapper for transforming FHIR resources.
"""

import os
import yaml
from typing import Dict, Any, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from fhir_pipeline.transforms.base import BaseTransformer
from fhir_pipeline.transforms.path_extractor import PathExtractor


class YAMLMapper(BaseTransformer):
    """
    Transforms FHIR resources based on a YAML configuration file.
    
    The YAML file should contain mappings from source fields to target fields,
    allowing for complex transformation of nested FHIR structures into
    a flattened, normalized format.
    """
    
    def __init__(self, spark, config_path: str):
        """
        Initialize the YAML mapper.
        
        Args:
            spark: SparkSession
            config_path: Path to the YAML configuration file
        """
        super().__init__(spark)
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load the YAML configuration file.
        
        Returns:
            Dictionary containing the parsed YAML configuration
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Transform the input DataFrame according to the YAML mapping.
        
        Args:
            df: Input DataFrame with FHIR resources
            
        Returns:
            Transformed DataFrame with columns mapped according to configuration
        """
        # Extract mappings from the configuration
        mappings = self.config.get("mappings", [])
        
        # Create a dictionary of source to target mappings
        path_mapping = {}
        for mapping in mappings:
            source = mapping.get("source")
            target = mapping.get("target")
            if source and target:
                path_mapping[source] = target
        
        # Use the PathExtractor to apply all mappings
        path_extractor = PathExtractor(
            spark=self.spark,
            path_mapping=path_mapping
        )
        result_df = path_extractor.transform(df)
        
        # If the configuration specifies to drop original columns, do so
        if self.config.get("drop_original_columns", False):
            # Keep only the target columns
            keep_columns = list(path_mapping.values())
            result_df = result_df.select(*keep_columns)
        
        return result_df
    
    @classmethod
    def from_string(cls, spark, yaml_string: str) -> 'YAMLMapper':
        """
        Create a mapper from a YAML string.
        
        Args:
            spark: SparkSession
            yaml_string: YAML configuration as a string
            
        Returns:
            YAMLMapper instance
        """
        import tempfile
        
        # Write the YAML to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_string)
            temp_path = f.name
        
        # Create the mapper from the temporary file
        try:
            mapper = cls(spark, temp_path)
            return mapper
        finally:
            # Clean up the temporary file
            os.unlink(temp_path) 