"""
Tests for the data quality module.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from epic_fhir_integration.metrics.data_quality import (
    DataQualityAssessor,
    DataQualityDimension
)


class TestDataQualityAssessor(unittest.TestCase):
    """Tests for the DataQualityAssessor class."""

    def setUp(self):
        """Set up test resources."""
        self.mock_metrics_collector = MagicMock()
        self.assessor = DataQualityAssessor(self.mock_metrics_collector)
        
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
        
        self.incomplete_patient = {
            "resourceType": "Patient",
            "id": "incomplete",
            "name": [
                {
                    "family": "Doe"
                }
            ]
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

    def test_assess_completeness(self):
        """Test assessing completeness of a resource."""
        # Test complete patient
        required_paths = [
            "name.given", 
            "gender", 
            "birthDate"
        ]
        
        result = self.assessor.assess_completeness(self.patient_resource, required_paths)
        
        self.assertEqual(result["completeness_score"], 1.0)
        self.assertEqual(len(result["missing_fields"]), 0)
        self.assertEqual(result["complete_field_count"], 3)
        self.assertEqual(result["total_required_fields"], 3)
        
        # Test incomplete patient
        result = self.assessor.assess_completeness(self.incomplete_patient, required_paths)
        
        self.assertLess(result["completeness_score"], 1.0)
        self.assertGreater(len(result["missing_fields"]), 0)
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()

    def test_assess_conformance(self):
        """Test assessing conformance of a resource."""
        # Mock validator function
        mock_validator = MagicMock(return_value={"valid": True, "issues": []})
        
        result = self.assessor.assess_conformance(self.patient_resource, mock_validator)
        
        self.assertTrue(result["conformance_valid"])
        self.assertEqual(len(result["issues"]), 0)
        
        # Test with invalid resource
        mock_validator.return_value = {
            "valid": False, 
            "issues": [{"message": "Test issue"}]
        }
        
        result = self.assessor.assess_conformance(self.incomplete_patient, mock_validator)
        
        self.assertFalse(result["conformance_valid"])
        self.assertEqual(len(result["issues"]), 1)
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()

    def test_assess_consistency(self):
        """Test assessing consistency of a resource."""
        # Define consistency rules
        consistency_rules = [
            {
                "name": "Gender is valid",
                "condition": "gender.matches('male|female|other|unknown')"
            },
            {
                "name": "Name has family",
                "condition": "name.exists() implies name.family.exists()"
            }
        ]
        
        # Test consistent resource
        result = self.assessor.assess_consistency(self.patient_resource, consistency_rules)
        
        self.assertEqual(result["consistency_score"], 1.0)
        self.assertEqual(len(result["failed_rules"]), 0)
        
        # Test inconsistent resource
        inconsistent_patient = {
            "resourceType": "Patient",
            "id": "inconsistent",
            "gender": "invalid",
            "name": [{}]
        }
        
        result = self.assessor.assess_consistency(inconsistent_patient, consistency_rules)
        
        self.assertLess(result["consistency_score"], 1.0)
        self.assertGreater(len(result["failed_rules"]), 0)
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()

    def test_assess_timeliness(self):
        """Test assessing timeliness of a resource."""
        # Get reference time
        now = datetime.utcnow()
        
        # Test with recent resource
        recent_time = now - timedelta(hours=1)
        recent_resource = {
            "resourceType": "Observation",
            "effectiveDateTime": recent_time.isoformat() + "Z"
        }
        
        result = self.assessor.assess_timeliness(
            recent_resource, 
            "effectiveDateTime", 
            reference_time=now
        )
        
        self.assertGreater(result["timeliness_score"], 0.9)
        
        # Test with old resource
        old_time = now - timedelta(days=30)
        old_resource = {
            "resourceType": "Observation",
            "effectiveDateTime": old_time.isoformat() + "Z"
        }
        
        result = self.assessor.assess_timeliness(
            old_resource, 
            "effectiveDateTime", 
            reference_time=now
        )
        
        self.assertLess(result["timeliness_score"], 0.5)
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()

    def test_assess_overall_quality(self):
        """Test assessing overall quality of a resource."""
        # Mock validator function
        mock_validator = MagicMock(return_value={"valid": True, "issues": []})
        
        # Define consistency rules
        consistency_rules = [
            {
                "name": "Has gender",
                "condition": "gender.exists()"
            }
        ]
        
        # Define required paths
        required_paths = ["name.given", "gender"]
        
        # Test with a complete resource
        result = self.assessor.assess_overall_quality(
            self.patient_resource,
            required_paths=required_paths,
            validator_fn=mock_validator,
            consistency_rules=consistency_rules,
            timestamp_path="meta.lastUpdated"
        )
        
        self.assertIn("overall_quality_score", result)
        self.assertIn("dimensions", result)
        self.assertIn(DataQualityDimension.COMPLETENESS, result["dimensions"])
        self.assertIn(DataQualityDimension.CONFORMANCE, result["dimensions"])
        self.assertIn(DataQualityDimension.CONSISTENCY, result["dimensions"])
        
        # Test with custom weights
        weights = {
            DataQualityDimension.COMPLETENESS: 0.5,
            DataQualityDimension.CONFORMANCE: 0.3,
            DataQualityDimension.CONSISTENCY: 0.2
        }
        
        result = self.assessor.assess_overall_quality(
            self.patient_resource,
            required_paths=required_paths,
            validator_fn=mock_validator,
            consistency_rules=consistency_rules,
            weights=weights
        )
        
        self.assertIn("weighted_scores", result)
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()

    def test_assess_batch_quality(self):
        """Test assessing quality for a batch of resources."""
        # Mock validator function
        mock_validator = MagicMock(return_value={"valid": True, "issues": []})
        
        # Define consistency rules
        consistency_rules = [
            {
                "name": "Has gender",
                "condition": "gender.exists()"
            }
        ]
        
        # Define required paths
        required_paths = ["name.given", "gender"]
        
        # Test with a batch of resources
        resources = [self.patient_resource, self.incomplete_patient]
        
        result = self.assessor.assess_batch_quality(
            resources,
            required_paths=required_paths,
            validator_fn=mock_validator,
            consistency_rules=consistency_rules
        )
        
        self.assertIn("overall_quality_score", result)
        self.assertEqual(result["resource_count"], 2)
        self.assertIn("quality_by_type", result)
        self.assertIn("Patient", result["quality_by_type"])
        
        # Verify metrics collector was called
        self.mock_metrics_collector.record_metric.assert_called()


if __name__ == "__main__":
    unittest.main() 