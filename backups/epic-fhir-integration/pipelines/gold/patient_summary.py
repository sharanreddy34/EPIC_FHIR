"""
Patient Summary Gold Transform

Creates a comprehensive patient summary table combining demographics,
conditions, medications, and recent vital signs into a row-per-patient format.
"""
import logging
from typing import Any, Dict

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from fhir_pipeline.utils.logging import get_logger

def create_patient_summary(spark: SparkSession, inputs: list, output: Any) -> None:
    """
    Generate a comprehensive patient summary combining data from multiple FHIR resources.
    
    Args:
        spark: SparkSession
        inputs: List of input datasets
            [0] - patient data
            [1] - condition data (optional)
            [2] - observation data (optional)
            [3] - medication request data (optional)
        output: Output dataset for the patient summary
    """
    logger = get_logger(__name__)
    
    # Extract input DataFrames with error handling
    try:
        patient_df = inputs[0].dataframe()
        logger.info(f"Loaded patient data: {patient_df.count()} records")
    except Exception as e:
        logger.error(f"Failed to load patient data: {str(e)}")
        raise
    
    # Optional inputs - use empty DataFrame if not available
    try:
        condition_df = inputs[1].dataframe() if len(inputs) > 1 else spark.createDataFrame([], patient_df.schema)
        logger.info(f"Loaded condition data: {condition_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load condition data: {str(e)}")
        condition_df = spark.createDataFrame([], patient_df.schema)
    
    try:
        observation_df = inputs[2].dataframe() if len(inputs) > 2 else spark.createDataFrame([], patient_df.schema)
        logger.info(f"Loaded observation data: {observation_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load observation data: {str(e)}")
        observation_df = spark.createDataFrame([], patient_df.schema)
    
    try:
        medication_df = inputs[3].dataframe() if len(inputs) > 3 else spark.createDataFrame([], patient_df.schema)
        logger.info(f"Loaded medication data: {medication_df.count()} records")
    except Exception as e:
        logger.warning(f"Failed to load medication data: {str(e)}")
        medication_df = spark.createDataFrame([], patient_df.schema)
    
    # 1. Start with patient demographics
    logger.info("Building patient demographics base")
    summary_df = patient_df.select(
        "patient_id",
        "name_text",
        "gender",
        "birth_date",
        "phone",
        "email",
        "address_line",
        "address_city",
        "address_state",
        "address_postal_code",
        "patient_summary_text"
    )
    
    # 2. Add conditions (active diagnoses)
    if "clinical_status" in condition_df.columns and "code_display" in condition_df.columns:
        logger.info("Adding condition data")
        
        # Get active conditions
        active_conditions = condition_df.filter(
            (F.col("clinical_status") == "active") | 
            (F.col("clinical_status") == "recurrence") | 
            (F.col("clinical_status") == "relapse")
        )
        
        # Collect conditions by patient
        conditions_by_patient = active_conditions.groupBy("patient_id").agg(
            F.collect_set("code_display").alias("condition_list"),
            F.count("condition_id").alias("condition_count")
        )
        
        # Join conditions to the summary
        summary_df = summary_df.join(
            conditions_by_patient, 
            "patient_id", 
            "left"
        )
        
        # Fill nulls for patients without conditions
        summary_df = summary_df.withColumn(
            "condition_list", 
            F.coalesce(F.col("condition_list"), F.array())
        ).withColumn(
            "condition_count", 
            F.coalesce(F.col("condition_count"), F.lit(0))
        )
    
    # 3. Add most recent vital signs
    if "code_code" in observation_df.columns and "value" in observation_df.columns:
        logger.info("Adding vital signs data")
        
        # Filter to vital signs
        vitals = observation_df.filter(
            (F.col("code_system") == "http://loinc.org") & 
            F.col("value").isNotNull()
        )
        
        # Common vital sign LOINC codes
        vital_sign_codes = {
            "8302-2": "height",
            "29463-7": "weight",
            "8867-4": "pulse",
            "8480-6": "bp_systolic",
            "8462-4": "bp_diastolic",
            "8310-5": "temperature",
            "59408-5": "oxygen_saturation"
        }
        
        # Keep only selected vital signs
        vitals = vitals.filter(F.col("code_code").isin(list(vital_sign_codes.keys())))
        
        # Rank by recency
        window_spec = Window.partitionBy("patient_id", "code_code").orderBy(F.desc("issued_datetime"))
        vitals = vitals.withColumn("recency_rank", F.row_number().over(window_spec))
        
        # Keep only most recent reading per type
        most_recent_vitals = vitals.filter(F.col("recency_rank") == 1)
        
        # Pivot to get one column per vital sign
        vital_pivot = most_recent_vitals.groupBy("patient_id").pivot(
            "code_code", 
            list(vital_sign_codes.keys())
        ).agg(F.first("value"))
        
        # Rename columns to meaningful names
        for code, name in vital_sign_codes.items():
            if code in vital_pivot.columns:
                vital_pivot = vital_pivot.withColumnRenamed(code, name)
        
        # Add latest measurement dates
        measurement_dates = most_recent_vitals.groupBy("patient_id").agg(
            F.max("issued_datetime").alias("last_vitals_date")
        )
        
        vital_pivot = vital_pivot.join(measurement_dates, "patient_id", "left")
        
        # Join vitals to summary
        summary_df = summary_df.join(vital_pivot, "patient_id", "left")
    
    # 4. Add active medications
    if "status" in medication_df.columns and "medication_display" in medication_df.columns:
        logger.info("Adding medication data")
        
        # Filter to active medications
        active_meds = medication_df.filter(F.col("status") == "active")
        
        # Group by patient
        meds_by_patient = active_meds.groupBy("patient_id").agg(
            F.collect_set("medication_display").alias("medication_list"),
            F.count("medication_request_id").alias("medication_count")
        )
        
        # Join to summary
        summary_df = summary_df.join(meds_by_patient, "patient_id", "left")
        
        # Fill nulls
        summary_df = summary_df.withColumn(
            "medication_list", 
            F.coalesce(F.col("medication_list"), F.array())
        ).withColumn(
            "medication_count", 
            F.coalesce(F.col("medication_count"), F.lit(0))
        )
    
    # 5. Add summary text that combines all the information
    logger.info("Building comprehensive patient summary text")
    
    @F.udf
    def generate_comprehensive_summary(name, gender, birth_date, conditions, medications):
        parts = []
        
        # Basic demographics
        if name:
            parts.append(f"Patient {name}")
        if gender:
            parts.append(f"is a {gender} patient")
        if birth_date:
            parts.append(f"born on {birth_date}")
        
        # Add conditions if available
        if conditions and len(conditions) > 0:
            if len(conditions) <= 3:
                conditions_str = ", ".join(conditions)
                parts.append(f"with diagnoses of {conditions_str}")
            else:
                conditions_str = ", ".join(conditions[:3]) + f" and {len(conditions) - 3} more"
                parts.append(f"with diagnoses including {conditions_str}")
        
        # Add medications if available
        if medications and len(medications) > 0:
            if len(medications) <= 3:
                meds_str = ", ".join(medications)
                parts.append(f"currently taking {meds_str}")
            else:
                meds_str = ", ".join(medications[:3]) + f" and {len(medications) - 3} more"
                parts.append(f"currently taking medications including {meds_str}")
        
        # Combine all parts
        return ". ".join(parts) + "."
    
    # Apply summary generation
    summary_df = summary_df.withColumn(
        "comprehensive_summary",
        generate_comprehensive_summary(
            F.col("name_text"),
            F.col("gender"),
            F.col("birth_date"),
            F.col("condition_list") if "condition_list" in summary_df.columns else F.array(),
            F.col("medication_list") if "medication_list" in summary_df.columns else F.array()
        )
    )
    
    # Add metadata
    summary_df = summary_df.withColumn(
        "_updated_at", 
        F.current_timestamp()
    ).withColumn(
        "_hash_id", 
        F.sha2(F.col("patient_id"), 256)
    )
    
    # Write output
    logger.info(f"Writing {summary_df.count()} patient summaries to {output.path}")
    
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
                    "target.patient_id = source.patient_id"
                ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
                
                logger.info(f"Merged patient summary records to existing table")
            else:
                # First time write with Delta format
                summary_df.write.format("delta").mode("overwrite").save(output.path)
                logger.info(f"Created new patient summary Delta table")
        else:
            # Fallback to parquet if Delta not available
            summary_df.write.mode("overwrite").parquet(output.path)
            logger.info(f"Created new patient summary parquet table (Delta not available)")
    except Exception as e:
        logger.error(f"Error writing output: {str(e)}")
        logger.warning(f"Falling back to standard parquet write")
        # Fallback to regular write
        summary_df.write.mode("overwrite").parquet(output.path)
    
    logger.info("Patient summary transform complete") 