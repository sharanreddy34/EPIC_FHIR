"""
Patient Silver transform for Epic FHIR integration.

This module provides a transform for cleaning and conforming Patient resources
from the Bronze dataset to a Silver dataset in Foundry.
"""

import json
from typing import Dict, Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json, explode, when, lit, to_date
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, TimestampType, DateType
from transforms.api import transform_df, incremental, Input, Output

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


# Define schema for flattened Patient data
PATIENT_SCHEMA = StructType([
    StructField("id", StringType(), True),
    StructField("identifier", StringType(), True),
    StructField("active", StringType(), True),
    StructField("name_given", StringType(), True),
    StructField("name_family", StringType(), True),
    StructField("name_text", StringType(), True),
    StructField("gender", StringType(), True),
    StructField("birthDate", DateType(), True),
    StructField("address_line", StringType(), True),
    StructField("address_city", StringType(), True),
    StructField("address_state", StringType(), True),
    StructField("address_postalCode", StringType(), True),
    StructField("address_country", StringType(), True),
    StructField("telecom_phone", StringType(), True),
    StructField("telecom_email", StringType(), True),
    StructField("maritalStatus", StringType(), True),
    StructField("communication_language", StringType(), True),
    StructField("meta_lastUpdated", TimestampType(), True),
    StructField("source", StringType(), True),
])


def parse_patient_json(json_data: str) -> Dict[str, Any]:
    """Parse JSON data into a flattened Patient dictionary.
    
    Args:
        json_data: JSON string containing a FHIR Patient resource.
        
    Returns:
        Flattened Patient dictionary.
    """
    # Parse JSON
    patient = json.loads(json_data)
    
    # Initialize result dictionary with default values
    result = {
        "id": None,
        "identifier": None,
        "active": None,
        "name_given": None,
        "name_family": None,
        "name_text": None,
        "gender": None,
        "birthDate": None,
        "address_line": None,
        "address_city": None,
        "address_state": None,
        "address_postalCode": None,
        "address_country": None,
        "telecom_phone": None,
        "telecom_email": None,
        "maritalStatus": None,
        "communication_language": None,
        "meta_lastUpdated": None,
        "source": "epic",
    }
    
    # Extract basic fields
    result["id"] = patient.get("id")
    result["active"] = str(patient.get("active")).lower() if "active" in patient else None
    result["gender"] = patient.get("gender")
    result["birthDate"] = patient.get("birthDate")
    
    # Extract meta.lastUpdated
    meta = patient.get("meta", {})
    result["meta_lastUpdated"] = meta.get("lastUpdated")
    
    # Extract first identifier
    identifiers = patient.get("identifier", [])
    if identifiers:
        result["identifier"] = f"{identifiers[0].get('system', '')}|{identifiers[0].get('value', '')}"
    
    # Extract name components from the first name
    names = patient.get("name", [])
    if names:
        name = names[0]
        result["name_given"] = " ".join(name.get("given", [])) if "given" in name else None
        result["name_family"] = name.get("family")
        result["name_text"] = name.get("text")
    
    # Extract address components from the first address
    addresses = patient.get("address", [])
    if addresses:
        address = addresses[0]
        result["address_line"] = ", ".join(address.get("line", [])) if "line" in address else None
        result["address_city"] = address.get("city")
        result["address_state"] = address.get("state")
        result["address_postalCode"] = address.get("postalCode")
        result["address_country"] = address.get("country")
    
    # Extract telecom values
    telecoms = patient.get("telecom", [])
    for telecom in telecoms:
        system = telecom.get("system")
        value = telecom.get("value")
        if system == "phone" and value and not result["telecom_phone"]:
            result["telecom_phone"] = value
        elif system == "email" and value and not result["telecom_email"]:
            result["telecom_email"] = value
    
    # Extract marital status
    marital_status = patient.get("maritalStatus", {})
    if marital_status and "coding" in marital_status:
        codings = marital_status["coding"]
        if codings:
            result["maritalStatus"] = codings[0].get("code")
    
    # Extract communication language
    communications = patient.get("communication", [])
    for comm in communications:
        language = comm.get("language", {})
        if language and "coding" in language:
            codings = language["coding"]
            if codings:
                result["communication_language"] = codings[0].get("code")
                break
    
    return result


@incremental(snapshot_inputs=True)
@transform_df(
    Output("datasets.Patient_Clean_Silver"),
    Input("datasets.Patient_Raw_Bronze"),
)
def compute(ctx, output, patient_bronze):
    """Transform Patient resources from Bronze to Silver.
    
    Args:
        ctx: Transform context.
        output: Output dataset.
        patient_bronze: Input Bronze dataset.
    """
    logger.info("Starting Patient silver transformation")
    
    # Read input dataset
    bronze_df = patient_bronze.dataframe()
    logger.info("Read bronze dataset", count=bronze_df.count())
    
    # Parse JSON data using UDF
    spark = ctx.spark_session
    
    from pyspark.sql.functions import udf
    from pyspark.sql.types import MapType
    
    parse_patient_udf = udf(parse_patient_json, PATIENT_SCHEMA)
    
    # Apply UDF to each row
    parsed_df = bronze_df.select(
        parse_patient_udf(col("json_data")).alias("patient_data"),
        col("ingest_timestamp"),
        col("ingest_date")
    )
    
    # Flatten the struct into columns
    flattened_df = parsed_df.select(
        col("patient_data.id"),
        col("patient_data.identifier"),
        col("patient_data.active"),
        col("patient_data.name_given"),
        col("patient_data.name_family"),
        col("patient_data.name_text"),
        col("patient_data.gender"),
        col("patient_data.birthDate"),
        col("patient_data.address_line"),
        col("patient_data.address_city"),
        col("patient_data.address_state"),
        col("patient_data.address_postalCode"),
        col("patient_data.address_country"),
        col("patient_data.telecom_phone"),
        col("patient_data.telecom_email"),
        col("patient_data.maritalStatus"),
        col("patient_data.communication_language"),
        col("patient_data.meta_lastUpdated"),
        col("patient_data.source"),
        col("ingest_timestamp"),
        col("ingest_date")
    )
    
    # Apply data quality rules
    clean_df = flattened_df.filter(col("id").isNotNull())
    
    # Write to output
    logger.info("Writing Patient silver dataset", count=clean_df.count())
    clean_df.write.partitionBy("ingest_date").format("parquet").mode("overwrite").save(output.uri) 