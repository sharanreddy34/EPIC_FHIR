import logging
from typing import Dict, Any, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from fhir_pipeline.transforms.base import BaseTransformer

logger = logging.getLogger(__name__)

class Transformer(BaseTransformer):
    """
    Custom transformer for Patient resources.
    
    Extends the BaseTransformer with specialized logic for Patient resources,
    including:
    
    1. Adding a patient_summary_text field combining demographics
    2. Validating and standardizing contact information
    3. Computing age-related fields 
    """
    
    def post_normalize(self, df: DataFrame) -> DataFrame:
        """
        Apply patient-specific post-processing logic after YAML mapping.
        
        Args:
            df: DataFrame with mapped Patient data
            
        Returns:
            Enhanced Patient DataFrame with additional fields
        """
        # First, let the parent class's post_normalize run
        # This handles validation if enabled in the mapping spec
        df = super().post_normalize(df)
        
        # Generate enhanced patient_summary_text if needed
        if 'patient_summary_text' in df.columns and 'name_text' in df.columns:
            # Define a UDF to generate a more comprehensive patient summary
            @F.udf(StringType())
            def enhanced_patient_summary(name, birth_date, gender):
                parts = []
                if name:
                    parts.append(f"Patient: {name}")
                if birth_date:
                    parts.append(f"DOB: {birth_date}")
                if gender:
                    parts.append(f"Gender: {gender}")
                
                if not parts:
                    return None
                return ". ".join(parts)
            
            # Apply the UDF to replace any empty summaries
            df = df.withColumn(
                "patient_summary_text",
                F.when(
                    F.col("patient_summary_text").isNull() | (F.col("patient_summary_text") == ""),
                    enhanced_patient_summary(
                        F.col("name_text"), 
                        F.col("birth_date"), 
                        F.col("gender")
                    )
                ).otherwise(F.col("patient_summary_text"))
            )
        
        # Standardize phone numbers (simple example)
        if 'phone' in df.columns:
            df = df.withColumn(
                "phone_standardized",
                F.regexp_replace(F.col("phone"), "[^0-9]", "")
            )
        
        # Calculate age if birth_date is present
        if 'birth_date' in df.columns:
            df = df.withColumn(
                "age_years", 
                F.floor(F.months_between(F.current_date(), F.to_date(F.col("birth_date"))) / 12)
            )
            
            # Add age group for demographics
            df = df.withColumn(
                "age_group",
                F.when(F.col("age_years") < 18, "pediatric")
                 .when(F.col("age_years") < 65, "adult")
                 .otherwise("senior")
            )
        
        self.logger.info("Applied Patient-specific post-processing")
        return df
    
    def pre_normalize(self, df: DataFrame) -> DataFrame:
        """
        Apply patient-specific pre-processing logic before YAML mapping.
        
        Args:
            df: DataFrame with raw Patient resources
            
        Returns:
            Pre-processed Patient DataFrame
        """
        # Apply parent class pre-processing
        df = super().pre_normalize(df)
        
        # Add resource-specific pre-processing here if needed
        # For example, flag patients with multiple identifiers
        
        return df 