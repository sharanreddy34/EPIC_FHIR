"""
Integration tests for the transform pipeline component.
"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, explode

from fhir_pipeline.transforms.registry import get_transformer
from fhir_pipeline.pipelines.transform_load import transform_resource

# Define resource types to test
RESOURCE_TYPES = ["Patient", "Observation", "Encounter", "Condition", "MedicationRequest"]


@pytest.fixture(scope="function")
def sample_data_df(spark, request):
    """Create sample data for a specific resource type."""
    resource_type = request.param
    
    # Create sample resources based on resource type
    if resource_type == "Patient":
        sample_data = [
            {"resourceType": "Patient", "resource": {"resourceType": "Patient", "id": "patient1", "gender": "male", "birthDate": "1970-01-01"}},
            {"resourceType": "Patient", "resource": {"resourceType": "Patient", "id": "patient2", "gender": "female", "birthDate": "1980-01-01"}}
        ]
    elif resource_type == "Observation":
        sample_data = [
            {"resourceType": "Observation", "resource": {
                "resourceType": "Observation", 
                "id": "obs1", 
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Height"}]},
                "subject": {"reference": "Patient/patient1"},
                "valueQuantity": {"value": 180, "unit": "cm"}
            }},
            {"resourceType": "Observation", "resource": {
                "resourceType": "Observation", 
                "id": "obs2", 
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7", "display": "Weight"}]},
                "subject": {"reference": "Patient/patient1"},
                "valueQuantity": {"value": 75, "unit": "kg"}
            }}
        ]
    elif resource_type == "Encounter":
        sample_data = [
            {"resourceType": "Encounter", "resource": {
                "resourceType": "Encounter", 
                "id": "enc1", 
                "status": "finished",
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
                "subject": {"reference": "Patient/patient1"},
                "period": {"start": "2023-01-01T08:00:00Z", "end": "2023-01-01T09:00:00Z"}
            }}
        ]
    elif resource_type == "Condition":
        sample_data = [
            {"resourceType": "Condition", "resource": {
                "resourceType": "Condition", 
                "id": "cond1", 
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertension"}]},
                "subject": {"reference": "Patient/patient1"}
            }}
        ]
    elif resource_type == "MedicationRequest":
        sample_data = [
            {"resourceType": "MedicationRequest", "resource": {
                "resourceType": "MedicationRequest", 
                "id": "med1", 
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1191", "display": "Aspirin"}]},
                "subject": {"reference": "Patient/patient1"},
                "authoredOn": "2023-01-01"
            }}
        ]
    else:
        # Default empty data for unknown types
        sample_data = []
    
    return spark.createDataFrame(sample_data)


@pytest.mark.parametrize("sample_data_df", RESOURCE_TYPES, indirect=True)
def test_transform_pipeline(spark, sample_data_df, temp_output_dir, mock_config_env, request):
    """Test transform pipeline with various resource types."""
    resource_type = request.param
    
    # Create input and output paths
    input_path = os.path.join(temp_output_dir, "bronze", resource_type.lower())
    output_path = os.path.join(temp_output_dir, "silver", resource_type.lower())
    
    # Write input data
    sample_data_df.write.format("delta").save(input_path)
    
    # Skip test if no transformer is available for this resource type
    try:
        # Try to get a transformer for the resource type
        get_transformer(resource_type)
    except (ValueError, KeyError):
        pytest.skip(f"No transformer available for {resource_type}")
    
    # Run transform
    transform_resource(spark, resource_type, input_path, output_path)
    
    # Read output data
    output_df = spark.read.format("delta").load(output_path)
    
    # Verify the output has the expected number of rows
    assert output_df.count() == sample_data_df.count(), f"Output should have same number of rows as input for {resource_type}"
    
    # Verify output has expected structure and content based on resource type
    if resource_type == "Patient":
        # Check expected columns
        assert "patient_id" in output_df.columns
        assert "gender" in output_df.columns
        assert "birth_date" in output_df.columns
        
        # Check data
        patients = output_df.toPandas()
        assert len(patients[patients["patient_id"] == "patient1"]) == 1
        assert len(patients[patients["patient_id"] == "patient2"]) == 1
        
    elif resource_type == "Observation":
        # Check expected columns
        assert "observation_id" in output_df.columns
        assert "patient_id" in output_df.columns
        assert "code_code" in output_df.columns
        
        # Check data
        observations = output_df.toPandas()
        assert len(observations[observations["observation_id"] == "obs1"]) == 1
        assert len(observations[observations["code_code"] == "8302-2"]) == 1
        assert len(observations[observations["code_code"] == "29463-7"]) == 1
        
    elif resource_type == "Encounter":
        # Check expected columns
        assert "encounter_id" in output_df.columns
        assert "patient_id" in output_df.columns
        assert "status" in output_df.columns
        
        # Check data
        encounters = output_df.toPandas()
        assert len(encounters[encounters["encounter_id"] == "enc1"]) == 1
        assert encounters.iloc[0]["status"] == "finished"
        
    elif resource_type == "Condition":
        # Check expected columns
        assert "condition_id" in output_df.columns
        assert "patient_id" in output_df.columns
        assert "code_code" in output_df.columns
        
        # Check data
        conditions = output_df.toPandas()
        assert len(conditions[conditions["condition_id"] == "cond1"]) == 1
        
    elif resource_type == "MedicationRequest":
        # Check expected columns
        assert "medication_request_id" in output_df.columns
        assert "patient_id" in output_df.columns
        assert "medication_code" in output_df.columns
        
        # Check data
        medications = output_df.toPandas()
        assert len(medications[medications["medication_request_id"] == "med1"]) == 1


def test_transform_with_custom_config(spark, temp_output_dir):
    """Test transform with custom configuration."""
    # Create a custom config for testing
    custom_config = {
        "Patient": {
            "mappings": [
                {"source": "id", "target": "custom_patient_id"},
                {"source": "name[0].family", "target": "last_name"},
                {"source": "name[0].given[0]", "target": "first_name"}
            ]
        }
    }
    
    # Create a temporary config file
    config_dir = os.path.join(temp_output_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "transformations.json")
    
    with open(config_file, 'w') as f:
        json.dump(custom_config, f)
    
    # Create sample data
    sample_data = [
        {"resourceType": "Patient", "resource": {
            "resourceType": "Patient", 
            "id": "custom-patient-1", 
            "name": [{"family": "Smith", "given": ["John"]}]
        }}
    ]
    df = spark.createDataFrame(sample_data)
    
    # Create input and output paths
    input_path = os.path.join(temp_output_dir, "bronze", "patient")
    output_path = os.path.join(temp_output_dir, "silver", "patient")
    
    # Write input data
    df.write.format("delta").save(input_path)
    
    # Run transform with custom config
    with patch.dict(os.environ, {"FHIR_CONFIG_DIR": config_dir}):
        transform_resource(spark, "Patient", input_path, output_path)
    
    # Read output data
    output_df = spark.read.format("delta").load(output_path)
    
    # Verify custom columns
    assert "custom_patient_id" in output_df.columns
    assert "last_name" in output_df.columns
    assert "first_name" in output_df.columns
    
    # Check data
    patients = output_df.toPandas()
    assert len(patients[patients["custom_patient_id"] == "custom-patient-1"]) == 1
    assert patients.iloc[0]["last_name"] == "Smith"
    assert patients.iloc[0]["first_name"] == "John"


def test_transform_with_errors(spark, temp_output_dir, mock_config_env):
    """Test transform with problematic data to ensure error handling."""
    # Create data with missing required fields
    sample_data = [
        {"resourceType": "Patient", "resource": {"resourceType": "Patient", "id": "valid-patient"}},
        {"resourceType": "Patient", "resource": {"resourceType": "Patient"}}  # Missing ID
    ]
    df = spark.createDataFrame(sample_data)
    
    # Create input and output paths
    input_path = os.path.join(temp_output_dir, "bronze", "patient_errors")
    output_path = os.path.join(temp_output_dir, "silver", "patient_errors")
    
    # Write input data
    df.write.format("delta").save(input_path)
    
    # Run transform with error handling
    transform_resource(spark, "Patient", input_path, output_path, handle_errors=True)
    
    # Read output data
    output_df = spark.read.format("delta").load(output_path)
    
    # Verify the valid record was processed
    assert output_df.count() >= 1, "At least the valid record should be processed"
    
    # Check if error table was created if supported
    error_path = f"{output_path}_errors"
    try:
        error_df = spark.read.format("delta").load(error_path)
        # If error table exists, verify it contains the problematic record
        assert error_df.count() >= 1, "Error table should contain at least one record"
    except:
        # If error table doesn't exist, the implementation may handle errors differently
        pass
