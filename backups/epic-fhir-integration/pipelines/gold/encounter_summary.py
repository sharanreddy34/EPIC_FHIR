"""
Encounter Summary Gold Transform

Creates a comprehensive encounter summary table combining details,
diagnoses, medications, and observations from an encounter into a row-per-encounter format.
"""
import logging
from typing import Any, Dict

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from fhir_pipeline.utils.logging import get_logger

def create_encounter_summary(spark: SparkSession, inputs: list, output: Any) -> None:
    """
    Generate a comprehensive encounter summary combining data from multiple FHIR resources.
    
    Args:
        spark: SparkSession
        inputs: List of input datasets
            [0] - encounter data
            [1] - patient data (optional)
            [2] - condition data (optional)
            [3] - observation data (optional)
            [4] - medication request data (optional)
        output: Output dataset for the encounter summary
    """
    logger = get_logger(__name__)
    
    # Extract input DataFrames with error handling
    try:
        encounter_df = inputs[0].dataframe()
        logger.info(f"Loaded encounter data: {encounter_df.count()} records")
    except Exception as e:
        logger.error(f"Failed to load encounter data: {str(e)}")
        raise
    
    # Optional inputs - use empty DataFrame if not available
    try:
        patient_df = inputs[1].dataframe() if len(inputs) > 1 else spark.createDataFrame([], encounter_df.schema)
        logger.info(f"Loaded patient data: {patient_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load patient data: {str(e)}")
        patient_df = spark.createDataFrame([], encounter_df.schema)
    
    try:
        condition_df = inputs[2].dataframe() if len(inputs) > 2 else spark.createDataFrame([], encounter_df.schema)
        logger.info(f"Loaded condition data: {condition_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load condition data: {str(e)}")
        condition_df = spark.createDataFrame([], encounter_df.schema)
    
    try:
        observation_df = inputs[3].dataframe() if len(inputs) > 3 else spark.createDataFrame([], encounter_df.schema)
        logger.info(f"Loaded observation data: {observation_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load observation data: {str(e)}")
        observation_df = spark.createDataFrame([], encounter_df.schema)
    
    try:
        medication_df = inputs[4].dataframe() if len(inputs) > 4 else spark.createDataFrame([], encounter_df.schema)
        logger.info(f"Loaded medication data: {medication_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load medication data: {str(e)}")
        medication_df = spark.createDataFrame([], encounter_df.schema)
    
    # 1. Start with encounter details
    logger.info("Building encounter base")
    summary_df = encounter_df.select(
        "encounter_id",
        "patient_id",
        "status",
        "class_code",
        "class_display",
        "type_code",
        "type_display",
        "period_start",
        "period_end",
        "service_provider"
    )
    
    # 2. Add patient details if available
    if "name_text" in patient_df.columns:
        logger.info("Adding patient details")
        patient_details = patient_df.select(
            "patient_id",
            "name_text",
            "gender",
            "birth_date"
        ).distinct()
        
        summary_df = summary_df.join(
            patient_details,
            "patient_id",
            "left"
        )
    
    # 3. Add conditions (diagnoses)
    if "clinical_status" in condition_df.columns and "encounter_id" in condition_df.columns:
        logger.info("Adding condition data")
        
        # Get conditions for encounters
        encounter_conditions = condition_df.filter(
            condition_df.encounter_id.isNotNull()
        )
        
        # Collect conditions by encounter
        conditions_by_encounter = encounter_conditions.groupBy("encounter_id").agg(
            F.collect_set("code_display").alias("diagnosis_list"),
            F.count("condition_id").alias("diagnosis_count")
        )
        
        # Join conditions to the summary
        summary_df = summary_df.join(
            conditions_by_encounter, 
            "encounter_id", 
            "left"
        )
        
        # Fill nulls for encounters without conditions
        summary_df = summary_df.withColumn(
            "diagnosis_list", 
            F.coalesce(F.col("diagnosis_list"), F.array())
        ).withColumn(
            "diagnosis_count", 
            F.coalesce(F.col("diagnosis_count"), F.lit(0))
        )
    
    # 4. Add medications 
    if "status" in medication_df.columns and "encounter_id" in medication_df.columns:
        logger.info("Adding medication data")
        
        # Filter to medications associated with encounters
        encounter_meds = medication_df.filter(
            medication_df.encounter_id.isNotNull()
        )
        
        # Group by encounter
        meds_by_encounter = encounter_meds.groupBy("encounter_id").agg(
            F.collect_set("medication_display").alias("medication_list"),
            F.count("medication_request_id").alias("medication_count")
        )
        
        # Join to summary
        summary_df = summary_df.join(meds_by_encounter, "encounter_id", "left")
        
        # Fill nulls
        summary_df = summary_df.withColumn(
            "medication_list", 
            F.coalesce(F.col("medication_list"), F.array())
        ).withColumn(
            "medication_count", 
            F.coalesce(F.col("medication_count"), F.lit(0))
        )
    
    # 5. Add observations
    if "code_code" in observation_df.columns and "encounter_id" in observation_df.columns:
        logger.info("Adding observation data")
        
        # Filter to observations with encounters
        encounter_obs = observation_df.filter(
            observation_df.encounter_id.isNotNull()
        )
        
        # Group by encounter
        obs_by_encounter = encounter_obs.groupBy("encounter_id").agg(
            F.collect_set("code_display").alias("observation_list"),
            F.count("observation_id").alias("observation_count"),
            F.max("issued_datetime").alias("last_observation_time")
        )
        
        # Join to summary
        summary_df = summary_df.join(obs_by_encounter, "encounter_id", "left")
        
        # Fill nulls
        summary_df = summary_df.withColumn(
            "observation_list", 
            F.coalesce(F.col("observation_list"), F.array())
        ).withColumn(
            "observation_count", 
            F.coalesce(F.col("observation_count"), F.lit(0))
        )
    
    # 6. Add summary text that combines all the information
    logger.info("Building comprehensive encounter summary text")
    
    @F.udf
    def generate_encounter_summary(status, class_display, type_display, period_start, period_end, 
                                  diagnoses, medications, observations):
        parts = []
        
        # Basic encounter info
        encounter_type = type_display if type_display else class_display
        if encounter_type and status:
            parts.append(f"{status.title()} {encounter_type} encounter")
        
        # Period
        if period_start and period_end:
            parts.append(f"from {period_start} to {period_end}")
        elif period_start:
            parts.append(f"started on {period_start}")
        
        # Add diagnoses if available
        if diagnoses and len(diagnoses) > 0:
            if len(diagnoses) <= 3:
                diagnoses_str = ", ".join(diagnoses)
                parts.append(f"with diagnoses of {diagnoses_str}")
            else:
                diagnoses_str = ", ".join(diagnoses[:3]) + f" and {len(diagnoses) - 3} more"
                parts.append(f"with diagnoses including {diagnoses_str}")
        
        # Add medications if available
        if medications and len(medications) > 0:
            if len(medications) <= 3:
                meds_str = ", ".join(medications)
                parts.append(f"medications: {meds_str}")
            else:
                meds_str = ", ".join(medications[:3]) + f" and {len(medications) - 3} more"
                parts.append(f"medications including {meds_str}")
        
        # Add observations count if available
        if observations and len(observations) > 0:
            parts.append(f"with {len(observations)} observations")
        
        # Combine all parts
        return ". ".join(parts) + "."
    
    # Apply summary generation
    cols_to_check = ["diagnosis_list", "medication_list", "observation_list"]
    for col in cols_to_check:
        if col not in summary_df.columns:
            summary_df = summary_df.withColumn(col, F.array())
    
    summary_df = summary_df.withColumn(
        "encounter_summary",
        generate_encounter_summary(
            F.col("status"),
            F.col("class_display"),
            F.col("type_display"),
            F.col("period_start"),
            F.col("period_end"),
            F.col("diagnosis_list") if "diagnosis_list" in summary_df.columns else F.array(),
            F.col("medication_list") if "medication_list" in summary_df.columns else F.array(),
            F.col("observation_list") if "observation_list" in summary_df.columns else F.array()
        )
    )
    
    # Add metadata
    summary_df = summary_df.withColumn(
        "_updated_at", 
        F.current_timestamp()
    ).withColumn(
        "_hash_id", 
        F.sha2(F.col("encounter_id"), 256)
    )
    
    # Write output
    logger.info(f"Writing {summary_df.count()} encounter summaries to {output.path}")
    
    # If output already exists, use merge to update
    try:
        # First, check if delta-spark is available
        delta_available = False
        try:
            from delta.tables import DeltaTable
            delta_available = True
        except (ImportError, ModuleNotFoundError):
            logger.warning("Delta Lake not available - falling back to standard write mode")
        
        if delta_available and spark.conf.get("spark.sql.catalog.spark_catalog", "") == "org.apache.spark.sql.delta.catalog.DeltaCatalog":
            # Check if output path exists as a Delta table
            from os.path import exists
            delta_log_exists = exists(f"{output.path}/_delta_log")
            
            if delta_log_exists:
                # Perform delta merge (upsert)
                delta_table = DeltaTable.forPath(spark, output.path)
                
                delta_table.alias("target").merge(
                    summary_df.alias("source"),
                    "target.encounter_id = source.encounter_id"
                ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
                
                logger.info(f"Merged encounter summary records to existing table")
            else:
                # First time write with Delta format
                summary_df.write.format("delta").mode("overwrite").save(output.path)
                logger.info(f"Created new encounter summary Delta table")
        else:
            # Fallback to parquet if Delta not available
            summary_df.write.mode("overwrite").parquet(output.path)
            logger.info(f"Created new encounter summary parquet table (Delta not available)")
    except Exception as e:
        logger.error(f"Error writing output: {str(e)}")
        logger.warning(f"Falling back to standard parquet write")
        # Fallback to regular write
        summary_df.write.mode("overwrite").parquet(output.path)
    
    logger.info("Encounter summary transform complete") 