import os
import sys
import pytest
from unittest.mock import patch, MagicMock

import yaml
from pyspark.sql import SparkSession

from fhir_pipeline.transforms.base import BaseTransformer
from fhir_pipeline.transforms.registry import get_transformer, GenericTransformer

# Create a fixture for SparkSession
@pytest.fixture(scope="module")
def spark():
    spark = SparkSession.builder \
        .appName("test-registry") \
        .master("local[2]") \
        .getOrCreate()
    yield spark
    spark.stop()

# Mock YAML mapping spec
@pytest.fixture
def mock_patient_mapping():
    return {
        "resourceType": "Patient",
        "version": 1,
        "columns": {
            "patient_id": "id",
            "name_text": "name[0].text"
        }
    }

# Test getting the generic transformer when no custom one exists
@patch("fhir_pipeline.transforms.registry._load_mapping_spec")
@patch("fhir_pipeline.transforms.registry._try_import_custom_transformer")
def test_get_generic_transformer(mock_import, mock_load_spec, spark, mock_patient_mapping):
    """Test retrieving a generic transformer when no custom one exists."""
    # Setup mocks
    mock_load_spec.return_value = mock_patient_mapping
    mock_import.return_value = None
    
    # Get transformer
    transformer = get_transformer(spark, "Patient")
    
    # Assertions
    assert isinstance(transformer, GenericTransformer)
    assert transformer.resource_type == "Patient"
    assert transformer.mapping_spec == mock_patient_mapping
    
    # Verify mocks were called correctly
    mock_load_spec.assert_called_once_with("Patient")
    mock_import.assert_called_once_with("Patient")

# Test getting a custom transformer when one exists
@patch("fhir_pipeline.transforms.registry._load_mapping_spec")
@patch("fhir_pipeline.transforms.registry._try_import_custom_transformer")
def test_get_custom_transformer(mock_import, mock_load_spec, spark, mock_patient_mapping):
    """Test retrieving a custom transformer when one exists."""
    # Create a mock custom transformer class
    class MockCustomTransformer(BaseTransformer):
        pass
    
    # Setup mocks
    mock_load_spec.return_value = mock_patient_mapping
    mock_import.return_value = MockCustomTransformer
    
    # Get transformer
    transformer = get_transformer(spark, "Patient")
    
    # Assertions
    assert isinstance(transformer, MockCustomTransformer)
    assert transformer.resource_type == "Patient"
    assert transformer.mapping_spec == mock_patient_mapping
    
    # Verify mocks were called correctly
    mock_load_spec.assert_called_once_with("Patient")
    mock_import.assert_called_once_with("Patient")

# Test error handling for unsupported resource types
@patch("fhir_pipeline.transforms.registry._load_mapping_spec")
def test_get_transformer_unsupported_resource(mock_load_spec, spark):
    """Test that an appropriate error is raised for unsupported resource types."""
    # Setup mock to raise FileNotFoundError
    mock_load_spec.side_effect = FileNotFoundError("No mapping file found")
    
    # Attempt to get transformer for unsupported resource
    with pytest.raises(ValueError) as exc_info:
        get_transformer(spark, "UnsupportedResourceType")
    
    # Verify error message
    assert "Unsupported resource type" in str(exc_info.value)
    assert "UnsupportedResourceType" in str(exc_info.value)
    
    # Verify mock was called correctly
    mock_load_spec.assert_called_once_with("UnsupportedResourceType")

# Test loading mapping spec
@patch("os.path.exists")
@patch("builtins.open")
@patch("yaml.safe_load")
def test_load_mapping_spec(mock_yaml_load, mock_open, mock_exists):
    """Test loading a mapping specification from YAML."""
    # Import the function directly for testing
    from fhir_pipeline.transforms.registry import _load_mapping_spec
    
    # Setup mocks
    mock_exists.return_value = True
    mock_yaml_load.return_value = {
        "resourceType": "Patient",
        "version": 1,
        "columns": {"patient_id": "id"}
    }
    
    # Call the function
    spec = _load_mapping_spec("Patient")
    
    # Verify result
    assert spec["resourceType"] == "Patient"
    assert "columns" in spec
    assert spec["columns"]["patient_id"] == "id"
    
    # Verify mocks were called correctly
    mock_exists.assert_called_once()
    mock_open.assert_called_once()
    mock_yaml_load.assert_called_once()

# Test GenericTransformer implementation
def test_generic_transformer_implementation(spark, mock_patient_mapping):
    """Test that GenericTransformer properly inherits and uses BaseTransformer functionality."""
    # Create a transformer instance
    transformer = GenericTransformer(spark, "Patient", mock_patient_mapping)
    
    # Create a mock DataFrame
    mock_df = MagicMock()
    mock_df.count.return_value = 10
    
    # Mock apply_mapping to return the input DataFrame
    with patch("fhir_pipeline.transforms.yaml_mappers.apply_mapping", return_value=mock_df):
        # Call transform
        result = transformer.transform(mock_df)
        
        # Verify result
        assert result == mock_df 