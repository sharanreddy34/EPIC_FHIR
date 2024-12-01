"""
Encounter summary transformer for the Gold layer.

This module transforms Encounter data from the Silver layer into the Gold layer.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lit, array, struct, to_date, to_timestamp, 
    when, expr, concat, split, first, last, datediff, hour, minute
)

from epic_fhir_integration.schemas.gold import ENCOUNTER_SCHEMA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EncounterSummary:
    """Transformer for Encounter resources to the Gold layer."""
    
    def __init__(
        self,
        spark: SparkSession,
        silver_path: Union[str, Path] = None,
        gold_path: Union[str, Path] = None,
    ):
        """Initialize a new Encounter summary transformer.
        
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
        (self.gold_path / "encounter").mkdir(parents=True, exist_ok=True)
    
    def load_silver_data(self) -> DataFrame:
        """Load Encounter data from the Silver layer.
        
        Returns:
            DataFrame containing Silver layer Encounter data.
        """
        silver_encounter_path = self.silver_path / "encounter"
        
        if not silver_encounter_path.exists():
            raise ValueError(f"Silver layer path does not exist: {silver_encounter_path}")
        
        logger.info(f"Loading Encounter data from Silver layer: {silver_encounter_path}")
        df = self.spark.read.parquet(str(silver_encounter_path))
        
        return df
    
    def transform(self, silver_df: Optional[DataFrame] = None) -> DataFrame:
        """Transform Silver layer Encounter data to Gold layer format.
        
        Args:
            silver_df: DataFrame containing Silver layer Encounter data.
                      If not provided, it will be loaded from the Silver layer.
                      
        Returns:
            DataFrame in Gold layer format.
        """
        # Load silver data if not provided
        if silver_df is None:
            silver_df = self.load_silver_data()
        
        logger.info("Transforming Encounter data to Gold layer format")
        
        # Add duration calculation
        silver_df = silver_df.withColumn(
            "duration_minutes",
            when(
                col("period.start").isNotNull() & col("period.end").isNotNull(),
                expr("(to_timestamp(period.end) - to_timestamp(period.start)) / 60")
            ).otherwise(None)
        )
        
        # Extract and transform encounter data
        gold_df = silver_df.select(
            # Required fields
            col("id").alias("encounter_id"),
            
            # Extract patient ID from subject reference
            when(col("subject.reference").isNotNull(),
                 expr("substring(subject.reference, 9)") # Assumes format "Patient/123"
            ).alias("patient_id"),
            
            # Date and time
            to_timestamp(col("period.start")).alias("start_datetime"),
            to_timestamp(col("period.end")).alias("end_datetime"),
            
            # Duration
            col("duration_minutes"),
            
            # Status
            col("status"),
            
            # Class
            when(col("class.code").isNotNull(), 
                 col("class.code")
            ).alias("class_code"),
            
            when(col("class.display").isNotNull(), 
                 col("class.display")
            ).alias("class_display"),
            
            # Encounter type
            when(col("type").isNotNull(),
                 expr("transform(type, x -> x.coding[0].code)[0]")
            ).alias("type_code"),
            
            when(col("type").isNotNull(),
                 expr("transform(type, x -> x.coding[0].display)[0]")
            ).alias("type_display"),
            
            # Service type
            when(col("serviceType.coding").isNotNull(),
                 col("serviceType.coding[0].code")
            ).alias("service_type_code"),
            
            when(col("serviceType.coding").isNotNull(),
                 col("serviceType.coding[0].display")
            ).alias("service_type_display"),
            
            # Priority
            when(col("priority.coding").isNotNull(),
                 col("priority.coding[0].code")
            ).alias("priority_code"),
            
            when(col("priority.coding").isNotNull(),
                 col("priority.coding[0].display")
            ).alias("priority_display"),
            
            # Location
            when(col("location").isNotNull(),
                 expr("transform(location, x -> substring(x.location.reference, 10))[0]") # Assumes format "Location/123"
            ).alias("location_id"),
            
            when(col("location").isNotNull(),
                 expr("transform(location, x -> x.location.display)[0]")
            ).alias("location_name"),
            
            # Department - assuming a specific extension for department
            when(col("serviceProvider.reference").isNotNull(),
                 expr("substring(serviceProvider.reference, 13)") # Assumes format "Organization/123"
            ).alias("department_id"),
            
            when(col("serviceProvider.display").isNotNull(),
                 col("serviceProvider.display")
            ).alias("department_name"),
            
            # Provider
            when(col("participant").isNotNull(),
                 expr("transform(participant, x -> CASE WHEN x.individual.reference LIKE 'Practitioner/%' THEN substring(x.individual.reference, 14) ELSE NULL END)[0]")
            ).alias("provider_id"),
            
            when(col("participant").isNotNull(),
                 expr("transform(participant, x -> x.individual.display)[0]")
            ).alias("provider_name"),
            
            when(col("participant").isNotNull(),
                 expr("transform(participant, x -> x.type[0].coding[0].display)[0]")
            ).alias("provider_role"),
            
            # Reason
            when(col("reasonCode").isNotNull(),
                 expr("transform(reasonCode, x -> x.coding[0].code)[0]")
            ).alias("reason_code"),
            
            when(col("reasonCode").isNotNull(),
                 expr("transform(reasonCode, x -> x.coding[0].display)[0]")
            ).alias("reason_display"),
            
            when(col("reasonCode").isNotNull(), 
                 expr("transform(reasonCode, x -> x.text)[0]")
            ).alias("chief_complaint"),
            
            # Diagnoses
            when(col("diagnosis").isNotNull(),
                 expr("transform(diagnosis, x -> struct(" +
                      "x.condition.coding[0].code as diagnosis_code, " +
                      "x.condition.coding[0].display as diagnosis_display, " +
                      "x.use.coding[0].code as diagnosis_type, " +
                      "x.rank as diagnosis_rank))")
            ).otherwise(array()).alias("diagnoses"),
            
            # Discharge disposition
            when(col("hospitalization.dischargeDisposition.coding").isNotNull(),
                 col("hospitalization.dischargeDisposition.coding[0].code")
            ).alias("discharge_disposition_code"),
            
            when(col("hospitalization.dischargeDisposition.coding").isNotNull(),
                 col("hospitalization.dischargeDisposition.coding[0].display")
            ).alias("discharge_disposition_display"),
            
            # Admission source
            when(col("hospitalization.admitSource.coding").isNotNull(),
                 col("hospitalization.admitSource.coding[0].code")
            ).alias("admission_source_code"),
            
            when(col("hospitalization.admitSource.coding").isNotNull(),
                 col("hospitalization.admitSource.coding[0].display")
            ).alias("admission_source_display"),
            
            # Length of stay
            when(
                col("period.start").isNotNull() & col("period.end").isNotNull(),
                expr("datediff(to_date(period.end), to_date(period.start))")
            ).alias("length_of_stay_days"),
            
            # Related encounters
            when(col("partOf.reference").isNotNull(),
                 array(
                     struct(
                         expr("substring(partOf.reference, 11)").alias("related_id"),
                         lit("part-of").alias("relationship_type")
                     )
                 )
            ).otherwise(array()).alias("related_encounters"),
            
            # Metadata
            to_timestamp(expr("meta.lastUpdated")).alias("created_at"),
            to_timestamp(expr("meta.lastUpdated")).alias("updated_at"),
            lit("EPIC").alias("source_system"),
            when(col("meta.versionId").isNotNull(), col("meta.versionId")).otherwise(lit("1")).alias("source_version"),
        )
        
        # Validate against schema
        gold_df = self.spark.createDataFrame(gold_df.rdd, ENCOUNTER_SCHEMA)
        
        return gold_df
    
    def write(self, gold_df: DataFrame) -> None:
        """Write the Gold layer DataFrame to Parquet.
        
        Args:
            gold_df: DataFrame in Gold layer format.
        """
        output_path = self.gold_path / "encounter"
        logger.info(f"Writing Encounter data to Gold layer: {output_path}")
        
        gold_df.write.mode("overwrite").parquet(str(output_path))
    
    def execute(self) -> None:
        """Execute the full ETL process for Encounter data."""
        try:
            # Load silver data
            silver_df = self.load_silver_data()
            
            # Transform to gold
            gold_df = self.transform(silver_df)
            
            # Write to gold layer
            self.write(gold_df)
            
            logger.info("Encounter Gold ETL completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Encounter Gold ETL: {e}")
            raise 