"""
Unit tests for the Pathling analytics service.

This module tests the PathlingService class functionality without requiring
an actual Pathling server by mocking the subprocess and network calls.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from epic_fhir_integration.analytics.pathling_service import PathlingService

class TestPathlingService:
    """Test the PathlingService class."""
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run to avoid actual system calls."""
        with mock.patch('subprocess.run') as mock_run:
            # Set up the mock to return a successful result
            mock_process = mock.MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = '{}'
            mock_process.stderr = ''
            mock_run.return_value = mock_process
            yield mock_run
    
    @pytest.fixture
    def service(self):
        """Create a PathlingService instance for testing."""
        with mock.patch('epic_fhir_integration.analytics.pathling_service.PathlingService._check_java_availability'):
            return PathlingService(base_url="http://test-server/fhir")
    
    def test_init(self):
        """Test initializing the PathlingService."""
        with mock.patch('epic_fhir_integration.analytics.pathling_service.PathlingService._check_java_availability'):
            service = PathlingService(base_url="http://test-server/fhir")
            assert service.base_url == "http://test-server/fhir"
            assert service.use_docker is False
            
            service = PathlingService(use_docker=True)
            assert service.use_docker is True
            assert service.server_running is False
    
    def test_check_java_availability(self):
        """Test the Java version checking functionality."""
        # Mock a successful Java 11 check
        with mock.patch('subprocess.run') as mock_run:
            mock_result = mock.MagicMock()
            mock_result.stderr = 'openjdk version "11.0.11" 2021-04-20\nOpenJDK Runtime Environment'
            mock_run.return_value = mock_result
            
            service = PathlingService()
            # No exception should be raised
            
        # Mock a Java 8 check which should raise an error
        with mock.patch('subprocess.run') as mock_run:
            mock_result = mock.MagicMock()
            mock_result.stderr = 'openjdk version "1.8.0_282" 2021-01-19\nOpenJDK Runtime Environment'
            mock_run.return_value = mock_result
            
            with pytest.raises(RuntimeError) as excinfo:
                service = PathlingService()
            assert "Java version 11+" in str(excinfo.value)
            
        # Mock a missing Java check
        with mock.patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("No java")
            
            with pytest.raises(RuntimeError) as excinfo:
                service = PathlingService()
            assert "Java not found" in str(excinfo.value)
    
    def test_start_server(self, mock_subprocess_run, service):
        """Test starting the Pathling server."""
        # Non-Docker mode
        service.start_server()
        mock_subprocess_run.assert_not_called()
        
        # Docker mode
        service.use_docker = True
        
        # Create a temporary file to test docker-compose.yml creation
        compose_file = "docker-compose.yml"
        try:
            # Remove the file if it exists
            if os.path.exists(compose_file):
                os.unlink(compose_file)
                
            service.start_server(data_dir="test_data")
            
            # Check that docker-compose file was created
            assert os.path.exists(compose_file)
            
            # Check docker-compose up was called
            mock_subprocess_run.assert_called_once_with(
                ["docker-compose", "up", "-d"],
                check=True
            )
            
            # Check that the server is marked as running
            assert service.server_running is True
            assert service.base_url == "http://localhost:8080/fhir"
            
        finally:
            # Clean up
            if os.path.exists(compose_file):
                os.unlink(compose_file)
    
    def test_stop_server(self, mock_subprocess_run, service):
        """Test stopping the Pathling server."""
        # Non-Docker mode
        service.stop_server()
        mock_subprocess_run.assert_not_called()
        
        # Docker mode with server not running
        service.use_docker = True
        service.stop_server()
        mock_subprocess_run.assert_not_called()
        
        # Docker mode with server running
        service.server_running = True
        service.stop_server()
        
        # Check docker-compose down was called
        mock_subprocess_run.assert_called_once_with(
            ["docker-compose", "down"],
            check=True
        )
        
        # Check that the server is marked as stopped
        assert service.server_running is False
    
    def test_load_resources(self, mock_subprocess_run, service):
        """Test loading resources into Pathling."""
        # Create test resources
        resources = [
            {"resourceType": "Patient", "id": "1", "name": [{"family": "Smith"}]},
            {"resourceType": "Patient", "id": "2", "name": [{"family": "Jones"}]}
        ]
        
        # Configure mock to return success
        mock_subprocess_run.return_value.returncode = 0
        
        # Load resources
        result = service.load_resources(resources, "Patient")
        
        # Verify curl command was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "curl"
        assert args[1] == "-X"
        assert args[2] == "POST"
        assert "Patient/$import" in args[3]
        
        # Verify result
        assert result is True
        
        # Test failure case
        mock_subprocess_run.reset_mock()
        mock_subprocess_run.return_value.returncode = 1
        
        result = service.load_resources(resources, "Patient")
        assert result is False
    
    @mock.patch('json.loads')
    def test_aggregate(self, mock_json_loads, mock_subprocess_run, service):
        """Test the aggregate method."""
        # Configure mock response
        mock_response = {
            "parameter": {
                "group": [
                    {
                        "code": [{"code": "gender", "value": "male"}],
                        "result": [{"name": "count", "value": 10}]
                    },
                    {
                        "code": [{"code": "gender", "value": "female"}],
                        "result": [{"name": "count", "value": 15}]
                    }
                ]
            }
        }
        mock_json_loads.return_value = mock_response
        mock_subprocess_run.return_value.stdout = json.dumps(mock_response)
        
        # Execute aggregation
        result = service.aggregate(
            resource_type="Patient",
            aggregations=["count()"],
            grouping=["gender"]
        )
        
        # Verify curl command was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "curl"
        assert "-X" in args
        assert "GET" in args
        assert "Patient/$aggregate" in args[3]
        
        # Verify DataFrame result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        
        # Test with no grouping
        mock_json_loads.reset_mock()
        mock_subprocess_run.reset_mock()
        
        mock_response = {
            "parameter": [
                {"name": "result", "part": [{"name": "count", "valueDecimal": 25}]}
            ]
        }
        mock_json_loads.return_value = mock_response
        mock_subprocess_run.return_value.stdout = json.dumps(mock_response)
        
        result = service.aggregate(
            resource_type="Patient",
            aggregations=["count()"]
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
    
    @mock.patch('json.loads')
    def test_extract_dataset(self, mock_json_loads, mock_subprocess_run, service):
        """Test the extract_dataset method."""
        # Configure mock response
        mock_response = {
            "entry": [
                {
                    "resource": {
                        "parameter": [
                            {"name": "id", "value": "1"},
                            {"name": "name", "value": "Smith"}
                        ]
                    }
                },
                {
                    "resource": {
                        "parameter": [
                            {"name": "id", "value": "2"},
                            {"name": "name", "value": "Jones"}
                        ]
                    }
                }
            ]
        }
        mock_json_loads.return_value = mock_response
        mock_subprocess_run.return_value.stdout = json.dumps(mock_response)
        
        # Execute extraction
        result = service.extract_dataset(
            resource_type="Patient",
            columns=["id", "name.where(use = 'official').family"]
        )
        
        # Verify curl command was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "curl"
        assert "-X" in args
        assert "GET" in args
        assert "Patient/$extract" in args[3]
        
        # Verify DataFrame result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        
        # Test with empty response
        mock_json_loads.reset_mock()
        mock_subprocess_run.reset_mock()
        
        mock_response = {}
        mock_json_loads.return_value = mock_response
        mock_subprocess_run.return_value.stdout = json.dumps(mock_response)
        
        result = service.extract_dataset(
            resource_type="Patient",
            columns=["id"]
        )
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    @mock.patch('json.loads')
    def test_execute_measure(self, mock_json_loads, mock_subprocess_run, service, tmp_path):
        """Test the execute_measure method."""
        # Create a temporary measure file
        measure_file = tmp_path / "measure.json"
        measure_file.write_text('{"resourceType": "Measure", "id": "test-measure"}')
        
        # Configure mock response
        mock_response = {
            "resourceType": "MeasureReport",
            "status": "complete",
            "measure": "test-measure",
            "group": [
                {
                    "population": [
                        {"code": {"coding": [{"code": "initial-population"}]}, "count": 100}
                    ]
                }
            ]
        }
        mock_json_loads.return_value = mock_response
        mock_subprocess_run.return_value.stdout = json.dumps(mock_response)
        
        # Execute measure
        result = service.execute_measure(str(measure_file))
        
        # Verify curl command was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args[0] == "curl"
        assert "-X" in args
        assert "POST" in args
        assert "Measure/$evaluate-measure" in args[3]
        
        # Verify result
        assert result == mock_response
        
        # Test with non-existent file
        mock_subprocess_run.reset_mock()
        
        result = service.execute_measure(str(tmp_path / "non-existent.json"))
        
        # Verify no curl call was made
        mock_subprocess_run.assert_not_called()
        assert result == {}
    
    @mock.patch('json.loads')
    def test_batch_process(self, mock_json_loads, mock_subprocess_run, service):
        """Test the batch_process method."""
        # Configure mock responses for two batch calls
        batch1_response = {
            "entry": [
                {"resource": {"id": "1", "resourceType": "Patient"}},
                {"resource": {"id": "2", "resourceType": "Patient"}}
            ],
            "link": [
                {"relation": "next", "url": "http://test-server/fhir/Patient?_count=1000&page=2"}
            ]
        }
        batch2_response = {
            "entry": [
                {"resource": {"id": "3", "resourceType": "Patient"}}
            ]
        }
        
        # Use side_effect to return different responses for each call
        mock_json_loads.side_effect = [batch1_response, batch2_response]
        mock_subprocess_run.return_value.stdout = 'dummy'  # Will be overridden by json.loads mock
        
        # Create a processing function
        def process_func(resources):
            return len(resources)
        
        # Execute batch processing
        result = service.batch_process("Patient", process_func, chunk_size=1000)
        
        # Verify curl commands were called twice
        assert mock_subprocess_run.call_count == 2
        
        # Verify the first call used the initial URL
        first_args = mock_subprocess_run.call_args_list[0][0][0]
        assert "Patient?_count=1000" in first_args[3]
        
        # Verify the second call used the next URL
        second_args = mock_subprocess_run.call_args_list[1][0][0]
        assert "Patient?_count=1000&page=2" in second_args[3]
        
        # Verify result contains counts from both batches
        assert result == [2, 1] 