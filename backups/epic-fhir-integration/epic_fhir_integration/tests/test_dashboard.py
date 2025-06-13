"""
Tests for dashboard components.

This module contains tests for the quality and validation dashboard components.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from epic_fhir_integration.metrics.dashboard.quality_dashboard import QualityDashboardGenerator
from epic_fhir_integration.metrics.dashboard.validation_dashboard import ValidationDashboard
from epic_fhir_integration.metrics.data_quality import DataQualityAssessor


@pytest.fixture
def sample_quality_report():
    """Sample quality report data."""
    return {
        "report_id": "test-report-123",
        "timestamp": datetime.now().isoformat(),
        "overall_score": 0.85,
        "dimension_scores": {
            "completeness": 0.9,
            "conformance": 0.8,
            "consistency": 0.85,
            "timeliness": 0.75
        },
        "resource_scores": {
            "Patient": {
                "completeness": 0.92,
                "conformance": 0.88,
                "consistency": 0.9
            },
            "Observation": {
                "completeness": 0.85,
                "conformance": 0.75,
                "consistency": 0.8
            }
        },
        "quality_issues": [
            {
                "category": "Missing Data",
                "severity": "medium",
                "description": "Patient resources missing address information",
                "affected_count": 12,
                "total_count": 100
            },
            {
                "category": "Terminology",
                "severity": "high",
                "description": "Non-standard codes in Observation resources",
                "affected_count": 25,
                "total_count": 150
            }
        ]
    }


@pytest.fixture
def sample_validation_results():
    """Sample validation results data."""
    return {
        "results": [
            {
                "resourceType": "Patient",
                "id": "patient-001",
                "valid": True,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
                "issues": []
            },
            {
                "resourceType": "Patient",
                "id": "patient-002",
                "valid": False,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
                "issues": [
                    {
                        "severity": "error",
                        "type": "required",
                        "message": "Patient.name: minimum required = 1, but only found 0",
                        "location": ["Patient.name"]
                    }
                ]
            },
            {
                "resourceType": "Observation",
                "id": "obs-001",
                "valid": True,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"],
                "issues": []
            },
            {
                "resourceType": "Observation",
                "id": "obs-002",
                "valid": False,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"],
                "issues": [
                    {
                        "severity": "warning",
                        "type": "value",
                        "message": "Observation.value[x]: None of the types are valid",
                        "location": ["Observation.value[x]"]
                    },
                    {
                        "severity": "information",
                        "type": "informational",
                        "message": "Observation.code: A code with this value should come from..."
                    }
                ]
            }
        ],
        "profiles": {
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient": {
                "total": 2,
                "conformant": 1
            },
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab": {
                "total": 2,
                "conformant": 1
            }
        }
    }


@pytest.fixture
def mock_quality_assessor():
    """Mock DataQualityAssessor with sample data."""
    mock = MagicMock(spec=DataQualityAssessor)
    mock.report_id = "test-report-123"
    mock.last_assessment_time = datetime.now()
    mock.get_overall_score.return_value = 0.85
    mock.get_dimension_scores.return_value = {
        "completeness": 0.9,
        "conformance": 0.8,
        "consistency": 0.85,
        "timeliness": 0.75
    }
    mock.get_resource_scores.return_value = {
        "Patient": {
            "completeness": 0.92,
            "conformance": 0.88,
            "consistency": 0.9
        },
        "Observation": {
            "completeness": 0.85,
            "conformance": 0.75,
            "consistency": 0.8
        }
    }
    mock.get_quality_issues.return_value = [
        {
            "category": "Missing Data",
            "severity": "medium",
            "description": "Patient resources missing address information",
            "affected_count": 12,
            "total_count": 100
        },
        {
            "category": "Terminology",
            "severity": "high",
            "description": "Non-standard codes in Observation resources",
            "affected_count": 25,
            "total_count": 150
        }
    ]
    return mock


def test_quality_dashboard_init():
    """Test QualityDashboardGenerator initialization."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dashboard = QualityDashboardGenerator(output_dir=tmp_dir, title="Test Dashboard")
        assert dashboard.title == "Test Dashboard"
        assert dashboard.output_dir == Path(tmp_dir)
        assert dashboard.port == 8050  # Default port
        assert not dashboard.debug  # Default debug setting
        assert not dashboard.quality_data  # Empty initial data
        assert not dashboard.validation_data  # Empty initial data
        assert not dashboard.trends_data  # Empty initial data
        assert dashboard.app is None  # No app created yet


def test_quality_dashboard_load_quality_report(sample_quality_report):
    """Test loading a quality report from a file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a test report file
        report_path = Path(tmp_dir) / "report.json"
        with open(report_path, "w") as f:
            json.dump(sample_quality_report, f)
        
        # Load the report
        dashboard = QualityDashboardGenerator(output_dir=tmp_dir)
        dashboard.load_quality_report(report_path)
        
        # Check the data was loaded correctly
        assert dashboard.quality_data["report_id"] == sample_quality_report["report_id"]
        assert dashboard.quality_data["overall_score"] == sample_quality_report["overall_score"]
        assert dashboard.quality_data["dimension_scores"] == sample_quality_report["dimension_scores"]
        assert dashboard.quality_data["resource_scores"] == sample_quality_report["resource_scores"]
        assert dashboard.quality_data["issues"] == sample_quality_report["quality_issues"]


def test_quality_dashboard_create_dashboard(sample_quality_report):
    """Test creating a dashboard app."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize dashboard with data
        dashboard = QualityDashboardGenerator(output_dir=tmp_dir)
        dashboard.quality_data = {
            "report_id": sample_quality_report["report_id"],
            "timestamp": sample_quality_report["timestamp"],
            "overall_score": sample_quality_report["overall_score"],
            "dimension_scores": sample_quality_report["dimension_scores"],
            "resource_scores": sample_quality_report["resource_scores"],
            "issues": sample_quality_report["quality_issues"]
        }
        
        # Create dashboard app
        app = dashboard.create_dashboard()
        
        # Check app was created successfully
        assert app is not None
        assert dashboard.app is not None
        assert app.title == dashboard.title


def test_quality_dashboard_from_quality_assessor(mock_quality_assessor):
    """Test creating a dashboard from a DataQualityAssessor."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create dashboard from assessor
        dashboard = QualityDashboardGenerator.from_quality_assessor(
            assessor=mock_quality_assessor,
            output_dir=tmp_dir,
            title="Assessor Dashboard"
        )
        
        # Check data was loaded correctly
        assert dashboard.quality_data["report_id"] == mock_quality_assessor.report_id
        assert dashboard.quality_data["overall_score"] == mock_quality_assessor.get_overall_score()
        assert dashboard.quality_data["dimension_scores"] == mock_quality_assessor.get_dimension_scores()
        assert dashboard.quality_data["resource_scores"] == mock_quality_assessor.get_resource_scores()
        assert dashboard.quality_data["issues"] == mock_quality_assessor.get_quality_issues()


def test_quality_dashboard_generate_static_dashboard(sample_quality_report):
    """Test generating a static dashboard file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize dashboard with data
        dashboard = QualityDashboardGenerator(output_dir=tmp_dir)
        dashboard.quality_data = {
            "report_id": sample_quality_report["report_id"],
            "timestamp": sample_quality_report["timestamp"],
            "overall_score": sample_quality_report["overall_score"],
            "dimension_scores": sample_quality_report["dimension_scores"],
            "resource_scores": sample_quality_report["resource_scores"],
            "issues": sample_quality_report["quality_issues"]
        }
        
        # Mock dashboard app for testing
        dashboard.app = MagicMock()
        dashboard.app.index_string = "<div>Mock Dashboard</div>"
        
        # Generate static dashboard
        output_file = dashboard.generate_static_dashboard()
        
        # Check file was created
        assert output_file.exists()
        assert output_file.is_file()
        
        # Check content
        with open(output_file, "r") as f:
            content = f.read()
            assert "<div>Mock Dashboard</div>" in content
            assert dashboard.title in content


def test_validation_dashboard_init():
    """Test ValidationDashboard initialization."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dashboard = ValidationDashboard(output_dir=tmp_dir, title="Test Validation Dashboard")
        assert dashboard.title == "Test Validation Dashboard"
        assert dashboard.output_dir == Path(tmp_dir)
        assert dashboard.port == 8051  # Default port
        assert not dashboard.debug  # Default debug setting
        assert not dashboard.validation_data  # Empty initial data
        assert not dashboard.profile_data  # Empty initial data
        assert dashboard.app is None  # No app created yet


def test_validation_dashboard_load_validation_results(sample_validation_results):
    """Test loading validation results from a file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a test validation results file
        results_path = Path(tmp_dir) / "validation_results.json"
        with open(results_path, "w") as f:
            json.dump(sample_validation_results, f)
        
        # Load the results
        dashboard = ValidationDashboard(output_dir=tmp_dir)
        dashboard.load_validation_results(results_path)
        
        # Check the data was loaded correctly
        assert len(dashboard.validation_data) == len(sample_validation_results["results"])
        assert dashboard.profile_data == sample_validation_results["profiles"]


def test_validation_dashboard_create_dashboard(sample_validation_results):
    """Test creating a validation dashboard app."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize dashboard with data
        dashboard = ValidationDashboard(output_dir=tmp_dir)
        dashboard.validation_data = sample_validation_results["results"]
        dashboard.profile_data = sample_validation_results["profiles"]
        
        # Create dashboard app
        app = dashboard.create_dashboard()
        
        # Check app was created successfully
        assert app is not None
        assert dashboard.app is not None
        assert app.title == dashboard.title


def test_validation_dashboard_from_validation_results(sample_validation_results):
    """Test creating a dashboard from validation results file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a test validation results file
        results_path = Path(tmp_dir) / "validation_results.json"
        with open(results_path, "w") as f:
            json.dump(sample_validation_results, f)
        
        # Create dashboard from results
        dashboard = ValidationDashboard.from_validation_results(
            results_path=results_path,
            output_dir=tmp_dir,
            title="Validation Results Dashboard"
        )
        
        # Check data was loaded correctly
        assert len(dashboard.validation_data) == len(sample_validation_results["results"])
        assert dashboard.profile_data == sample_validation_results["profiles"]


def test_validation_dashboard_generate_static_dashboard(sample_validation_results):
    """Test generating a static validation dashboard file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize dashboard with data
        dashboard = ValidationDashboard(output_dir=tmp_dir)
        dashboard.validation_data = sample_validation_results["results"]
        dashboard.profile_data = sample_validation_results["profiles"]
        
        # Mock dashboard app for testing
        dashboard.app = MagicMock()
        dashboard.app.index_string = "<div>Mock Validation Dashboard</div>"
        
        # Generate static dashboard
        output_file = dashboard.generate_static_dashboard()
        
        # Check file was created
        assert output_file.exists()
        assert output_file.is_file()
        
        # Check content
        with open(output_file, "r") as f:
            content = f.read()
            assert "<div>Mock Validation Dashboard</div>" in content
            assert dashboard.title in content 