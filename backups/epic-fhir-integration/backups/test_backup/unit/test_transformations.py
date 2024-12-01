"""
Unit tests for FHIR data transformations.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock

import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType, MapType

from fhir_pipeline.transforms.yaml_mappers import YAMLMapper, FieldExtractor
from fhir_pipeline.transforms.base import FHIRTransformer, PathExtractor


class TestFieldExtractor:
    """Test the field extractor used for mapping FHIR elements to columns."""

    def test_simple_path_extraction(self):
        """Test extracting a simple path from a nested object."""
        # Simple object with a direct path
        obj = {"id": "test-id", "status": "active"}
        
        # Extract the value
        extractor = FieldExtractor()
        result = extractor.extract_value(obj, "id")
        
        assert result == "test-id"
    
    def test_nested_path_extraction(self):
        """Test extracting a nested path from an object."""
        # Nested object
        obj = {
            "id": "test-id",
            "meta": {
                "versionId": "1",
                "lastUpdated": "2023-01-01T12:00:00Z"
            }
        }
        
        # Extract nested value
        extractor = FieldExtractor()
        result = extractor.extract_value(obj, "meta.lastUpdated")
        
        assert result == "2023-01-01T12:00:00Z"
    
    def test_array_path_extraction(self):
        """Test extracting from an array using index."""
        # Object with array
        obj = {
            "id": "test-id",
            "name": [
                {"use": "official", "family": "Smith", "given": ["John", "Jacob"]},
                {"use": "nickname", "family": "Smith", "given": ["Johnny"]}
            ]
        }
        
        # Extract from array with index
        extractor = FieldExtractor()
        result = extractor.extract_value(obj, "name[0].family")
        assert result == "Smith"
        
        # Extract from nested array
        result = extractor.extract_value(obj, "name[0].given[1]")
        assert result == "Jacob"
    
    def test_missing_path(self):
        """Test behavior with missing paths."""
        obj = {"id": "test-id"}
        
        extractor = FieldExtractor()
        # Missing top-level field
        assert extractor.extract_value(obj, "status") is None
        
        # Missing nested field
        assert extractor.extract_value(obj, "meta.lastUpdated") is None
        
        # Missing array index
        assert extractor.extract_value(obj, "name[0].family") is None
    
    def test_wildcard_array_extraction(self):
        """Test extracting all elements from an array using wildcard."""
        obj = {
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "8302-2", "display": "Height"},
                    {"system": "http://snomed.info/sct", "code": "50373000", "display": "Height"}
                ]
            }
        }
        
        extractor = FieldExtractor()
        # Extract all codes from coding array
        result = extractor.extract_value(obj, "code.coding[*].code")
        
        assert isinstance(result, list)
        assert result == ["8302-2", "50373000"]
    
    def test_conditional_extraction(self):
        """Test extracting based on a condition."""
        obj = {
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "8302-2", "display": "Height"},
                    {"system": "http://snomed.info/sct", "code": "50373000", "display": "Height"}
                ]
            }
        }
        
        extractor = FieldExtractor()
        # Extract code where system is LOINC
        result = extractor.extract_value(obj, "code.coding[?system='http://loinc.org'].code")
        
        assert result == "8302-2"


class TestYAMLMapper:
    """Test the YAML-based mapping functionality."""
    
    def test_load_from_string(self):
        """Test loading mappings from a YAML string."""
        yaml_str = """
        resourceType: Patient
        mappings:
          - source: id
            target: patient_id
          - source: gender
            target: gender
          - source: birthDate
            target: birth_date
        """
        
        mapper = YAMLMapper.from_string(yaml_str)
        
        assert mapper.resource_type == "Patient"
        assert len(mapper.mappings) == 3
        assert mapper.mappings[0]["source"] == "id"
        assert mapper.mappings[0]["target"] == "patient_id"
    
    def test_load_from_file(self, tmp_path):
        """Test loading mappings from a YAML file."""
        # Create a temporary YAML file
        yaml_content = """
        resourceType: Observation
        mappings:
          - source: id
            target: observation_id
          - source: code.coding[0].code
            target: code
        """
        
        file_path = tmp_path / "observation_mapping.yaml"
        with open(file_path, "w") as f:
            f.write(yaml_content)
        
        # Load from file
        mapper = YAMLMapper.from_file(file_path)
        
        assert mapper.resource_type == "Observation"
        assert len(mapper.mappings) == 2
        assert mapper.mappings[1]["source"] == "code.coding[0].code"
        assert mapper.mappings[1]["target"] == "code"
    
    def test_generate_extraction_udf(self, spark):
        """Test generating a UDF for field extraction."""
        yaml_str = """
        resourceType: Patient
        mappings:
          - source: id
            target: patient_id
          - source: gender
            target: gender
        """
        
        mapper = YAMLMapper.from_string(yaml_str)
        extract_udf = mapper.generate_extraction_udf()
        
        # Test with a simple object
        data = [{"resource": {"id": "test-patient", "gender": "male"}}]
        df = spark.createDataFrame(data, ["resource"])
        
        # Apply UDF
        result_df = df.withColumn("extracted", extract_udf(F.col("resource")))
        result = result_df.collect()[0]["extracted"]
        
        # Verify result structure
        assert result["patient_id"] == "test-patient"
        assert result["gender"] == "male"
    
    def test_missing_fields_in_udf(self, spark):
        """Test UDF behavior with missing fields."""
        yaml_str = """
        resourceType: Patient
        mappings:
          - source: id
            target: patient_id
          - source: nonexistent.field
            target: missing_value
        """
        
        mapper = YAMLMapper.from_string(yaml_str)
        extract_udf = mapper.generate_extraction_udf()
        
        # Test with a simple object
        data = [{"resource": {"id": "test-patient"}}]
        df = spark.createDataFrame(data, ["resource"])
        
        # Apply UDF
        result_df = df.withColumn("extracted", extract_udf(F.col("resource")))
        result = result_df.collect()[0]["extracted"]
        
        # Verify result structure
        assert result["patient_id"] == "test-patient"
        assert result["missing_value"] is None


class TestFHIRTransformer:
    """Test the base FHIR transformer functionality."""
    
    def test_basic_transformation(self, spark):
        """Test basic transformation of FHIR resources."""
        # Create a simple transformer
        class SimplePatientTransformer(FHIRTransformer):
            def transform(self, df):
                # Extract ID and gender fields
                return df.withColumn("patient_id", F.col("resource.id")) \
                         .withColumn("gender", F.col("resource.gender")) \
                         .drop("resource", "resourceType")
        
        # Sample data
        data = [
            {"resourceType": "Patient", "resource": {"id": "p1", "gender": "male"}},
            {"resourceType": "Patient", "resource": {"id": "p2", "gender": "female"}}
        ]
        df = spark.createDataFrame(data)
        
        # Apply transformer
        transformer = SimplePatientTransformer()
        result_df = transformer.transform(df)
        
        # Verify results
        results = result_df.collect()
        assert len(results) == 2
        assert results[0]["patient_id"] == "p1"
        assert results[0]["gender"] == "male"
        assert results[1]["patient_id"] == "p2"
        assert results[1]["gender"] == "female"
        
        # Verify schema
        assert "patient_id" in result_df.columns
        assert "gender" in result_df.columns
        assert "resource" not in result_df.columns
    
    def test_transformation_with_path_extraction(self, spark):
        """Test transformation using path extraction."""
        # Create a transformer that uses PathExtractor
        class ObservationTransformer(FHIRTransformer):
            def transform(self, df):
                return df.withColumn("observation_id", PathExtractor.path_str(df, "resource.id")) \
                         .withColumn("code", PathExtractor.path_str(df, "resource.code.coding[0].code")) \
                         .withColumn("value", PathExtractor.path_float(df, "resource.valueQuantity.value")) \
                         .withColumn("unit", PathExtractor.path_str(df, "resource.valueQuantity.unit")) \
                         .drop("resource", "resourceType")
        
        # Sample data
        data = [
            {"resourceType": "Observation", "resource": {
                "id": "obs1",
                "code": {"coding": [{"code": "8302-2", "display": "Height"}]},
                "valueQuantity": {"value": 180.5, "unit": "cm"}
            }}
        ]
        df = spark.createDataFrame(data)
        
        # Apply transformer
        transformer = ObservationTransformer()
        result_df = transformer.transform(df)
        
        # Verify results
        results = result_df.collect()
        assert results[0]["observation_id"] == "obs1"
        assert results[0]["code"] == "8302-2"
        assert results[0]["value"] == 180.5
        assert results[0]["unit"] == "cm"
    
    def test_path_extractor_functions(self, spark):
        """Test different path extractor functions."""
        # Create sample data
        data = [
            {"resource": {
                "id": "test1",
                "active": True,
                "multipleBirthInteger": 2,
                "deceasedDateTime": "2023-01-01T00:00:00Z",
                "multipleBirthBoolean": True,
                "contact": [
                    {"relationship": [{"text": "parent"}]},
                    {"relationship": [{"text": "guardian"}]}
                ]
            }}
        ]
        df = spark.createDataFrame(data)
        
        # Test different extraction methods
        result_df = df \
            .withColumn("id", PathExtractor.path_str(df, "resource.id")) \
            .withColumn("active", PathExtractor.path_bool(df, "resource.active")) \
            .withColumn("birth_count", PathExtractor.path_int(df, "resource.multipleBirthInteger")) \
            .withColumn("deceased", PathExtractor.path_timestamp(df, "resource.deceasedDateTime")) \
            .withColumn("multiple_birth", PathExtractor.path_bool(df, "resource.multipleBirthBoolean")) \
            .withColumn("contact_relationships", PathExtractor.path_array(df, "resource.contact[*].relationship[0].text"))
        
        # Verify results
        result = result_df.collect()[0]
        assert result["id"] == "test1"
        assert result["active"] is True
        assert result["birth_count"] == 2
        assert result["multiple_birth"] is True
        assert result["contact_relationships"] == ["parent", "guardian"]
    
    def test_null_handling(self, spark):
        """Test null handling in path extraction."""
        # Data with nulls and missing fields
        data = [
            {"resource": {"id": "test1", "gender": None}},
            {"resource": {"id": "test2"}}  # Missing gender field
        ]
        df = spark.createDataFrame(data)
        
        # Extract with path_str (should handle nulls and missing fields)
        result_df = df \
            .withColumn("id", PathExtractor.path_str(df, "resource.id")) \
            .withColumn("gender", PathExtractor.path_str(df, "resource.gender"))
        
        # Verify results
        results = result_df.collect()
        assert results[0]["id"] == "test1"
        assert results[0]["gender"] is None
        assert results[1]["id"] == "test2"
        assert results[1]["gender"] is None
