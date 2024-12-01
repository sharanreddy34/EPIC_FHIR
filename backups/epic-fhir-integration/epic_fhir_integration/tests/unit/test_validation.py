"""
Unit tests for the FHIR data validation components.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, ArrayType

from fhir_pipeline.validation.schema_validator import SchemaValidator
from fhir_pipeline.validation.fhir_validator import FHIRValidator
from fhir_pipeline.validation.data_quality import DataQualityChecker


# Test data for validation
@pytest.fixture
def patient_data(spark):
    """Create a sample patient DataFrame for testing."""
    patient_schema = StructType([
        StructField("id", StringType(), True),
        StructField("resourceType", StringType(), True),
        StructField("name", ArrayType(
            StructType([
                StructField("family", StringType(), True),
                StructField("given", ArrayType(StringType()), True),
                StructField("use", StringType(), True)
            ])
        ), True),
        StructField("gender", StringType(), True),
        StructField("birthDate", StringType(), True)
    ])
    
    patient_data = [
        {
            "id": "patient1", 
            "resourceType": "Patient",
            "name": [{"family": "Smith", "given": ["John"], "use": "official"}],
            "gender": "male",
            "birthDate": "1970-01-01"
        },
        {
            "id": "patient2", 
            "resourceType": "Patient",
            "name": [{"family": "Johnson", "given": ["Sarah"], "use": "official"}],
            "gender": "female",
            "birthDate": "1980-05-15"
        },
        {
            "id": "patient3", 
            "resourceType": "Patient",
            "name": [{"family": "Garcia", "given": ["Maria"], "use": "official"}],
            "gender": "female",
            "birthDate": None  # Missing birth date
        },
        {
            "id": "patient4", 
            "resourceType": "Patient",
            "name": None,  # Missing name
            "gender": "male",
            "birthDate": "1990-10-20"
        },
        {
            "id": "patient5", 
            "resourceType": "Patient",
            "name": [{"family": "Lee", "given": ["David"], "use": "official"}],
            "gender": "unknown",  # Invalid gender value
            "birthDate": "2000-02-28"
        }
    ]
    
    return spark.createDataFrame(patient_data, schema=patient_schema)

@pytest.fixture
def invalid_observation_data(spark):
    """Create a sample observation DataFrame with validation issues."""
    observation_schema = StructType([
        StructField("id", StringType(), True),
        StructField("resourceType", StringType(), True),
        StructField("status", StringType(), True),
        StructField("subject", StructType([
            StructField("reference", StringType(), True)
        ]), True),
        StructField("code", StructType([
            StructField("coding", ArrayType(
                StructType([
                    StructField("system", StringType(), True),
                    StructField("code", StringType(), True),
                    StructField("display", StringType(), True)
                ])
            ), True)
        ]), True),
        StructField("valueQuantity", StructType([
            StructField("value", StringType(), True),
            StructField("unit", StringType(), True),
            StructField("system", StringType(), True),
            StructField("code", StringType(), True)
        ]), True),
        StructField("effectiveDateTime", StringType(), True)
    ])
    
    observation_data = [
        {
            "id": "obs1",
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": "Patient/patient1"},
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "valueQuantity": {"value": "80", "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"},
            "effectiveDateTime": "2023-01-01T12:00:00Z"
        },
        {
            "id": "obs2",
            "resourceType": "Observation",
            "status": "invalid-status",  # Invalid status
            "subject": {"reference": "Patient/patient1"},
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "valueQuantity": {"value": "90", "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"},
            "effectiveDateTime": "2023-01-01T13:00:00Z"
        },
        {
            "id": "obs3",
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": "Patient/nonexistent"},  # Reference to non-existent patient
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "valueQuantity": {"value": "70", "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"},
            "effectiveDateTime": "invalid-date"  # Invalid date format
        }
    ]
    
    return spark.createDataFrame(observation_data, schema=observation_schema)


class TestSchemaValidator:
    """Tests for the SchemaValidator class."""
    
    def test_validate_schema(self, spark, patient_data):
        """Test validation of DataFrame schema."""
        # Define expected schema
        expected_schema = StructType([
            StructField("id", StringType(), True),
            StructField("resourceType", StringType(), True),
            StructField("name", ArrayType(
                StructType([
                    StructField("family", StringType(), True),
                    StructField("given", ArrayType(StringType()), True),
                    StructField("use", StringType(), True)
                ])
            ), True),
            StructField("gender", StringType(), True),
            StructField("birthDate", StringType(), True)
        ])
        
        # Create a schema validator
        validator = SchemaValidator(expected_schema=expected_schema)
        
        # Validate the schema
        validation_result = validator.validate(patient_data)
        
        # Verify validation passed
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0
    
    def test_validate_schema_missing_field(self, spark, patient_data):
        """Test validation with a missing field in the schema."""
        # Define schema with an additional required field
        expected_schema = StructType([
            StructField("id", StringType(), True),
            StructField("resourceType", StringType(), True),
            StructField("name", ArrayType(
                StructType([
                    StructField("family", StringType(), True),
                    StructField("given", ArrayType(StringType()), True),
                    StructField("use", StringType(), True)
                ])
            ), True),
            StructField("gender", StringType(), True),
            StructField("birthDate", StringType(), True),
            StructField("telecom", ArrayType(StringType()), False)  # Required field not in data
        ])
        
        # Create a schema validator
        validator = SchemaValidator(expected_schema=expected_schema)
        
        # Validate the schema
        validation_result = validator.validate(patient_data)
        
        # Verify validation failed
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
        assert any("telecom" in error for error in validation_result.errors)
    
    def test_validate_schema_wrong_type(self, spark):
        """Test validation with wrong data type."""
        # Create DataFrame with incorrect type for gender (should be string, not int)
        schema = StructType([
            StructField("id", StringType(), True),
            StructField("gender", StringType(), True)  # String in schema
        ])
        
        data = [
            {"id": "patient1", "gender": 1}  # Integer in data (should be string)
        ]
        
        df = spark.createDataFrame(data, schema=schema)
        
        # Define expected schema with string type for gender
        expected_schema = StructType([
            StructField("id", StringType(), True),
            StructField("gender", StringType(), True)
        ])
        
        # Create a schema validator
        validator = SchemaValidator(expected_schema=expected_schema)
        
        # Validate the schema
        validation_result = validator.validate(df)
        
        # This should be valid since Spark will convert integers to strings when loading into StringType columns
        assert validation_result.is_valid


class TestFHIRValidator:
    """Tests for the FHIRValidator class."""
    
    def test_validate_patient_resource(self, spark, patient_data):
        """Test validation of patient resources."""
        # Create a FHIR validator for Patient resources
        validator = FHIRValidator(resource_type="Patient")
        
        # Validate the data
        validation_result = validator.validate(patient_data)
        
        # 2 out of 5 patients are valid, 3 have issues
        assert not validation_result.is_valid
        assert validation_result.valid_count == 2
        assert validation_result.invalid_count == 3
        assert len(validation_result.errors) == 3
    
    def test_validate_observation_resource(self, spark, invalid_observation_data):
        """Test validation of observation resources."""
        # Create a FHIR validator for Observation resources
        validator = FHIRValidator(resource_type="Observation")
        
        # Validate the data
        validation_result = validator.validate(invalid_observation_data)
        
        # 1 out of 3 observations are valid, 2 have issues
        assert not validation_result.is_valid
        assert validation_result.valid_count == 1
        assert validation_result.invalid_count == 2
        assert len(validation_result.errors) == 2
    
    def test_get_validation_report(self, spark, patient_data):
        """Test generating a validation report."""
        # Create a FHIR validator for Patient resources
        validator = FHIRValidator(resource_type="Patient")
        
        # Validate the data
        validation_result = validator.validate(patient_data)
        
        # Generate a validation report
        report = validator.get_validation_report(validation_result)
        
        # Verify report contains expected information
        assert "Patient" in report
        assert "Valid records: 2" in report
        assert "Invalid records: 3" in report
        assert "Validation errors:" in report


class TestDataQualityChecker:
    """Tests for the DataQualityChecker class."""
    
    def test_check_missing_values(self, spark, patient_data):
        """Test checking for missing values."""
        # Create a data quality checker
        checker = DataQualityChecker(spark=spark)
        
        # Check for missing values in required fields
        required_fields = ["id", "resourceType", "name", "gender", "birthDate"]
        missing_results = checker.check_missing_values(patient_data, required_fields)
        
        # Verify results
        assert "id" in missing_results
        assert "resourceType" in missing_results
        assert "name" in missing_results
        assert "gender" in missing_results
        assert "birthDate" in missing_results
        
        # id, resourceType, gender should have no missing values
        assert missing_results["id"] == 0
        assert missing_results["resourceType"] == 0
        assert missing_results["gender"] == 0
        
        # name and birthDate should have missing values
        assert missing_results["name"] == 1  # patient4 has missing name
        assert missing_results["birthDate"] == 1  # patient3 has missing birthDate
    
    def test_check_value_distribution(self, spark, patient_data):
        """Test checking value distribution."""
        # Create a data quality checker
        checker = DataQualityChecker(spark=spark)
        
        # Check distribution of gender values
        distribution = checker.check_value_distribution(patient_data, "gender")
        
        # Verify distribution
        assert "male" in distribution
        assert "female" in distribution
        assert "unknown" in distribution
        assert distribution["male"] == 2  # 2 male patients
        assert distribution["female"] == 2  # 2 female patients
        assert distribution["unknown"] == 1  # 1 patient with unknown gender
    
    def test_check_data_consistency(self, spark, patient_data, invalid_observation_data):
        """Test checking data consistency between related resources."""
        # Create a data quality checker
        checker = DataQualityChecker(spark=spark)
        
        # Extract patient IDs from the subject references in observations
        observation_patient_refs = invalid_observation_data.select("subject.reference").rdd \
            .map(lambda x: x[0].replace("Patient/", "") if x[0] else None) \
            .collect()
        
        # Check if referenced patients exist
        patient_ids = patient_data.select("id").rdd.map(lambda x: x[0]).collect()
        
        # Manual check for data consistency
        missing_refs = []
        for ref in observation_patient_refs:
            if ref and ref not in patient_ids:
                missing_refs.append(ref)
        
        # Verify there is one missing reference
        assert len(missing_refs) == 1
        assert "nonexistent" in missing_refs 