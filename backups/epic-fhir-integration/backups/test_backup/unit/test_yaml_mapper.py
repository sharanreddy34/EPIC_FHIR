import json
import os
import sys
import pytest
from unittest.mock import patch

import yaml
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, MapType

from fhir_pipeline.transforms.yaml_mappers import apply_mapping

# Create a fixture for SparkSession
@pytest.fixture(scope="module")
def spark():
    spark = SparkSession.builder \
        .appName("test-yaml-mapper") \
        .master("local[2]") \
        .getOrCreate()
    yield spark
    spark.stop()

# Load sample FHIR data
@pytest.fixture(scope="module")
def sample_observation(spark):
    # Sample FHIR Observation resource
    sample_data = {
        "resourceType": "Observation",
        "id": "obs123",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }
            ],
            "text": "Heart rate"
        },
        "subject": {
            "reference": "Patient/pat123"
        },
        "effectiveDateTime": "2023-05-01T12:30:00Z",
        "issued": "2023-05-01T12:35:00Z",
        "valueQuantity": {
            "value": 75,
            "unit": "beats/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    }
    
    # Create a DataFrame with the sample data
    data = [(json.dumps(sample_data), sample_data)]
    schema = StructType([
        StructField("resource_str", StringType(), True),
        StructField("resource", MapType(StringType(), StringType()), True)
    ])
    return spark.createDataFrame(data, schema)

# Sample YAML mapping spec
@pytest.fixture
def observation_mapping():
    return {
        "resourceType": "Observation",
        "version": 1,
        "columns": {
            "observation_id": "id",
            "status": "status",
            "category_code": "category[0].coding[0].code",
            "category_display": "category[0].coding[0].display",
            "code_code": "code.coding[0].code",
            "code_display": "code.coding[0].display",
            "patient_id": "subject.reference.replace('Patient/','')",
            "effective_datetime": "effectiveDateTime",
            "issued_datetime": "issued",
            "value_quantity": "valueQuantity.value",
            "value_unit": "valueQuantity.unit"
        }
    }

def test_apply_mapping_with_observation(spark, sample_observation, observation_mapping):
    """Test applying mapping to an Observation resource."""
    # Apply mapping
    result = apply_mapping(sample_observation, observation_mapping)
    
    # Convert to pandas for easier assertions
    result_pd = result.toPandas()
    
    # Verify number of rows
    assert len(result_pd) == 1, "Should have one row"
    
    # Verify all expected columns are present
    for col_name in observation_mapping["columns"].keys():
        assert col_name in result_pd.columns, f"Column {col_name} should be present"
    
    # Verify values
    row = result_pd.iloc[0]
    assert row["observation_id"] == "obs123"
    assert row["status"] == "final"
    assert row["category_code"] == "vital-signs"
    assert row["category_display"] == "Vital Signs"
    assert row["code_code"] == "8867-4"
    assert row["code_display"] == "Heart rate"
    assert row["patient_id"] == "pat123"
    assert row["effective_datetime"] == "2023-05-01T12:30:00Z"
    assert row["issued_datetime"] == "2023-05-01T12:35:00Z"
    assert row["value_quantity"] == 75
    assert row["value_unit"] == "beats/min"

def test_handle_missing_paths(spark, sample_observation, observation_mapping):
    """Test that missing paths in the resource fallback to None."""
    # Add a non-existent path to the mapping
    mapping_with_missing = observation_mapping.copy()
    mapping_with_missing["columns"]["non_existent"] = "path.that.does.not.exist"
    
    # Apply mapping
    result = apply_mapping(sample_observation, mapping_with_missing)
    
    # Convert to pandas for easier assertions
    result_pd = result.toPandas()
    
    # Verify the non-existent path produces a null value
    assert "non_existent" in result_pd.columns
    assert pd.isna(result_pd.iloc[0]["non_existent"])

def test_apply_mapping_with_fallback_paths(spark, sample_observation):
    """Test mapping with fallback paths using the '|' operator."""
    # Create mapping with fallback
    mapping_with_fallback = {
        "resourceType": "Observation",
        "version": 1,
        "columns": {
            "value": "valueString | valueQuantity.value | valueCodeableConcept.text",
            "observation_id": "id"
        }
    }
    
    # Apply mapping
    result = apply_mapping(sample_observation, mapping_with_fallback)
    
    # Convert to pandas for easier assertions
    result_pd = result.toPandas()
    
    # The valueString doesn't exist, so it should fall back to valueQuantity.value
    assert result_pd.iloc[0]["value"] == 75

def test_text_div_html_stripping(spark):
    """Test that HTML is stripped from narrative text."""
    # Sample with HTML in text.div
    sample_with_html = {
        "resourceType": "Observation",
        "id": "obs456",
        "text": {
            "div": "<div xmlns='http://www.w3.org/1999/xhtml'>Heart rate <b>75</b> beats/min</div>"
        }
    }
    
    # Create a DataFrame with the sample data
    data = [(json.dumps(sample_with_html), sample_with_html)]
    schema = StructType([
        StructField("resource_str", StringType(), True),
        StructField("resource", MapType(StringType(), StringType()), True)
    ])
    df = spark.createDataFrame(data, schema)
    
    # Create mapping for narrative
    mapping = {
        "resourceType": "Observation",
        "version": 1,
        "columns": {
            "narrative": "text.div"
        }
    }
    
    # Apply mapping
    result = apply_mapping(df, mapping)
    
    # Convert to pandas for easier assertions
    result_pd = result.toPandas()
    
    # Verify HTML is stripped
    assert result_pd.iloc[0]["narrative"] == "Heart rate 75 beats/min" 