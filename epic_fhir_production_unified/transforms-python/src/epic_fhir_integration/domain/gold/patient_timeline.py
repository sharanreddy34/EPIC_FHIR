"""
Patient Timeline Gold transform for Epic FHIR integration.

This module provides a transform for creating a patient timeline from Silver datasets
in Foundry, consolidating key patient events into a single timeline.
"""

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, Window
from transforms.api import transform_df, Input, Output

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


@transform_df(
    Output("datasets.Patient_Timeline_Gold"),
    Input("datasets.Patient_Clean_Silver"),
    Input("datasets.Encounter_Clean_Silver"),
    Input("datasets.Observation_Clean_Silver", optional=True),
    Input("datasets.Condition_Clean_Silver", optional=True),
)
def compute(ctx, output, patient_silver, encounter_silver, observation_silver=None, condition_silver=None):
    """Create a patient timeline from FHIR Silver datasets.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        patient_silver: Patient Silver dataset.
        encounter_silver: Encounter Silver dataset.
        observation_silver: Optional Observation Silver dataset.
        condition_silver: Optional Condition Silver dataset.
    """
    logger.info("Starting Patient Timeline Gold transform")
    
    # Read input datasets
    patient_df = patient_silver.dataframe()
    logger.info("Read Patient Silver dataset", count=patient_df.count())
    
    encounter_df = encounter_silver.dataframe()
    logger.info("Read Encounter Silver dataset", count=encounter_df.count())
    
    # Select key patient columns
    patient_slim = patient_df.select(
        "id",
        "given_name",
        "family_name",
        "gender",
        "birth_date"
    ).withColumnRenamed("id", "patient_id")
    
    # Select key encounter columns with start date for timeline
    encounter_slim = encounter_df.select(
        "id",
        "patient_id",
        "start_date",
        "end_date",
        "class_code",
        "class_display",
        "encounter_type_display",
        "reason_display"
    ).withColumn("event_type", F.lit("Encounter"))
    
    # Create base timeline from encounters
    timeline_df = encounter_slim
    
    # Add observations if available
    if observation_silver is not None:
        observation_df = observation_silver.dataframe()
        logger.info("Read Observation Silver dataset", count=observation_df.count())
        
        observation_slim = observation_df.select(
            "id",
            "patient_id",
            "effective_date_time",
            "code_display",
            "quantity_value",
            "quantity_unit",
            "string_value",
            "concept_display"
        ).withColumn("event_type", F.lit("Observation"))
        
        # Rename date column to match encounters
        observation_slim = observation_slim.withColumnRenamed("effective_date_time", "start_date")
        
        # Add a display value that combines different value types
        observation_slim = observation_slim.withColumn(
            "display_value",
            F.coalesce(
                F.concat(F.col("quantity_value").cast("string"), F.lit(" "), F.col("quantity_unit")),
                F.col("string_value"),
                F.col("concept_display")
            )
        )
        
        # Union with timeline
        timeline_df = timeline_df.unionByName(
            observation_slim.select(*timeline_df.columns),
            allowMissingColumns=True
        )
    
    # Add conditions if available
    if condition_silver is not None:
        condition_df = condition_silver.dataframe()
        logger.info("Read Condition Silver dataset", count=condition_df.count())
        
        condition_slim = condition_df.select(
            "id",
            "patient_id",
            "onset_date_time",
            "code_display",
            "clinical_status_display",
            "verification_status_display"
        ).withColumn("event_type", F.lit("Condition"))
        
        # Rename date column to match encounters
        condition_slim = condition_slim.withColumnRenamed("onset_date_time", "start_date")
        
        # Union with timeline
        timeline_df = timeline_df.unionByName(
            condition_slim.select(*timeline_df.columns),
            allowMissingColumns=True
        )
    
    # Join with patient info
    patient_timeline = timeline_df.join(patient_slim, "patient_id", "inner")
    
    # Sort by patient and date
    patient_timeline = patient_timeline.orderBy("patient_id", "start_date")
    
    # Write to output
    logger.info("Writing Patient Timeline Gold dataset", count=patient_timeline.count())
    patient_timeline.write.format("delta").mode("overwrite").save(output.uri) 