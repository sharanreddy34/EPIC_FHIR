"""
Encounter schema for the Gold layer.

This module defines the schema for Encounter data in the Gold layer.
"""

from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    BooleanType, ArrayType, DateType, TimestampType
)

# Define the Encounter schema for the Gold layer
ENCOUNTER_SCHEMA = StructType([
    StructField("encounter_id", StringType(), False),
    StructField("patient_id", StringType(), False),
    StructField("start_datetime", TimestampType(), True),
    StructField("end_datetime", TimestampType(), True),
    StructField("duration_minutes", DoubleType(), True),
    StructField("status", StringType(), True),
    StructField("class_code", StringType(), True),
    StructField("class_display", StringType(), True),
    StructField("type_code", StringType(), True),
    StructField("type_display", StringType(), True),
    StructField("service_type_code", StringType(), True),
    StructField("service_type_display", StringType(), True),
    StructField("priority_code", StringType(), True),
    StructField("priority_display", StringType(), True),
    StructField("location_id", StringType(), True),
    StructField("location_name", StringType(), True),
    StructField("department_id", StringType(), True),
    StructField("department_name", StringType(), True),
    StructField("provider_id", StringType(), True),
    StructField("provider_name", StringType(), True),
    StructField("provider_role", StringType(), True),
    StructField("reason_code", StringType(), True),
    StructField("reason_display", StringType(), True),
    StructField("chief_complaint", StringType(), True),
    StructField("diagnoses", ArrayType(
        StructType([
            StructField("diagnosis_code", StringType(), True),
            StructField("diagnosis_display", StringType(), True),
            StructField("diagnosis_type", StringType(), True),
            StructField("diagnosis_rank", StringType(), True)
        ])
    ), True),
    StructField("discharge_disposition_code", StringType(), True),
    StructField("discharge_disposition_display", StringType(), True),
    StructField("admission_source_code", StringType(), True),
    StructField("admission_source_display", StringType(), True),
    StructField("length_of_stay_days", DoubleType(), True),
    StructField("related_encounters", ArrayType(
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