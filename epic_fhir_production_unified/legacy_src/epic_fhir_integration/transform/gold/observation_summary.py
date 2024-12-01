"""
Observation summary transformer for the Gold layer.

This module transforms Observation data from the Silver layer into the Gold layer.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lit, array, struct, to_date, to_timestamp, 
    when, expr, concat, split, first, last
)

from epic_fhir_integration.schemas.gold import OBSERVATION_SCHEMA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObservationSummary:
    """Transformer for Observation resources to the Gold layer."""
    
    def __init__(
        self,
        spark: SparkSession,
        silver_path: Union[str, Path] = None,
        gold_path: Union[str, Path] = None,
    ):
        """Initialize a new Observation summary transformer.
        
        Args:
            spark: Spark session.
            silver_path: Path to the silver layer data.
            gold_path: Path to the gold layer output.
        """
        self.spark = spark
        
        # Set default paths if not provided
        if silver_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            silver_path = base_dir / "output" / "silver"
        elif isinstance(silver_path, str):
            silver_path = Path(silver_path)
        
        if gold_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            gold_path = base_dir / "output" / "gold"
        elif isinstance(gold_path, str):
            gold_path = Path(gold_path)
        
        self.silver_path = silver_path
        self.gold_path = gold_path
        
        # Create gold output directory
        (self.gold_path / "observation").mkdir(parents=True, exist_ok=True)
    
    def load_silver_data(self) -> DataFrame:
        """Load Observation data from the Silver layer.
        
        Returns:
            DataFrame containing Silver layer Observation data.
        """
        silver_observation_path = self.silver_path / "observation"
        
        if not silver_observation_path.exists():
            raise ValueError(f"Silver layer path does not exist: {silver_observation_path}")
        
        logger.info(f"Loading Observation data from Silver layer: {silver_observation_path}")
        df = self.spark.read.parquet(str(silver_observation_path))
        
        return df
    
    def transform(self, silver_df: Optional[DataFrame] = None) -> DataFrame:
        """Transform Silver layer Observation data to Gold layer format.
        
        Args:
            silver_df: DataFrame containing Silver layer Observation data.
                      If not provided, it will be loaded from the Silver layer.
                      
        Returns:
            DataFrame in Gold layer format.
        """
        # Load silver data if not provided
        if silver_df is None:
            silver_df = self.load_silver_data()
        
        logger.info("Transforming Observation data to Gold layer format")
        
        # Extract and transform observation data
        gold_df = silver_df.select(
            # Required fields
            col("id").alias("observation_id"),
            
            # Extract patient ID from subject reference
            when(col("subject.reference").isNotNull(),
                 expr("substring(subject.reference, 9)") # Assumes format "Patient/123"
            ).alias("patient_id"),
            
            # Extract encounter ID from encounter reference
            when(col("encounter.reference").isNotNull(),
                 expr("substring(encounter.reference, 11)") # Assumes format "Encounter/123"
            ).alias("encounter_id"),
            
            # Observation date and time
            to_timestamp(col("effectiveDateTime")).alias("observation_datetime"),
            
            # Coding information
            when(col("code.coding").isNotNull(),
                 col("code.coding[0].code")
            ).alias("observation_code"),
            
            when(col("code.coding").isNotNull(),
                 col("code.coding[0].system")
            ).alias("observation_code_system"),
            
            when(col("code.coding").isNotNull(),
                 col("code.coding[0].display")
            ).alias("observation_code_display"),
            
            # Category
            when(col("category").isNotNull(),
                 expr("transform(category, x -> x.coding[0].display)[0]")
            ).alias("observation_category"),
            
            # Status
            col("status").alias("observation_status"),
            
            # Observation values - extract the right one based on type
            when(col("valueString").isNotNull(), col("valueString"))
            .when(col("valueCodeableConcept").isNotNull(), col("valueCodeableConcept.text"))
            .otherwise(expr("null")).alias("observation_value_string"),
            
            when(col("valueQuantity.value").isNotNull(), col("valueQuantity.value"))
            .when(col("valueInteger").isNotNull(), col("valueInteger").cast("double"))
            .when(col("valueDecimal").isNotNull(), col("valueDecimal"))
            .otherwise(expr("null")).alias("observation_value_numeric"),
            
            when(col("valueQuantity.unit").isNotNull(), col("valueQuantity.unit"))
            .when(col("valueQuantity.code").isNotNull(), col("valueQuantity.code"))
            .otherwise(expr("null")).alias("observation_value_unit"),
            
            when(col("valueCodeableConcept.coding").isNotNull(),
                 col("valueCodeableConcept.coding[0].code")
            ).alias("observation_value_coded"),
            
            when(col("valueBoolean").isNotNull(), col("valueBoolean"))
            .otherwise(expr("null")).alias("observation_value_boolean"),
            
            # Interpretation
            when(col("interpretation").isNotNull(),
                 expr("transform(interpretation, x -> x.coding[0].display)[0]")
            ).alias("observation_interpretation"),
            
            # Reference range
            when(col("referenceRange").isNotNull(),
                 expr("transform(referenceRange, x -> x.low.value)[0]")
            ).cast("double").alias("reference_range_low"),
            
            when(col("referenceRange").isNotNull(),
                 expr("transform(referenceRange, x -> x.high.value)[0]")
            ).cast("double").alias("reference_range_high"),
            
            when(col("referenceRange").isNotNull(),
                 expr("transform(referenceRange, x -> x.text)[0]")
            ).alias("reference_range_text"),
            
            # Performer
            when(col("performer").isNotNull(),
                 expr("transform(performer, x -> CASE WHEN x.reference LIKE 'Practitioner/%' THEN substring(x.reference, 14) ELSE NULL END)[0]")
            ).alias("performer_id"),
            
            when(col("performer").isNotNull(),
                 expr("transform(performer, x -> x.display)[0]")
            ).alias("performer_name"),
            
            lit("Practitioner").alias("performer_type"),
            
            # Device information
            when(col("device.reference").isNotNull(),
                 expr("substring(device.reference, 8)") # Assumes format "Device/123"
            ).alias("device_id"),
            
            when(col("device.display").isNotNull(),
                 col("device.display")
            ).alias("device_name"),
            
            # Note
            when(col("note").isNotNull(),
                 expr("transform(note, x -> x.text)[0]")
            ).alias("note"),
            
            # Related observations
            when(col("related").isNotNull(),
                 expr("transform(related, x -> struct(substring(x.target.reference, 13) as related_id, x.type as relationship_type))")
            ).otherwise(array()).alias("related_observations"),
            
            # Metadata
            to_timestamp(expr("meta.lastUpdated")).alias("created_at"),
            to_timestamp(expr("meta.lastUpdated")).alias("updated_at"),
            lit("EPIC").alias("source_system"),
            when(col("meta.versionId").isNotNull(), col("meta.versionId")).otherwise(lit("1")).alias("source_version"),
        )
        
        # Validate against schema
        gold_df = self.spark.createDataFrame(gold_df.rdd, OBSERVATION_SCHEMA)
        
        return gold_df
    
    def write(self, gold_df: DataFrame) -> None:
        """Write the Gold layer DataFrame to Parquet.
        
        Args:
            gold_df: DataFrame in Gold layer format.
        """
        output_path = self.gold_path / "observation"
        logger.info(f"Writing Observation data to Gold layer: {output_path}")
        
        gold_df.write.mode("overwrite").parquet(str(output_path))
    
    def execute(self) -> None:
        """Execute the full ETL process for Observation data."""
        try:
            # Load silver data
            silver_df = self.load_silver_data()
            
            # Transform to gold
            gold_df = self.transform(silver_df)
            
            # Write to gold layer
            self.write(gold_df)
            
            logger.info("Observation Gold ETL completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Observation Gold ETL: {e}")
            raise 