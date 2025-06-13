"""
Integration tests for the FHIR extraction pipeline.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, ArrayType

from fhir_pipeline.pipelines.extract import FHIRExtractPipeline
from fhir_pipeline.io.fhir_client import FHIRClient
from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.auth.token_manager import TokenManager


class TestFHIRExtractPipeline:
    """Integration tests for the FHIR extraction pipeline."""

    @pytest.fixture(scope="class")
    def mock_fhir_client(self):
        """Create a mock FHIR client that returns test data."""
        with patch('fhir_pipeline.io.fhir_client.FHIRClient') as mock:
            client = MagicMock()
            mock.return_value = client
            
            # Mock patient bundle response
            patient_bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "patient1",
                            "identifier": [{"system": "urn:oid:1.2.36.146.595.217.0.1", "value": "12345"}],
                            "name": [{"family": "Smith", "given": ["John"]}],
                            "gender": "male",
                            "birthDate": "1970-01-01"
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "patient2",
                            "identifier": [{"system": "urn:oid:1.2.36.146.595.217.0.1", "value": "67890"}],
                            "name": [{"family": "Johnson", "given": ["Sarah"]}],
                            "gender": "female",
                            "birthDate": "1980-05-15"
                        }
                    }
                ]
            }
            
            # Mock observation bundle response
            observation_bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "id": "obs1",
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
                            "subject": {"reference": "Patient/patient1"},
                            "valueQuantity": {
                                "value": 80,
                                "unit": "beats/minute",
                                "system": "http://unitsofmeasure.org",
                                "code": "/min"
                            },
                            "effectiveDateTime": "2023-01-01T12:00:00Z"
                        }
                    }
                ]
            }
            
            # Mock the get_bundle method
            def mock_get_bundle(resource_type, **kwargs):
                if resource_type == "Patient":
                    return patient_bundle
                elif resource_type == "Observation":
                    return observation_bundle
                return {"resourceType": "Bundle", "entry": []}
                
            client.get_bundle.side_effect = mock_get_bundle
            yield client

    def test_extract_patients(self, spark, mock_fhir_client, temp_output_dir):
        """Test extracting patient data."""
        # Set up the extract pipeline
        pipeline = FHIRExtractPipeline(
            spark=spark,
            fhir_client=mock_fhir_client,
            output_dir=temp_output_dir
        )
        
        # Extract patient data
        patients_df = pipeline.extract_resource("Patient")
        
        # Verify the extracted data
        assert patients_df.count() == 2
        
        # Check for expected columns
        expected_cols = ["id", "identifier", "name", "gender", "birthDate", "resourceType"]
        for col in expected_cols:
            assert col in patients_df.columns
        
        # Verify specific patient data
        patient_rows = patients_df.collect()
        assert any(row.id == "patient1" and row.gender == "male" for row in patient_rows)
        assert any(row.id == "patient2" and row.gender == "female" for row in patient_rows)
        
        # Verify data is written to the output directory
        output_path = os.path.join(temp_output_dir, "Patient")
        assert os.path.exists(output_path)

    def test_extract_observations(self, spark, mock_fhir_client, temp_output_dir):
        """Test extracting observation data."""
        # Set up the extract pipeline
        pipeline = FHIRExtractPipeline(
            spark=spark,
            fhir_client=mock_fhir_client,
            output_dir=temp_output_dir
        )
        
        # Extract observation data
        observations_df = pipeline.extract_resource("Observation")
        
        # Verify the extracted data
        assert observations_df.count() == 1
        
        # Check for expected columns
        expected_cols = ["id", "status", "code", "subject", "valueQuantity", "effectiveDateTime", "resourceType"]
        for col in expected_cols:
            assert col in observations_df.columns
        
        # Verify specific observation data
        observation_rows = observations_df.collect()
        obs = observation_rows[0]
        assert obs.id == "obs1"
        assert obs.status == "final"
        assert obs.subject.reference == "Patient/patient1"
        
        # Verify data is written to the output directory
        output_path = os.path.join(temp_output_dir, "Observation")
        assert os.path.exists(output_path)

    def test_extract_multiple_resources(self, spark, mock_fhir_client, temp_output_dir):
        """Test extracting multiple resource types."""
        # Set up the extract pipeline
        pipeline = FHIRExtractPipeline(
            spark=spark,
            fhir_client=mock_fhir_client,
            output_dir=temp_output_dir
        )
        
        # Extract multiple resources
        result = pipeline.extract_resources(["Patient", "Observation"])
        
        # Verify the results
        assert "Patient" in result
        assert "Observation" in result
        assert result["Patient"].count() == 2
        assert result["Observation"].count() == 1
        
        # Verify data is written to the output directory
        assert os.path.exists(os.path.join(temp_output_dir, "Patient"))
        assert os.path.exists(os.path.join(temp_output_dir, "Observation"))

    @patch('fhir_pipeline.auth.jwt_client.JWTClient')
    def test_pipeline_with_jwt_auth(self, mock_jwt_client, spark, temp_output_dir):
        """Test extract pipeline with JWT authentication."""
        # Set up mock JWT client
        mock_client = MagicMock()
        mock_client.get_token.return_value = "mock-jwt-token"
        mock_jwt_client.return_value = mock_client
        
        # Mock FHIR client initialization
        with patch('fhir_pipeline.io.fhir_client.FHIRClient') as mock_fhir_client:
            fhir_client_instance = MagicMock()
            mock_fhir_client.return_value = fhir_client_instance
            
            # Set up mock bundle response
            fhir_client_instance.get_bundle.return_value = {
                "resourceType": "Bundle",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "test-patient"
                        }
                    }
                ]
            }
            
            # Create pipeline with JWT authentication
            pipeline = FHIRExtractPipeline(
                spark=spark,
                base_url="https://fhir.example.org",
                client_id="test-client",
                private_key="mock-private-key",
                output_dir=temp_output_dir
            )
            
            # Extract patient data
            patients_df = pipeline.extract_resource("Patient")
            
            # Verify JWT client was created with correct parameters
            mock_jwt_client.assert_called_once_with(
                client_id="test-client",
                private_key="mock-private-key"
            )
            
            # Verify FHIR client was created with correct parameters
            mock_fhir_client.assert_called_once()
            
            # Verify token was retrieved for authentication
            assert mock_client.get_token.called
            
            # Verify data was extracted
            assert patients_df.count() == 1 