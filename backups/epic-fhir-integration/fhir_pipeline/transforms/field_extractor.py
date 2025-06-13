"""
Field extraction component for FHIR data transformations.
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, expr

from fhir_pipeline.transforms.base import BaseTransformer


class FieldExtractor(BaseTransformer):
    """
    Extracts a single field from FHIR resources and creates a new column.
    
    Supports nested fields and array indexing using dot notation and square brackets.
    """
    
    def __init__(self, spark, source_field, target_field=None):
        """
        Initialize the field extractor.
        
        Args:
            spark: SparkSession
            source_field: Path to extract (e.g., "name[0].family")
            target_field: Column name for the extracted value, defaults to source_field if not specified
        """
        super().__init__(spark)
        self.source_field = source_field
        self.target_field = target_field or source_field
    
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Extract the field from the input DataFrame.
        
        Args:
            df: Input DataFrame with FHIR resources
            
        Returns:
            DataFrame with extracted field as a new column
        """
        # Construct the extraction expression
        source_path = self.source_field
        
        # Handle nested extraction with getField and array indexing
        if '[' in source_path:
            # Replace standard array notation with getItem calls
            import re
            # e.g., "name[0].family" becomes extracting name, then getItem(0), then getField(family)
            parts = re.split(r'\.|\[|\]', source_path)
            parts = [p for p in parts if p]  # Filter empty parts
            
            # Start with the base column
            expr_str = parts[0]
            
            # Build up the accessor chain
            for i in range(1, len(parts)):
                part = parts[i]
                if part.isdigit():
                    # Array index
                    expr_str = f"getItem({expr_str}, {part})"
                else:
                    # Field access
                    expr_str = f"getField({expr_str}, '{part}')"
            
            # Create the column expression
            return df.withColumn(self.target_field, expr(expr_str))
        else:
            # Simple field extraction
            return df.withColumn(self.target_field, col(source_path)) 