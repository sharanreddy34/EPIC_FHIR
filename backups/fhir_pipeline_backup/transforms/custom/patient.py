import logging
from typing import Dict, Any, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, udf
from pyspark.sql.types import StringType

from fhir_pipeline.transforms.base import BaseTransformer

logger = logging.getLogger(__name__)

class Transformer(BaseTransformer):
    """
    Custom Patient resource transformer.
    
    Extends the generic BaseTransformer to add:
    1. Sentence summarization for demographic information
    2. Special handling of name formats
    3. Additional validation specific to Patient resources
    """
    
    def pre_normalize(self, df: DataFrame) -> DataFrame:
        """
        Pre-normalization hook for Patient resources.
        
        Args:
            df: DataFrame with raw FHIR Patient resources
            
        Returns:
            Preprocessed DataFrame
        """
        logger.info("Applying Patient-specific pre-normalization")
        
        # Just return the base DataFrame for now - can add custom logic as needed
        return df
    
    def post_normalize(self, df: DataFrame) -> DataFrame:
        """
        Post-normalization hook for Patient resources.
        
        Adds a demographic_summary column containing a formatted sentence about the patient.
        
        Args:
            df: DataFrame with normalized Patient columns
            
        Returns:
            Enhanced DataFrame with additional summary columns
        """
        logger.info("Applying Patient-specific post-normalization")
        
        # Create a demographic summary as a readable sentence
        @udf(StringType())
        def generate_demographic_summary(name_text, gender, birth_date, address_city, address_state):
            parts = []
            
            if name_text:
                parts.append(f"{name_text}")
            
            if gender and birth_date:
                parts.append(f"is a {gender} patient born on {birth_date}")
            elif gender:
                parts.append(f"is a {gender} patient")
            elif birth_date:
                parts.append(f"was born on {birth_date}")
            
            if address_city and address_state:
                parts.append(f"from {address_city}, {address_state}")
            elif address_city:
                parts.append(f"from {address_city}")
            elif address_state:
                parts.append(f"from {address_state}")
            
            if not parts:
                return None
                
            return " ".join(parts) + "."
        
        # Apply the UDF to create the summary
        df = df.withColumn(
            "demographic_summary",
            generate_demographic_summary(
                col("name_text"),
                col("gender"),
                col("birth_date"),
                col("address_city"),
                col("address_state")
            )
        )
        
        # Format names properly if given and family names are available
        conditions = [
            (col("name_given").isNotNull() & col("name_family").isNotNull() & col("name_text").isNull())
        ]
        
        if any(c in df.columns for c in ["name_given", "name_family"]):
            from pyspark.sql.functions import concat_ws
            df = df.withColumn(
                "name_text",
                concat_ws(" ", col("name_given"), col("name_family"))
            )
        
        # Call the base class validation logic
        df = super().post_normalize(df)
        
        return df 