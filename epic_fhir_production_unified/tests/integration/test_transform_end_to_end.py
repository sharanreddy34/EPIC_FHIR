import json
import os
import sys
import tempfile
import pytest
from unittest.mock import patch

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, explode

from fhir_pipeline.transforms.registry import get_transformer
from fhir_pipeline.pipelines.transform_load import transform_resource

# Sample bundle data path
SAMPLE_BUNDLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample_patient_bundle.json")

# Create a fixture for SparkSession
@pytest.fixture(scope="module")
def spark():
    spark = SparkSession.builder \
        .appName("test-transform-end-to-end") \
        .master("local[2]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    yield spark
    spark.stop()

# Load and explode the sample bundle
@pytest.fixture(scope="module")
def sample_bundle_df(spark):
    # Ensure sample data exists
    if not os.path.exists(SAMPLE_BUNDLE_PATH):
        # If sample file doesn't exist, create a minimal one for testing
        os.makedirs(os.path.dirname(SAMPLE_BUNDLE_PATH), exist_ok=True)
        
        with open(SAMPLE_BUNDLE_PATH, 'w') as f:
            json.dump(_create_test_bundle(), f)
    
    # Load the bundle
    with open(SAMPLE_BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)
    
    # Create DataFrame with bundle entries
    entries = bundle.get("entry", [])
    
    # Extract resources from entries
    resources = []
    for entry in entries:
        if "resource" in entry:
            resources.append((entry["resource"].get("resourceType"), entry["resource"]))
    
    # Create DataFrame
    return spark.createDataFrame(resources, ["resourceType", "resource"])

# Create a temp directory for output
@pytest.fixture(scope="function")
def temp_output_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

def _create_test_bundle():
    """Create a minimal test bundle with Patient and Observation resources."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "test-patient-1",
                    "name": [
                        {
                            "family": "Test",
                            "given": ["Patient"]
                        }
                    ],
                    "gender": "male",
                    "birthDate": "1970-01-01"
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "test-obs-1",
                    "status": "final",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8867-4",
                                "display": "Heart rate"
                            }
                        ]
                    },
                    "subject": {
                        "reference": "Patient/test-patient-1"
                    },
                    "issued": "2023-01-01T12:00:00Z",
                    "valueQuantity": {
                        "value": 70,
                        "unit": "beats/min"
                    }
                }
            }
        ]
    }

def test_end_to_end_transform_patient(spark, sample_bundle_df, temp_output_dir):
    """Test end-to-end transformation of Patient resources."""
    # Filter for Patient resources
    patient_df = sample_bundle_df.filter(col("resourceType") == "Patient")
    
    # Create input and output paths
    input_path = os.path.join(temp_output_dir, "bronze", "patient")
    output_path = os.path.join(temp_output_dir, "silver", "patient")
    
    # Write input data
    patient_df.write.format("delta").save(input_path)
    
    # Mock config directory to point to our test config
    with patch.dict(os.environ, {"FHIR_CONFIG_DIR": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fhir_pipeline", "config")}):
        # Run transform
        transform_resource(spark, "Patient", input_path, output_path)
    
    # Read output data
    output_df = spark.read.format("delta").load(output_path)
    
    # Assertions
    assert output_df.count() == patient_df.count(), "Output should have same number of rows as input"
    
    # Check expected columns exist
    required_columns = ["patient_id", "name_family", "name_given", "gender", "birth_date"]
    for col_name in required_columns:
        assert col_name in output_df.columns, f"Column {col_name} should be present"
    
    # Verify no duplicates in output based on hash_id
    assert output_df.select("_hash_id").distinct().count() == output_df.count(), "No duplicates should exist in output"
    
    # Verify data contents
    output_pd = output_df.toPandas()
    
    # Check a patient record
    patient_row = output_pd[output_pd["patient_id"] == "test-patient-1"].iloc[0]
    assert patient_row["name_family"] == "Test"
    assert patient_row["gender"] == "male"
    assert patient_row["birth_date"] == "1970-01-01"

def test_end_to_end_transform_observation(spark, sample_bundle_df, temp_output_dir):
    """Test end-to-end transformation of Observation resources."""
    # Filter for Observation resources
    obs_df = sample_bundle_df.filter(col("resourceType") == "Observation")
    
    # Create input and output paths
    input_path = os.path.join(temp_output_dir, "bronze", "observation")
    output_path = os.path.join(temp_output_dir, "silver", "observation")
    
    # Write input data
    obs_df.write.format("delta").save(input_path)
    
    # Mock config directory to point to our test config
    with patch.dict(os.environ, {"FHIR_CONFIG_DIR": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fhir_pipeline", "config")}):
        # Run transform
        transform_resource(spark, "Observation", input_path, output_path)
    
    # Read output data
    output_df = spark.read.format("delta").load(output_path)
    
    # Assertions
    assert output_df.count() == obs_df.count(), "Output should have same number of rows as input"
    
    # Check expected columns exist
    required_columns = ["observation_id", "patient_id", "code_code", "value_quantity", "issued_datetime"]
    for col_name in required_columns:
        assert col_name in output_df.columns, f"Column {col_name} should be present"
    
    # Verify data contents
    output_pd = output_df.toPandas()
    
    # Check an observation record
    obs_row = output_pd[output_pd["observation_id"] == "test-obs-1"].iloc[0]
    assert obs_row["patient_id"] == "test-patient-1"
    assert obs_row["code_code"] == "8867-4"
    assert obs_row["value_quantity"] == 70
    assert obs_row["issued_datetime"] == "2023-01-01T12:00:00Z" 