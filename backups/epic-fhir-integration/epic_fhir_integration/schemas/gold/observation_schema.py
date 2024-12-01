"""
Observation schema for the Gold layer.

This module defines the schema for Observation data in the Gold layer.
"""

from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    BooleanType, ArrayType, DateType, TimestampType
)

# Define the Observation schema for the Gold layer
OBSERVATION_SCHEMA = StructType([
    StructField("observation_id", StringType(), False),
    StructField("patient_id", StringType(), False),
    StructField("encounter_id", StringType(), True),
    StructField("observation_datetime", TimestampType(), True),
    StructField("observation_code", StringType(), True),
    StructField("observation_code_system", StringType(), True),
    StructField("observation_code_display", StringType(), True),
    StructField("observation_category", StringType(), True),
    StructField("observation_status", StringType(), True),
    StructField("observation_value_string", StringType(), True),
    StructField("observation_value_numeric", DoubleType(), True),
    StructField("observation_value_unit", StringType(), True),
    StructField("observation_value_coded", StringType(), True),
    StructField("observation_value_boolean", BooleanType(), True),
    StructField("observation_interpretation", StringType(), True),
    StructField("reference_range_low", DoubleType(), True),
    StructField("reference_range_high", DoubleType(), True),
    StructField("reference_range_text", StringType(), True),
    StructField("performer_id", StringType(), True),
    StructField("performer_name", StringType(), True),
    StructField("performer_type", StringType(), True),
    StructField("device_id", StringType(), True),
    StructField("device_name", StringType(), True),
    StructField("note", StringType(), True),
    StructField("related_observations", ArrayType(
        StructType([
            StructField("related_id", StringType(), True),
            StructField("relationship_type", StringType(), True)
        ])
    ), True),
    StructField("created_at", TimestampType(), True),
    StructField("updated_at", TimestampType(), True),
    StructField("source_system", StringType(), True),
    StructField("source_version", StringType(), True),
]) 