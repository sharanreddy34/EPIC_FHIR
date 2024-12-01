"""
Encounter KPI Gold Transform

Creates a KPI dataset for encounters, including metrics like length-of-stay,
diagnosis counts, and other encounter-related statistics.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from fhir_pipeline.utils.logging import get_logger

def create_encounter_kpi(spark: SparkSession, inputs: list, output: Any) -> None:
    """
    Create Key Performance Indicators for encounters.
    
    Args:
        spark: SparkSession
        inputs: List of input datasets
            [0] - encounter data
            [1] - condition data (optional)
            [2] - observation data (optional)
            [3] - medication request data (optional)
        output: Output dataset for the encounter KPIs
    """
    logger = get_logger(__name__)
    
    # Extract input DataFrames with error handling
    try:
        encounter_df = inputs[0].dataframe()
        logger.info(f"Loaded encounter data: {encounter_df.count()} records")
    except Exception as e:
        logger.error(f"Failed to load encounter data: {str(e)}")
        raise
    
    # Optional inputs
    try:
        condition_df = inputs[1].dataframe() if len(inputs) > 1 else None
        if condition_df:
            logger.info(f"Loaded condition data: {condition_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load condition data: {str(e)}")
        condition_df = None
    
    try:
        observation_df = inputs[2].dataframe() if len(inputs) > 2 else None
        if observation_df:
            logger.info(f"Loaded observation data: {observation_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load observation data: {str(e)}")
        observation_df = None
    
    try:
        medication_df = inputs[3].dataframe() if len(inputs) > 3 else None
        if medication_df:
            logger.info(f"Loaded medication data: {medication_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load medication data: {str(e)}")
        medication_df = None
    
    # Start with the encounter dataset
    logger.info("Building encounter KPI base")
    
    # Add derived fields
    encounter_kpi = encounter_df.select(
        "encounter_id",
        "patient_id",
        "start_datetime",
        "end_datetime",
        "status",
        "class_code",
        "class_display",
        "type_code",
        "type_display"
    )
    
    # Calculate length of stay in hours
    encounter_kpi = encounter_kpi.withColumn(
        "length_of_stay_hours",
        F.when(
            F.col("end_datetime").isNotNull() & F.col("start_datetime").isNotNull(),
            F.round(
                F.unix_timestamp(F.col("end_datetime")) - F.unix_timestamp(F.col("start_datetime"))
            ) / 3600
        )
    )
    
    # Calculate length of stay in days
    encounter_kpi = encounter_kpi.withColumn(
        "length_of_stay_days",
        F.round(F.col("length_of_stay_hours") / 24, 1)
    )
    
    # Flag encounters that are still active (no end date)
    encounter_kpi = encounter_kpi.withColumn(
        "is_active",
        F.col("end_datetime").isNull() & F.col("status").isin(["in-progress", "onleave", "arrived", "triaged"])
    )
    
    # Add diagnosis counts if condition data is available
    if condition_df is not None and "encounter_id" in condition_df.columns:
        logger.info("Adding diagnosis counts")
        
        # Count diagnoses per encounter
        diagnosis_counts = condition_df.groupBy("encounter_id").agg(
            F.count("condition_id").alias("diagnosis_count"),
            F.countDistinct("code_code").alias("unique_diagnosis_count")
        )
        
        # Join to the KPI table
        encounter_kpi = encounter_kpi.join(
            diagnosis_counts,
            "encounter_id",
            "left"
        )
        
        # Fill nulls for encounters without diagnoses
        encounter_kpi = encounter_kpi.fillna({
            "diagnosis_count": 0,
            "unique_diagnosis_count": 0
        })
    else:
        # Add placeholder columns
        encounter_kpi = encounter_kpi.withColumn("diagnosis_count", F.lit(None).cast("integer"))
        encounter_kpi = encounter_kpi.withColumn("unique_diagnosis_count", F.lit(None).cast("integer"))
    
    # Add observation counts if observation data is available
    if observation_df is not None and "encounter_id" in observation_df.columns:
        logger.info("Adding observation counts")
        
        # Count observations per encounter
        observation_counts = observation_df.groupBy("encounter_id").agg(
            F.count("observation_id").alias("observation_count"),
            F.countDistinct("code_code").alias("unique_observation_count")
        )
        
        # Join to the KPI table
        encounter_kpi = encounter_kpi.join(
            observation_counts,
            "encounter_id",
            "left"
        )
        
        # Fill nulls for encounters without observations
        encounter_kpi = encounter_kpi.fillna({
            "observation_count": 0,
            "unique_observation_count": 0
        })
    else:
        # Add placeholder columns
        encounter_kpi = encounter_kpi.withColumn("observation_count", F.lit(None).cast("integer"))
        encounter_kpi = encounter_kpi.withColumn("unique_observation_count", F.lit(None).cast("integer"))
    
    # Add medication counts if medication data is available
    if medication_df is not None and "encounter_id" in medication_df.columns:
        logger.info("Adding medication counts")
        
        # Count medications per encounter
        medication_counts = medication_df.groupBy("encounter_id").agg(
            F.count("medication_request_id").alias("medication_count"),
            F.countDistinct("medication_code").alias("unique_medication_count")
        )
        
        # Join to the KPI table
        encounter_kpi = encounter_kpi.join(
            medication_counts,
            "encounter_id",
            "left"
        )
        
        # Fill nulls for encounters without medications
        encounter_kpi = encounter_kpi.fillna({
            "medication_count": 0,
            "unique_medication_count": 0
        })
    else:
        # Add placeholder columns
        encounter_kpi = encounter_kpi.withColumn("medication_count", F.lit(None).cast("integer"))
        encounter_kpi = encounter_kpi.withColumn("unique_medication_count", F.lit(None).cast("integer"))
    
    # Calculate patient encounter history (count of previous encounters)
    window_spec = Window.partitionBy("patient_id").orderBy("start_datetime").rangeBetween(
        Window.unboundedPreceding, -1
    )
    
    encounter_kpi = encounter_kpi.withColumn(
        "previous_encounter_count",
        F.count("encounter_id").over(window_spec)
    )
    
    # Categorize encounters by type
    encounter_kpi = encounter_kpi.withColumn(
        "encounter_category",
        F.when(F.col("class_code") == "IMP", "inpatient")
         .when(F.col("class_code") == "AMB", "ambulatory")
         .when(F.col("class_code") == "EMER", "emergency")
         .when(F.col("class_code") == "HH", "home_health")
         .otherwise("other")
    )
    
    # Set KPI flags
    encounter_kpi = encounter_kpi.withColumn(
        "is_long_stay",
        F.when(
            F.col("encounter_category") == "inpatient", 
            F.col("length_of_stay_days") > 7
        ).when(
            F.col("encounter_category") == "emergency",
            F.col("length_of_stay_hours") > 24
        ).otherwise(False)
    )
    
    # Add metadata columns
    encounter_kpi = encounter_kpi.withColumn(
        "_updated_at", 
        F.current_timestamp()
    ).withColumn(
        "_hash_id", 
        F.sha2(F.col("encounter_id"), 256)
    )
    
    # Write the KPI data
    logger.info(f"Writing {encounter_kpi.count()} encounter KPI records to {output.path}")
    
    # If output already exists, use merge to update
    try:
        from delta.tables import DeltaTable
        
        # Check if table exists
        if spark._jsparkSession.catalog().tableExists(output.path):
            # Perform delta merge (upsert)
            delta_table = DeltaTable.forPath(spark, output.path)
            
            delta_table.alias("target").merge(
                encounter_kpi.alias("source"),
                "target.encounter_id = source.encounter_id"
            ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
            
            logger.info(f"Merged encounter KPI records to existing table")
        else:
            # First time write
            encounter_kpi.write.format("delta").mode("overwrite").save(output.path)
            logger.info(f"Created new encounter KPI table")
    except Exception as e:
        logger.error(f"Error writing output: {str(e)}")
        # Fallback to regular write
        encounter_kpi.write.format("delta").mode("overwrite").save(output.path)
    
    logger.info("Encounter KPI transform complete") 