"""
Patient Timeline Gold Transform

Creates a temporal timeline of all patient events, ordering all clinical events
chronologically and preparing them for embeddings and RAG applications.
"""
import logging
from typing import Any, Dict, List, Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

from fhir_pipeline.utils.logging import get_logger

def create_patient_timeline(spark: SparkSession, inputs: list, output: Any) -> None:
    """
    Create a chronological timeline of all patient events.
    
    Args:
        spark: SparkSession
        inputs: List of input datasets
            [0] - observation data
            [1] - condition data
            [2] - encounter data
            [3] - medication request data (optional)
            [4] - diagnostic report data (optional)
        output: Output dataset for the patient timeline
    """
    logger = get_logger(__name__)
    
    # Define the common schema for all timeline events
    timeline_schema = StructType([
        StructField("patient_id", StringType(), False),
        StructField("event_time", TimestampType(), True),
        StructField("event_type", StringType(), False),
        StructField("event_id", StringType(), False),
        StructField("event_source", StringType(), False),
        StructField("clinical_text", StringType(), True),
        StructField("code_display", StringType(), True),
        StructField("status", StringType(), True)
    ])
    
    # Load input DataFrames
    input_dfs = []
    
    # Function to process each resource type
    def process_resource(index: int, resource_type: str) -> Optional[DataFrame]:
        if index >= len(inputs):
            logger.info(f"No {resource_type} data provided")
            return None
            
        try:
            df = inputs[index].dataframe()
            logger.info(f"Loaded {resource_type} data: {df.count()} records")
            return df
        except Exception as e:
            logger.warning(f"Failed to load {resource_type} data: {str(e)}")
            return None
    
    # Process all resource types
    observation_df = process_resource(0, "Observation")
    condition_df = process_resource(1, "Condition")
    encounter_df = process_resource(2, "Encounter")
    medication_df = process_resource(3, "MedicationRequest")
    diagnostic_df = process_resource(4, "DiagnosticReport")
    
    # Create timeline entries for each resource type
    timeline_entries = []
    
    # Process Observations
    if observation_df is not None:
        logger.info("Processing observations for timeline")
        
        obs_timeline = observation_df.select(
            F.col("patient_id"),
            F.to_timestamp(F.col("issued_datetime")).alias("event_time"),
            F.lit("Observation").alias("event_type"),
            F.col("observation_id").alias("event_id"),
            F.lit("FHIR").alias("event_source"),
            F.col("clinical_text"),
            F.col("code_display"),
            F.col("status")
        )
        timeline_entries.append(obs_timeline)
    
    # Process Conditions
    if condition_df is not None:
        logger.info("Processing conditions for timeline")
        
        # Use recorded_date or onset_datetime as the event time
        condition_timeline = condition_df.select(
            F.col("patient_id"),
            F.coalesce(
                F.to_timestamp(F.col("recorded_date")),
                F.to_timestamp(F.col("onset_datetime"))
            ).alias("event_time"),
            F.lit("Condition").alias("event_type"),
            F.col("condition_id").alias("event_id"),
            F.lit("FHIR").alias("event_source"),
            F.col("clinical_text"),
            F.col("code_display"),
            F.col("clinical_status").alias("status")
        )
        timeline_entries.append(condition_timeline)
    
    # Process Encounters
    if encounter_df is not None:
        logger.info("Processing encounters for timeline")
        
        encounter_timeline = encounter_df.select(
            F.col("patient_id"),
            F.to_timestamp(F.col("start_datetime")).alias("event_time"),
            F.lit("Encounter").alias("event_type"),
            F.col("encounter_id").alias("event_id"),
            F.lit("FHIR").alias("event_source"),
            F.col("clinical_text"),
            F.col("type_display").alias("code_display"),
            F.col("status")
        )
        timeline_entries.append(encounter_timeline)
    
    # Process MedicationRequests
    if medication_df is not None:
        logger.info("Processing medication requests for timeline")
        
        med_timeline = medication_df.select(
            F.col("patient_id"),
            F.to_timestamp(F.col("authored_datetime")).alias("event_time"),
            F.lit("MedicationRequest").alias("event_type"),
            F.col("medication_request_id").alias("event_id"),
            F.lit("FHIR").alias("event_source"),
            F.col("clinical_text"),
            F.col("medication_display").alias("code_display"),
            F.col("status")
        )
        timeline_entries.append(med_timeline)
    
    # Process DiagnosticReports
    if diagnostic_df is not None:
        logger.info("Processing diagnostic reports for timeline")
        
        diag_timeline = diagnostic_df.select(
            F.col("patient_id"),
            F.to_timestamp(F.col("issued_datetime")).alias("event_time"),
            F.lit("DiagnosticReport").alias("event_type"),
            F.col("report_id").alias("event_id"),
            F.lit("FHIR").alias("event_source"),
            F.col("clinical_text"),
            F.col("code_display"),
            F.col("status")
        )
        timeline_entries.append(diag_timeline)
    
    # Combine all timeline entries
    if not timeline_entries:
        logger.error("No timeline entries could be created from the provided inputs")
        # Create empty DataFrame with the correct schema
        timeline_df = spark.createDataFrame([], timeline_schema)
    else:
        logger.info("Unioning all timeline entries")
        timeline_df = timeline_entries[0]
        for df in timeline_entries[1:]:
            timeline_df = timeline_df.unionByName(df)
    
    # Order all entries chronologically
    logger.info("Ordering timeline entries chronologically")
    timeline_df = timeline_df.orderBy("patient_id", "event_time")
    
    # Fill missing event_time with current timestamp to avoid nulls
    timeline_df = timeline_df.fillna({"event_time": F.current_timestamp()})
    
    # Fill missing clinical_text with code_display to avoid nulls
    timeline_df = timeline_df.withColumn(
        "clinical_text",
        F.coalesce(F.col("clinical_text"), F.col("code_display"))
    )
    
    # Add metadata
    timeline_df = timeline_df.withColumn(
        "_updated_at", 
        F.current_timestamp()
    ).withColumn(
        "_hash_id", 
        F.sha2(F.concat(F.col("event_id"), F.col("event_type")), 256)
    )
    
    # Generate sequence numbers for each patient's timeline
    timeline_df = timeline_df.withColumn(
        "event_sequence", 
        F.row_number().over(
            F.Window.partitionBy("patient_id").orderBy("event_time")
        )
    )
    
    # Write the timeline
    logger.info(f"Writing {timeline_df.count()} timeline entries to {output.path}")
    
    # If output already exists, use merge to update
    try:
        from delta.tables import DeltaTable
        
        if spark._jsparkSession.catalog().tableExists(output.path):
            # Perform delta merge (upsert)
            delta_table = DeltaTable.forPath(spark, output.path)
            
            delta_table.alias("target").merge(
                timeline_df.alias("source"),
                "target.event_id = source.event_id AND target.event_type = source.event_type"
            ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
            
            logger.info(f"Merged timeline entries to existing table")
        else:
            # First time write
            timeline_df.write.format("delta").mode("overwrite").save(output.path)
            logger.info(f"Created new timeline table")
    except Exception as e:
        logger.error(f"Error writing output: {str(e)}")
        # Fallback to regular write
        timeline_df.write.format("delta").mode("overwrite").save(output.path)
    
    logger.info("Patient timeline transform complete") 