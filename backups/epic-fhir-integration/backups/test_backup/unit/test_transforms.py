"""
Unit tests for the FHIR transformation components.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from fhir_pipeline.transforms.base import BaseTransformer
from fhir_pipeline.transforms.field_extractor import FieldExtractor
from fhir_pipeline.transforms.path_extractor import PathExtractor
from fhir_pipeline.transforms.yaml_mapper import YAMLMapper


# Test data for transformations
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
        StructField("birthDate", StringType(), True),
        StructField("address", ArrayType(
            StructType([
                StructField("line", ArrayType(StringType()), True),
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("postalCode", StringType(), True)
            ])
        ), True)
    ])
    
    patient_data = [
        {
            "id": "patient1", 
            "resourceType": "Patient",
            "name": [{"family": "Smith", "given": ["John", "Q"], "use": "official"}],
            "gender": "male",
            "birthDate": "1970-01-01",
            "address": [{"line": ["123 Main St"], "city": "Anytown", "state": "CA", "postalCode": "12345"}]
        },
        {
            "id": "patient2", 
            "resourceType": "Patient",
            "name": [{"family": "Johnson", "given": ["Sarah"], "use": "official"}],
            "gender": "female",
            "birthDate": "1980-05-15",
            "address": [{"line": ["456 Oak Ave"], "city": "Somewhere", "state": "NY", "postalCode": "67890"}]
        }
    ]
    
    return spark.createDataFrame(patient_data, schema=patient_schema)


class TestBaseTransformer:
    """Tests for the BaseTransformer class."""
    
    def test_transform_method_requires_implementation(self, spark, patient_data):
        """Test that the transform method must be implemented by subclasses."""
        # Create a transformer that doesn't override transform
        class EmptyTransformer(BaseTransformer):
            pass
            
        transformer = EmptyTransformer(spark)
        
        # Attempting to call transform should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            transformer.transform(patient_data)
    
    def test_base_transformer_properties(self, spark):
        """Test basic properties of the BaseTransformer."""
        transformer = BaseTransformer(spark)
        
        # Verify properties
        assert transformer.spark == spark
        assert hasattr(transformer, "transform")


class TestFieldExtractor:
    """Tests for the FieldExtractor class."""
    
    def test_simple_field_extraction(self, spark, patient_data):
        """Test extraction of a simple field."""
        # Create a field extractor for the 'gender' field
        extractor = FieldExtractor(
            spark=spark,
            source_field="gender",
            target_field="patient_gender"
        )
        
        # Transform the data
        result_df = extractor.transform(patient_data)
        
        # Verify the result has the new field with the correct values
        assert "patient_gender" in result_df.columns
        result_data = result_df.collect()
        assert result_data[0].patient_gender == "male"
        assert result_data[1].patient_gender == "female"
        
        # Verify original field is still present
        assert "gender" in result_df.columns
    
    def test_nested_field_extraction(self, spark, patient_data):
        """Test extraction of a nested field."""
        # Create a field extractor for the nested field 'name.family'
        extractor = FieldExtractor(
            spark=spark,
            source_field="name[0].family",
            target_field="last_name"
        )
        
        # Transform the data
        result_df = extractor.transform(patient_data)
        
        # Verify the result has the new field with the correct values
        assert "last_name" in result_df.columns
        result_data = result_df.collect()
        assert result_data[0].last_name == "Smith"
        assert result_data[1].last_name == "Johnson"
    
    def test_array_field_extraction(self, spark, patient_data):
        """Test extraction from an array field."""
        # Create a field extractor for the array field 'name[0].given[0]'
        extractor = FieldExtractor(
            spark=spark,
            source_field="name[0].given[0]",
            target_field="first_name"
        )
        
        # Transform the data
        result_df = extractor.transform(patient_data)
        
        # Verify the result has the new field with the correct values
        assert "first_name" in result_df.columns
        result_data = result_df.collect()
        assert result_data[0].first_name == "John"
        assert result_data[1].first_name == "Sarah"


class TestPathExtractor:
    """Tests for the PathExtractor class."""
    
    def test_extract_multiple_fields(self, spark, patient_data):
        """Test extraction of multiple fields."""
        # Define mapping of source paths to target fields
        path_mapping = {
            "id": "patient_id",
            "name[0].family": "last_name",
            "name[0].given[0]": "first_name",
            "gender": "patient_gender",
            "birthDate": "date_of_birth",
            "address[0].city": "city",
            "address[0].state": "state"
        }
        
        # Create a path extractor
        extractor = PathExtractor(
            spark=spark,
            path_mapping=path_mapping
        )
        
        # Transform the data
        result_df = extractor.transform(patient_data)
        
        # Verify all target fields are present
        for target_field in path_mapping.values():
            assert target_field in result_df.columns
        
        # Verify values for the first patient
        result_data = result_df.collect()
        patient1 = result_data[0]
        assert patient1.patient_id == "patient1"
        assert patient1.last_name == "Smith"
        assert patient1.first_name == "John"
        assert patient1.patient_gender == "male"
        assert patient1.date_of_birth == "1970-01-01"
        assert patient1.city == "Anytown"
        assert patient1.state == "CA"
        
        # Verify original fields are still present
        assert "id" in result_df.columns
        assert "name" in result_df.columns
    
    def test_handle_missing_fields(self, spark, patient_data):
        """Test handling of missing fields."""
        # Define mapping with a non-existent field
        path_mapping = {
            "id": "patient_id",
            "nonexistent_field": "missing_value",
            "name[0].family": "last_name"
        }
        
        # Create a path extractor
        extractor = PathExtractor(
            spark=spark,
            path_mapping=path_mapping
        )
        
        # Transform the data
        result_df = extractor.transform(patient_data)
        
        # Verify fields are present
        assert "patient_id" in result_df.columns
        assert "missing_value" in result_df.columns
        assert "last_name" in result_df.columns
        
        # Verify values
        result_data = result_df.collect()
        assert result_data[0].patient_id == "patient1"
        assert result_data[0].missing_value is None  # Missing field should be null
        assert result_data[0].last_name == "Smith"


class TestYAMLMapper:
    """Tests for the YAMLMapper class."""
    
    @pytest.fixture
    def sample_yaml_config(self, tmp_path):
        """Create a sample YAML configuration file."""
        yaml_content = """
        name: patient_transformer
        description: Transforms patient data to a simplified format
        source_resource: Patient
        target_table: patients_simple
        mappings:
          - source: id
            target: patient_id
          - source: name[0].family
            target: last_name
          - source: name[0].given[0]
            target: first_name
          - source: gender
            target: gender
          - source: birthDate
            target: date_of_birth
          - source: address[0].city
            target: city
          - source: address[0].state
            target: state
          - source: address[0].postalCode
            target: zip_code
        """
        
        # Write YAML to a temporary file
        yaml_file = tmp_path / "patient_transform.yaml"
        yaml_file.write_text(yaml_content)
        
        return str(yaml_file)
    
    def test_yaml_mapper_transform(self, spark, patient_data, sample_yaml_config):
        """Test transformation using a YAML configuration."""
        # Create a YAML mapper
        mapper = YAMLMapper(
            spark=spark,
            config_path=sample_yaml_config
        )
        
        # Transform the data
        result_df = mapper.transform(patient_data)
        
        # Verify the target fields are present
        expected_fields = [
            "patient_id", "last_name", "first_name", "gender", 
            "date_of_birth", "city", "state", "zip_code"
        ]
        for field in expected_fields:
            assert field in result_df.columns
        
        # Verify the values for the first patient
        result_data = result_df.collect()
        patient1 = result_data[0]
        assert patient1.patient_id == "patient1"
        assert patient1.last_name == "Smith"
        assert patient1.first_name == "John"
        assert patient1.gender == "male"
        assert patient1.date_of_birth == "1970-01-01"
        assert patient1.city == "Anytown"
        assert patient1.state == "CA"
        assert patient1.zip_code == "12345"
        
        # Verify the original fields are not present (unless they're mapped)
        assert "resourceType" not in result_df.columns
        assert "name" not in result_df.columns
        assert "address" not in result_df.columns
    
    def test_yaml_mapper_properties(self, spark, sample_yaml_config):
        """Test basic properties of the YAMLMapper."""
        # Create a YAML mapper
        mapper = YAMLMapper(
            spark=spark,
            config_path=sample_yaml_config
        )
        
        # Verify properties
        assert mapper.config["name"] == "patient_transformer"
        assert mapper.config["source_resource"] == "Patient"
        assert mapper.config["target_table"] == "patients_simple"
        assert len(mapper.config["mappings"]) == 8 