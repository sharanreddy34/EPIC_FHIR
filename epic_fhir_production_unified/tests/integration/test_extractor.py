"""
Integration tests for the extractor module.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from epic_fhir_integration.extract.extractor import ResourceExtractor
from epic_fhir_integration.io.fhir_client import FHIRClient


class TestResourceExtractor:
    """Integration test suite for resource extractors using recorded fixtures."""
    
    @pytest.fixture
    def mock_patient_response(self):
        """Load mock patient response from fixture file."""
        fixture_path = Path(__file__).parent.parent / "data" / "mock_patient_response.json"
        with open(fixture_path, "r") as f:
            return json.load(f)
    
    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create temporary output directory."""
        bronze_dir = tmp_path / "bronze"
        bronze_dir.mkdir()
        return tmp_path
    
    @patch("epic_fhir_integration.io.fhir_client.create_fhir_client")
    def test_extract_patients(self, mock_create_client, mock_patient_response, output_dir):
        """Test extracting patient resources."""
        # Setup mock client
        mock_client = MagicMock(spec=FHIRClient)
        mock_client.search_resources.return_value = [
            mock_patient_response["entry"][0]["resource"]
        ]
        mock_create_client.return_value = mock_client
        
        # Create extractor
        extractor = ResourceExtractor(
            resource_type="Patient",
            output_dir=str(output_dir),
            params={"_count": 10}
        )
        
        # Run extraction
        result = extractor.extract()
        
        # Verify extraction result
        assert result["resource_type"] == "Patient"
        assert result["count"] == 1
        assert "output_file" in result
        
        # Verify output file exists and contains the expected data
        output_file = Path(result["output_file"])
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            extracted_data = json.load(f)
        
        assert extracted_data["resourceType"] == "Bundle"
        assert extracted_data["type"] == "collection"
        assert len(extracted_data["entry"]) == 1
        assert extracted_data["entry"][0]["resource"]["id"] == "123"
    
    @patch("epic_fhir_integration.io.fhir_client.create_fhir_client")
    def test_extract_empty_results(self, mock_create_client, output_dir):
        """Test extracting with no results."""
        # Setup mock client with empty results
        mock_client = MagicMock(spec=FHIRClient)
        mock_client.search_resources.return_value = []
        mock_create_client.return_value = mock_client
        
        # Create extractor
        extractor = ResourceExtractor(
            resource_type="Observation",
            output_dir=str(output_dir),
            params={"code": "nonexistent-code"}
        )
        
        # Run extraction
        result = extractor.extract()
        
        # Verify extraction result
        assert result["resource_type"] == "Observation"
        assert result["count"] == 0
        assert "output_file" in result
        
        # Verify output file exists with empty bundle
        output_file = Path(result["output_file"])
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            extracted_data = json.load(f)
        
        assert extracted_data["resourceType"] == "Bundle"
        assert extracted_data["type"] == "collection"
        assert len(extracted_data["entry"]) == 0
    
    @patch("epic_fhir_integration.io.fhir_client.create_fhir_client")
    def test_extract_with_pagination(self, mock_create_client, mock_patient_response, output_dir):
        """Test extracting resources with pagination."""
        # Create a second patient by modifying the first
        second_patient = json.loads(json.dumps(mock_patient_response["entry"][0]["resource"]))
        second_patient["id"] = "456"
        second_patient["name"][0]["family"] = "Doe"
        
        # Setup mock client with pagination
        mock_client = MagicMock(spec=FHIRClient)
        mock_client.search_resources.return_value = [
            mock_patient_response["entry"][0]["resource"],
            second_patient
        ]
        mock_create_client.return_value = mock_client
        
        # Create extractor with limit
        extractor = ResourceExtractor(
            resource_type="Patient",
            output_dir=str(output_dir),
            params={"_count": 10},
            limit=2
        )
        
        # Run extraction
        result = extractor.extract()
        
        # Verify extraction result
        assert result["resource_type"] == "Patient"
        assert result["count"] == 2
        
        # Verify output file content
        output_file = Path(result["output_file"])
        with open(output_file, "r") as f:
            extracted_data = json.load(f)
        
        assert len(extracted_data["entry"]) == 2
        assert extracted_data["entry"][0]["resource"]["id"] == "123"
        assert extracted_data["entry"][1]["resource"]["id"] == "456"
        
        # Verify limit was respected
        assert mock_client.search_resources.call_args[1]["total_limit"] == 2 