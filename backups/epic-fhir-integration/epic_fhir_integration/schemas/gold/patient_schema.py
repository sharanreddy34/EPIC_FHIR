"""
Patient schema for the Gold layer.

This module defines the schema for Patient data in the Gold layer.
"""

from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    BooleanType, ArrayType, DateType, TimestampType
)

# Define the Patient schema for the Gold layer
PATIENT_SCHEMA = StructType([
    StructField("patient_id", StringType(), False),
    StructField("mrn", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("birth_date", DateType(), True),
    StructField("gender", StringType(), True),
    StructField("address_line1", StringType(), True),
    StructField("address_line2", StringType(), True),
    StructField("city", StringType(), True),
    StructField("state", StringType(), True),
    StructField("postal_code", StringType(), True),
    StructField("country", StringType(), True),
    StructField("phone", StringType(), True),
    StructField("email", StringType(), True),
    StructField("marital_status", StringType(), True),
    StructField("language", StringType(), True),
    StructField("race", StringType(), True),
    StructField("ethnicity", StringType(), True),
    StructField("is_deceased", BooleanType(), True),
    StructField("deceased_date", DateType(), True),
    StructField("primary_care_provider_id", StringType(), True),
    StructField("primary_care_provider_name", StringType(), True),
    StructField("insurance_plans", ArrayType(
        StructType([
            StructField("plan_id", StringType(), True),
            StructField("plan_name", StringType(), True),
            StructField("coverage_type", StringType(), True),
            StructField("start_date", DateType(), True),
            StructField("end_date", DateType(), True)
        ])
    ), True),
    StructField("created_at", TimestampType(), True),
    StructField("updated_at", TimestampType(), True),
    StructField("source_system", StringType(), True),
    StructField("source_version", StringType(), True),
]) 