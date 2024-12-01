"""
Tests for the validation metrics module.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from epic_fhir_integration.metrics.validation_metrics import (
    ValidationMetricsRecorder,
    ValidationReporter,
    ValidationSeverity,
    ValidationCategory,
    ValidationType
)


class TestValidationMetricsRecorder(unittest.TestCase):
    """Tests for the ValidationMetricsRecorder class."""

    def setUp(self):
        """Set up test resources."""
        self.mock_metrics_collector = MagicMock()
        self.recorder = ValidationMetricsRecorder(self.mock_metrics_collector)
        
        # Sample validation issues
        self.issues = [
            {
                "severity": "error",
                "category": "structure",
                "message": "Missing required field"
            },
            {
                "severity": "warning",
                "category": "value",
                "message": "Value out of expected range"
            }
        ]

    def test_record_validation_result(self):
        """Test recording a validation result."""
        self.recorder.record_validation_result(
            resource_type="Patient",
            is_valid=False,
            validation_type=ValidationType.SCHEMA,
            pipeline_stage="bronze",
            issues=self.issues
        )
        
        # Verify metrics collector was called with expected arguments
        self.mock_metrics_collector.record_metric.assert_any_call(
            "validation.Patient.schema.valid",
            0.0,
            {
                "pipeline_stage": "bronze",
                "resource_type": "Patient",
                "validation_type": "schema"
            }
        )
        
        self.mock_metrics_collector.record_metric.assert_any_call(
            "validation.Patient.schema.issue_count",
            2,
            {
                "pipeline_stage": "bronze",
                "resource_type": "Patient",
                "validation_type": "schema"
            }
        )
        
        # Verify severity metrics were recorded
        self.mock_metrics_collector.record_metric.assert_any_call(
            "validation.Patient.schema.error_count",
            1,
            {
                "pipeline_stage": "bronze",
                "resource_type": "Patient",
                "validation_type": "schema",
                "severity": "error"
            }
        )
        
        self.mock_metrics_collector.record_metric.assert_any_call(
            "validation.Patient.schema.warning_count",
            1,
            {
                "pipeline_stage": "bronze",
                "resource_type": "Patient",
                "validation_type": "schema",
                "severity": "warning"
            }
        )

    def test_record_batch_validation_results(self):
        """Test recording batch validation results."""
        # Sample validation results
        results = [
            {
                "resource_type": "Patient",
                "is_valid": True,
                "issues": []
            },
            {
                "resource_type": "Patient",
                "is_valid": False,
                "issues": self.issues
            },
            {
                "resource_type": "Observation",
                "is_valid": True,
                "issues": []
            }
        ]
        
        summary = self.recorder.record_batch_validation_results(
            results=results,
            validation_type=ValidationType.PROFILE,
            pipeline_stage="silver"
        )
        
        # Verify summary statistics
        self.assertEqual(summary["resources_total"], 3)
        self.assertEqual(summary["resources_valid"], 2)
        self.assertAlmostEqual(summary["validation_rate"], 2/3)
        self.assertEqual(summary["total_issues"], 2)
        
        # Verify by resource type statistics
        self.assertIn("Patient", summary["by_resource_type"])
        self.assertIn("Observation", summary["by_resource_type"])
        
        patient_stats = summary["by_resource_type"]["Patient"]
        self.assertEqual(patient_stats["resources_total"], 2)
        self.assertEqual(patient_stats["resources_valid"], 1)
        self.assertEqual(patient_stats["issue_count"], 2)
        
        # Verify batch metrics were recorded
        self.mock_metrics_collector.record_metric.assert_any_call(
            "validation.batch.profile.validation_rate",
            2/3,
            {
                "pipeline_stage": "silver",
                "validation_type": "profile",
                "resource_count": 3
            }
        )

    def test_count_issues_by_severity(self):
        """Test counting issues by severity."""
        counts = self.recorder._count_issues_by_severity(self.issues)
        
        self.assertEqual(counts[ValidationSeverity.ERROR.value], 1)
        self.assertEqual(counts[ValidationSeverity.WARNING.value], 1)
        self.assertEqual(counts[ValidationSeverity.INFORMATION.value], 0)
        
        # Test with fatal severity (should map to error)
        fatal_issue = {
            "severity": "fatal",
            "message": "Fatal error"
        }
        
        counts = self.recorder._count_issues_by_severity([fatal_issue])
        self.assertEqual(counts[ValidationSeverity.ERROR.value], 1)
        
        # Test with unknown severity (should map to warning)
        unknown_issue = {
            "severity": "unknown",
            "message": "Unknown severity"
        }
        
        counts = self.recorder._count_issues_by_severity([unknown_issue])
        self.assertEqual(counts[ValidationSeverity.WARNING.value], 1)

    def test_count_issues_by_category(self):
        """Test counting issues by category."""
        counts = self.recorder._count_issues_by_category(self.issues)
        
        self.assertEqual(counts[ValidationCategory.STRUCTURE.value], 1)
        self.assertEqual(counts[ValidationCategory.VALUE.value], 1)
        
        # Test with explicit category
        explicit_issue = {
            "category": "reference",
            "message": "Reference issue"
        }
        
        counts = self.recorder._count_issues_by_category([explicit_issue])
        self.assertEqual(counts[ValidationCategory.REFERENCE.value], 1)

    def test_categorize_issue(self):
        """Test categorizing issues by message pattern."""
        # Test structure issues
        structure_issue = {
            "message": "Missing required property"
        }
        
        category = self.recorder._categorize_issue(structure_issue)
        self.assertEqual(category, ValidationCategory.STRUCTURE.value)
        
        # Test reference issues
        reference_issue = {
            "message": "Unknown target reference"
        }
        
        category = self.recorder._categorize_issue(reference_issue)
        self.assertEqual(category, ValidationCategory.REFERENCE.value)
        
        # Test profile issues
        profile_issue = {
            "message": "Resource does not conform to profile"
        }
        
        category = self.recorder._categorize_issue(profile_issue)
        self.assertEqual(category, ValidationCategory.PROFILE.value)
        
        # Test value issues
        value_issue = {
            "message": "Value is invalid"
        }
        
        category = self.recorder._categorize_issue(value_issue)
        self.assertEqual(category, ValidationCategory.VALUE.value)
        
        # Test constraint issues
        constraint_issue = {
            "message": "Invariant violated"
        }
        
        category = self.recorder._categorize_issue(constraint_issue)
        self.assertEqual(category, ValidationCategory.INVARIANT.value)
        
        # Test terminology issues
        terminology_issue = {
            "message": "Code not found in binding"
        }
        
        category = self.recorder._categorize_issue(terminology_issue)
        self.assertEqual(category, ValidationCategory.TERMINOLOGY.value)
        
        # Test security issues
        security_issue = {
            "message": "Access permission denied"
        }
        
        category = self.recorder._categorize_issue(security_issue)
        self.assertEqual(category, ValidationCategory.SECURITY.value)
        
        # Test unknown issues
        unknown_issue = {
            "message": "Some other issue"
        }
        
        category = self.recorder._categorize_issue(unknown_issue)
        self.assertEqual(category, ValidationCategory.UNKNOWN.value)


class TestValidationReporter(unittest.TestCase):
    """Tests for the ValidationReporter class."""

    def setUp(self):
        """Set up test resources."""
        self.mock_metrics_collector = MagicMock()
        
        # Sample metrics for querying
        self.valid_metrics = [
            {
                "name": "validation.Patient.schema.valid",
                "value": 1.0,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Patient",
                    "validation_type": "schema",
                    "pipeline_stage": "bronze"
                }
            },
            {
                "name": "validation.Patient.schema.valid",
                "value": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Patient",
                    "validation_type": "schema",
                    "pipeline_stage": "bronze"
                }
            },
            {
                "name": "validation.Observation.profile.valid",
                "value": 1.0,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Observation",
                    "validation_type": "profile",
                    "pipeline_stage": "silver"
                }
            }
        ]
        
        self.issue_metrics = [
            {
                "name": "validation.Patient.schema.issue_count",
                "value": 2,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Patient",
                    "validation_type": "schema",
                    "pipeline_stage": "bronze"
                }
            },
            {
                "name": "validation.Patient.schema.issue_count",
                "value": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Patient",
                    "validation_type": "schema",
                    "pipeline_stage": "bronze"
                }
            },
            {
                "name": "validation.Observation.profile.issue_count",
                "value": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "labels": {
                    "resource_type": "Observation",
                    "validation_type": "profile",
                    "pipeline_stage": "silver"
                }
            }
        ]
        
        # Mock query_metrics to return our sample metrics
        self.mock_metrics_collector.query_metrics = MagicMock(side_effect=lambda metric_pattern, **kwargs: {
            "validation.*.*.valid": self.valid_metrics,
            "validation.*.*.issue_count": self.issue_metrics
        }.get(metric_pattern, []))
        
        self.reporter = ValidationReporter(self.mock_metrics_collector)

    def test_generate_validation_summary(self):
        """Test generating a validation summary report."""
        summary = self.reporter.generate_validation_summary()
        
        # Verify summary structure
        self.assertIn("overall", summary)
        self.assertIn("by_resource_type", summary)
        self.assertIn("by_validation_type", summary)
        self.assertIn("by_pipeline_stage", summary)
        self.assertIn("detailed", summary)
        self.assertIn("generated_at", summary)
        self.assertIn("query_parameters", summary)
        
        # Verify overall statistics
        self.assertEqual(summary["overall"]["total_validations"], 3)
        self.assertEqual(summary["overall"]["valid_count"], 2)
        self.assertAlmostEqual(summary["overall"]["validation_rate"], 2/3)
        self.assertEqual(summary["overall"]["total_issues"], 3)
        
        # Verify resource type statistics
        self.assertIn("Patient", summary["by_resource_type"])
        self.assertIn("Observation", summary["by_resource_type"])
        
        patient_stats = summary["by_resource_type"]["Patient"]
        self.assertEqual(patient_stats["total_validations"], 2)
        self.assertEqual(patient_stats["valid_count"], 1)
        self.assertAlmostEqual(patient_stats["validation_rate"], 0.5)
        
        # Verify validation type statistics
        self.assertIn("schema", summary["by_validation_type"])
        self.assertIn("profile", summary["by_validation_type"])
        
        # Verify pipeline stage statistics
        self.assertIn("bronze", summary["by_pipeline_stage"])
        self.assertIn("silver", summary["by_pipeline_stage"])
        
        # Verify detailed statistics
        self.assertIn("Patient.schema.bronze", summary["detailed"])
        self.assertIn("Observation.profile.silver", summary["detailed"])
        
        # Test with filters
        resource_types = ["Patient"]
        validation_types = [ValidationType.SCHEMA]
        pipeline_stages = ["bronze"]
        
        filtered_summary = self.reporter.generate_validation_summary(
            resource_types=resource_types,
            validation_types=validation_types,
            pipeline_stages=pipeline_stages
        )
        
        # Verify filter was applied
        self.mock_metrics_collector.query_metrics.assert_any_call(
            metric_pattern="validation.*.*.valid",
            filter_dict={
                "resource_type": resource_types,
                "validation_type": validation_types,
                "pipeline_stage": pipeline_stages
            },
            time_range=None
        )
        
        # Verify query parameters in report
        self.assertEqual(
            filtered_summary["query_parameters"]["resource_types"],
            resource_types
        )
        self.assertEqual(
            filtered_summary["query_parameters"]["validation_types"],
            validation_types
        )
        self.assertEqual(
            filtered_summary["query_parameters"]["pipeline_stages"],
            pipeline_stages
        )

    def test_process_validation_metrics(self):
        """Test processing validation metrics into a summary."""
        summary = self.reporter._process_validation_metrics(
            self.valid_metrics,
            self.issue_metrics
        )
        
        # Verify overall statistics
        self.assertEqual(summary["overall"]["total_validations"], 3)
        self.assertEqual(summary["overall"]["valid_count"], 2)
        self.assertAlmostEqual(summary["overall"]["validation_rate"], 2/3)
        self.assertEqual(summary["overall"]["total_issues"], 3)
        
        # Verify detailed statistics for Patient.schema.bronze
        detailed_key = "Patient.schema.bronze"
        self.assertIn(detailed_key, summary["detailed"])
        
        patient_schema_stats = summary["detailed"][detailed_key]
        self.assertEqual(patient_schema_stats["total_validations"], 2)
        self.assertEqual(patient_schema_stats["valid_count"], 1)
        self.assertAlmostEqual(patient_schema_stats["validation_rate"], 0.5)
        self.assertEqual(patient_schema_stats["total_issues"], 2)
        self.assertEqual(patient_schema_stats["issues_per_validation"], 1.0)
        
        # Verify detailed statistics for Observation.profile.silver
        detailed_key = "Observation.profile.silver"
        self.assertIn(detailed_key, summary["detailed"])
        
        observation_profile_stats = summary["detailed"][detailed_key]
        self.assertEqual(observation_profile_stats["total_validations"], 1)
        self.assertEqual(observation_profile_stats["valid_count"], 1)
        self.assertEqual(observation_profile_stats["validation_rate"], 1.0)
        self.assertEqual(observation_profile_stats["total_issues"], 1)
        self.assertEqual(observation_profile_stats["issues_per_validation"], 1.0)


if __name__ == "__main__":
    unittest.main() 