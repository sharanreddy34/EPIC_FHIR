"""
Path extraction component for FHIR data transformations.
"""

from typing import Dict

from pyspark.sql import DataFrame

from fhir_pipeline.transforms.base import BaseTransformer
from fhir_pipeline.transforms.field_extractor import FieldExtractor


class PathExtractor(BaseTransformer):
    """
    Extracts multiple fields from FHIR resources based on a mapping.
    
    Takes a dictionary mapping source paths to target column names
    and creates multiple columns in a single pass.
    """
    
    def __init__(self, spark, path_mapping: Dict[str, str]):
        """
        Initialize the path extractor.
        
        Args:
            spark: SparkSession
            path_mapping: Dictionary mapping source paths to target column names
                          e.g., {"name[0].family": "last_name", "gender": "sex"}
        """
        super().__init__(spark)
        self.path_mapping = path_mapping
    
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Extract multiple fields from the input DataFrame.
        
        Args:
            df: Input DataFrame with FHIR resources
            
        Returns:
            DataFrame with all extracted fields as new columns
        """
        result_df = df
        
        # Apply field extraction for each path in the mapping
        for source_path, target_field in self.path_mapping.items():
            field_extractor = FieldExtractor(
                spark=self.spark,
                source_field=source_path,
                target_field=target_field
            )
            result_df = field_extractor.transform(result_df)
        
        return result_df 