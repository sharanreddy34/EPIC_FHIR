"""
Tests for the Great Expectations validator module.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from great_expectations.core import ExpectationSuite
from great_expectations.dataset import PandasDataset

from epic_fhir_integration.metrics.great_expectations_validator import (
    GreatExpectationsValidator,
    create_patient_expectations,
    create_observation_expectations,
    create_medication_request_expectations
)


class TestGreatExpectationsValidator(unittest.TestCase):
    """Tests for the GreatExpectationsValidator class."""

    def setUp(self):
        """Set up test resources."""
        # Mock validation metrics recorder
        self.mock_validation_metrics_recorder = MagicMock()
        
        # Create a temporary directory for expectation suites
        self.temp_dir = "temp_expectation_suites"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Create validator
        with patch('great_expectations.data_context.DataContext') as mock_context:
            self.validator = GreatExpectationsValidator(
                validation_metrics_recorder=self.mock_validation_metrics_recorder,
                expectation_suite_dir=self.temp_dir
            )
        
        # Sample FHIR resources
        self.patient_resource = {
            "resourceType": "Patient",
            "id": "example",
            "name": [
                {
                    "use": "official",
                    "family": "Smith",
                    "given": ["John"]
                }
            ],
            "gender": "male",
            "birthDate": "1970-01-01"
        }
        
        self.invalid_patient = {
            "resourceType": "Patient",
            "id": "invalid",
            "gender": "invalid_gender"
        }
        
        self.observation_resource = {
            "resourceType": "Observation",
            "id": "example-bp",
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }
                ]
            },
            "subject": {
                "reference": "Patient/example"
            },
            "effectiveDateTime": "2020-01-01T12:00:00Z",
            "valueQuantity": {
                "value": 120,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            }
        }

    def tearDown(self):
        """Clean up test resources."""
        # Clean up temporary directory
        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    def test_create_expectation_suite(self):
        """Test creating an expectation suite."""
        # Create a new suite
        suite = self.validator.create_expectation_suite("test_suite")
        
        # Verify suite was created
        self.assertIsInstance(suite, ExpectationSuite)
        self.assertEqual(suite.expectation_suite_name, "test_suite")
        self.assertEqual(len(suite.expectations), 0)
        
        # Verify it was added to the validator's cache
        self.assertIn("test_suite", self.validator.expectation_suites)

    def test_add_expectation(self):
        """Test adding an expectation to a suite."""
        # Add an expectation
        result = self.validator.add_expectation(
            suite_name="test_suite_2",
            expectation_type="expect_column_to_exist",
            kwargs={"column": "resourceType"}
        )
        
        # Verify it was added successfully
        self.assertTrue(result)
        
        # Get the suite and verify the expectation was added
        suite = self.validator.get_expectation_suite("test_suite_2")
        self.assertIsInstance(suite, ExpectationSuite)
        self.assertEqual(len(suite.expectations), 1)
        self.assertEqual(suite.expectations[0].expectation_type, "expect_column_to_exist")
        self.assertEqual(suite.expectations[0].kwargs["column"], "resourceType")

    @patch('pandas.DataFrame')
    @patch('great_expectations.dataset.PandasDataset.validate')
    def test_validate_resource(self, mock_validate, mock_dataframe):
        """Test validating a FHIR resource."""
        # Set up mocks
        mock_validate.return_value = MagicMock(success=True, results=[])
        
        # Create patient expectations
        create_patient_expectations(self.validator, "patient")
        
        # Validate a valid patient
        result = self.validator.validate_resource(
            resource=self.patient_resource,
            expectation_suite_name="patient",
            pipeline_stage="bronze"
        )
        
        # Verify the result
        self.assertEqual(result["resource_type"], "Patient")
        self.assertEqual(result["resource_id"], "example")
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["validation_type"], "custom")
        self.assertEqual(len(result["issues"]), 0)
        
        # Validate with a suite that doesn't exist
        result = self.validator.validate_resource(
            resource=self.patient_resource,
            expectation_suite_name="nonexistent_suite",
            pipeline_stage="bronze"
        )
        
        # Verify error result
        self.assertFalse(result["is_valid"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertIn("not found", result["issues"][0]["message"])
        
        # Test with failed validation
        mock_validate.return_value = MagicMock(
            success=False,
            results=[
                MagicMock(
                    success=False,
                    expectation_config=MagicMock(
                        expectation_type="expect_column_values_to_be_in_set",
                        kwargs={"column": "gender", "value_set": ["male", "female", "other", "unknown"]}
                    ),
                    result={"observed_value": "invalid_gender"}
                )
            ]
        )
        
        # Validate an invalid patient
        result = self.validator.validate_resource(
            resource=self.invalid_patient,
            expectation_suite_name="patient",
            pipeline_stage="bronze"
        )
        
        # Verify result with issues
        self.assertFalse(result["is_valid"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["severity"], "error")
        self.assertEqual(result["issues"][0]["category"], "value")

    @patch('pandas.DataFrame')
    @patch('great_expectations.dataset.PandasDataset.validate')
    def test_validate_resources(self, mock_validate, mock_dataframe):
        """Test validating multiple FHIR resources."""
        # Set up mocks
        mock_validate.return_value = MagicMock(success=True, results=[])
        
        # Create patient expectations
        create_patient_expectations(self.validator, "patient")
        
        # Validate multiple resources
        resources = [self.patient_resource, self.patient_resource]
        result = self.validator.validate_resources(
            resources=resources,
            expectation_suite_name="patient",
            pipeline_stage="bronze"
        )
        
        # Verify the result
        self.assertEqual(result["resources_total"], 2)
        self.assertEqual(result["resources_valid"], 2)
        self.assertEqual(result["validation_rate"], 1.0)
        self.assertEqual(result["total_issues"], 0)

    def test_resource_to_dataframe(self):
        """Test converting a FHIR resource to a DataFrame."""
        # Convert a resource to a DataFrame
        df = self.validator._resource_to_dataframe(self.patient_resource)
        
        # Verify the DataFrame
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)  # One row
        self.assertIn("resourceType", df.columns)
        self.assertEqual(df["resourceType"].iloc[0], "Patient")

    def test_flatten_resource(self):
        """Test flattening a FHIR resource."""
        # Flatten a resource
        flattened = self.validator._flatten_resource(self.patient_resource)
        
        # Verify the flattened resource
        self.assertIsInstance(flattened, dict)
        self.assertIn("resourceType", flattened)
        self.assertIn("id", flattened)
        self.assertIn("name[0].family", flattened)
        self.assertIn("name[0].given[0]", flattened)
        self.assertIn("gender", flattened)
        self.assertIn("birthDate", flattened)

    def test_get_issue_category(self):
        """Test getting the category for a validation issue."""
        # Test structure category
        category = self.validator._get_issue_category("expect_column_to_exist")
        self.assertEqual(category, "structure")
        
        # Test value category
        category = self.validator._get_issue_category("expect_column_values_to_be_in_set")
        self.assertEqual(category, "value")
        
        # Test consistency category
        category = self.validator._get_issue_category("expect_column_pair_values_to_be_equal")
        self.assertEqual(category, "consistency")
        
        # Test unknown category
        category = self.validator._get_issue_category("unknown_expectation_type")
        self.assertEqual(category, "unknown")

    def test_create_patient_expectations(self):
        """Test creating patient expectations."""
        # Create patient expectations
        result = create_patient_expectations(self.validator, "test_patient")
        
        # Verify success
        self.assertTrue(result)
        
        # Verify expectations were created
        suite = self.validator.get_expectation_suite("test_patient")
        self.assertIsNotNone(suite)
        self.assertGreater(len(suite.expectations), 0)
        
        # Verify key expectations exist
        expectation_types = [exp.expectation_type for exp in suite.expectations]
        self.assertIn("expect_column_to_exist", expectation_types)
        self.assertIn("expect_column_values_to_be_in_set", expectation_types)

    def test_create_observation_expectations(self):
        """Test creating observation expectations."""
        # Create observation expectations
        result = create_observation_expectations(self.validator, "test_observation")
        
        # Verify success
        self.assertTrue(result)
        
        # Verify expectations were created
        suite = self.validator.get_expectation_suite("test_observation")
        self.assertIsNotNone(suite)
        self.assertGreater(len(suite.expectations), 0)

    def test_create_medication_request_expectations(self):
        """Test creating medication request expectations."""
        # Create medication request expectations
        result = create_medication_request_expectations(self.validator, "test_medication_request")
        
        # Verify success
        self.assertTrue(result)
        
        # Verify expectations were created
        suite = self.validator.get_expectation_suite("test_medication_request")
        self.assertIsNotNone(suite)
        self.assertGreater(len(suite.expectations), 0)

    def test_save_expectation_suite(self):
        """Test saving an expectation suite to a file."""
        # Create a suite with some expectations
        suite_name = "test_save_suite"
        self.validator.add_expectation(
            suite_name=suite_name,
            expectation_type="expect_column_to_exist",
            kwargs={"column": "resourceType"}
        )
        
        # Save the suite
        file_path = self.validator.save_expectation_suite(suite_name)
        
        # Verify the file was created
        self.assertIsNotNone(file_path)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify the file contents
        with open(file_path, "r") as f:
            data = json.load(f)
            self.assertIn("expectations", data)
            self.assertEqual(len(data["expectations"]), 1)
            self.assertEqual(data["expectations"][0]["expectation_type"], "expect_column_to_exist")


if __name__ == "__main__":
    unittest.main() 