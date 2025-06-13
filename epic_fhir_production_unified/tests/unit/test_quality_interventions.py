"""
Tests for the quality interventions module.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from epic_fhir_integration.metrics.quality_alerts import (
    QualityAlert,
    AlertCategory,
    AlertSeverity
)
from epic_fhir_integration.metrics.quality_interventions import (
    AutomatedFixIntervention,
    EscalationIntervention,
    InterventionManager,
    InterventionRegistry,
    InterventionStatus,
    InterventionType,
    ManualReviewIntervention,
    NotificationIntervention,
    QualityIntervention,
    create_intervention_for_completeness_issue,
    create_intervention_for_conformance_issue
)


class TestQualityIntervention(unittest.TestCase):
    """Tests for the QualityIntervention base class."""

    def setUp(self):
        """Set up test resources."""
        # Mock alert
        self.mock_alert = MagicMock(spec=QualityAlert)
        self.mock_alert.id = "test_alert_id"
        self.mock_alert.name = "Test Alert"
        self.mock_alert.category = AlertCategory.COMPLETENESS
        self.mock_alert.severity = AlertSeverity.HIGH
        
    def test_initialization(self):
        """Test intervention initialization."""
        intervention = QualityIntervention(
            alert=self.mock_alert,
            intervention_type=InterventionType.MANUAL_REVIEW,
            description="Test intervention",
            priority=2
        )
        
        # Check attributes
        self.assertEqual(intervention.alert, self.mock_alert)
        self.assertEqual(intervention.intervention_type, InterventionType.MANUAL_REVIEW)
        self.assertEqual(intervention.description, "Test intervention")
        self.assertEqual(intervention.priority, 2)
        self.assertEqual(intervention.status, InterventionStatus.PENDING)
        self.assertIsNone(intervention.result)
        self.assertEqual(intervention.notes, [])
        self.assertIsNotNone(intervention.created_at)
        self.assertIsNone(intervention.completed_at)
        
    def test_add_note(self):
        """Test adding notes to an intervention."""
        intervention = QualityIntervention(
            alert=self.mock_alert,
            intervention_type=InterventionType.MANUAL_REVIEW,
            description="Test intervention"
        )
        
        # Add a note
        intervention.add_note("Test note")
        
        # Verify the note was added
        self.assertEqual(len(intervention.notes), 1)
        self.assertEqual(intervention.notes[0]["text"], "Test note")
        self.assertIn("timestamp", intervention.notes[0])
        
    def test_to_dict(self):
        """Test conversion to dictionary."""
        intervention = QualityIntervention(
            alert=self.mock_alert,
            intervention_type=InterventionType.MANUAL_REVIEW,
            description="Test intervention"
        )
        
        # Convert to dict
        intervention_dict = intervention.to_dict()
        
        # Verify dictionary structure
        self.assertEqual(intervention_dict["alert_id"], "test_alert_id")
        self.assertEqual(intervention_dict["alert_name"], "Test Alert")
        self.assertEqual(intervention_dict["intervention_type"], InterventionType.MANUAL_REVIEW)
        self.assertEqual(intervention_dict["description"], "Test intervention")
        self.assertEqual(intervention_dict["status"], InterventionStatus.PENDING)
        self.assertIsNone(intervention_dict["result"])
        self.assertEqual(intervention_dict["notes"], [])
        self.assertIsNotNone(intervention_dict["created_at"])
        self.assertIsNone(intervention_dict["completed_at"])


class TestAutomatedFixIntervention(unittest.TestCase):
    """Tests for the AutomatedFixIntervention class."""

    def setUp(self):
        """Set up test resources."""
        # Mock alert
        self.mock_alert = MagicMock(spec=QualityAlert)
        self.mock_alert.id = "test_alert_id"
        self.mock_alert.name = "Test Alert"
        
        # Mock fix function
        self.mock_fix_function = MagicMock(return_value={"status": "fixed"})
        
    def test_initialization(self):
        """Test initialization."""
        intervention = AutomatedFixIntervention(
            alert=self.mock_alert,
            description="Fix test issue",
            fix_function=self.mock_fix_function,
            fix_args={"param1": "value1"},
            priority=1
        )
        
        # Check attributes
        self.assertEqual(intervention.alert, self.mock_alert)
        self.assertEqual(intervention.description, "Fix test issue")
        self.assertEqual(intervention.fix_function, self.mock_fix_function)
        self.assertEqual(intervention.fix_args, {"param1": "value1"})
        self.assertEqual(intervention.priority, 1)
        self.assertEqual(intervention.intervention_type, InterventionType.AUTOMATED_FIX)
        
    def test_execute_success(self):
        """Test successful execution."""
        intervention = AutomatedFixIntervention(
            alert=self.mock_alert,
            description="Fix test issue",
            fix_function=self.mock_fix_function,
            fix_args={"param1": "value1"}
        )
        
        # Execute the intervention
        result = intervention.execute()
        
        # Verify execution
        self.assertTrue(result)
        self.assertEqual(intervention.status, InterventionStatus.COMPLETED)
        self.assertIsNotNone(intervention.completed_at)
        self.assertEqual(intervention.result, {"status": "fixed"})
        self.assertTrue(len(intervention.notes) > 0)
        
        # Verify fix function was called with correct args
        self.mock_fix_function.assert_called_once_with(param1="value1")
        
    def test_execute_failure(self):
        """Test execution failure."""
        # Make fix function raise an exception
        self.mock_fix_function.side_effect = Exception("Test error")
        
        intervention = AutomatedFixIntervention(
            alert=self.mock_alert,
            description="Fix test issue",
            fix_function=self.mock_fix_function
        )
        
        # Execute the intervention
        result = intervention.execute()
        
        # Verify execution
        self.assertFalse(result)
        self.assertEqual(intervention.status, InterventionStatus.FAILED)
        self.assertIsNone(intervention.completed_at)
        self.assertIsNone(intervention.result)
        self.assertTrue(len(intervention.notes) > 0)
        self.assertIn("Error", intervention.notes[0]["text"])


class TestInterventionRegistry(unittest.TestCase):
    """Tests for the InterventionRegistry class."""

    def setUp(self):
        """Set up test resources."""
        self.registry = InterventionRegistry()
        
        # Mock alert
        self.mock_alert = MagicMock(spec=QualityAlert)
        self.mock_alert.id = "test_alert_id"
        self.mock_alert.name = "Test Alert"
        self.mock_alert.category = AlertCategory.COMPLETENESS
        self.mock_alert.severity = AlertSeverity.HIGH
        
    def test_register_intervention(self):
        """Test registering an intervention handler."""
        # Create mock intervention creator
        mock_creator = MagicMock(return_value=MagicMock(spec=QualityIntervention))
        
        # Register the intervention
        self.registry.register_intervention(
            alert_category=AlertCategory.COMPLETENESS,
            severity_level=AlertSeverity.MEDIUM,
            intervention_creator=mock_creator
        )
        
        # Check it was registered
        key = f"{AlertCategory.COMPLETENESS}:{AlertSeverity.MEDIUM}"
        self.assertIn(key, self.registry.intervention_handlers)
        self.assertEqual(self.registry.intervention_handlers[key], mock_creator)
        
    def test_get_intervention_exact_match(self):
        """Test getting intervention with exact category and severity match."""
        # Register a test intervention
        mock_intervention = MagicMock(spec=QualityIntervention)
        mock_creator = MagicMock(return_value=mock_intervention)
        
        self.registry.register_intervention(
            AlertCategory.COMPLETENESS,
            AlertSeverity.HIGH,
            mock_creator
        )
        
        # Get intervention for matching alert
        intervention = self.registry.get_intervention(self.mock_alert)
        
        # Verify results
        self.assertEqual(intervention, mock_intervention)
        mock_creator.assert_called_once_with(self.mock_alert)
        
    def test_get_intervention_category_wildcard(self):
        """Test getting intervention with category wildcard match."""
        # Register a test intervention with category wildcard
        mock_intervention = MagicMock(spec=QualityIntervention)
        mock_creator = MagicMock(return_value=mock_intervention)
        
        self.registry.register_intervention(
            "*",  # Any category
            AlertSeverity.HIGH,
            mock_creator
        )
        
        # Get intervention for alert with matching severity
        intervention = self.registry.get_intervention(self.mock_alert)
        
        # Verify results
        self.assertEqual(intervention, mock_intervention)
        mock_creator.assert_called_once_with(self.mock_alert)
        
    def test_get_intervention_no_match(self):
        """Test getting intervention with no match."""
        # Create alert with unhandled category/severity
        unhandled_alert = MagicMock(spec=QualityAlert)
        unhandled_alert.category = "unhandled_category"
        unhandled_alert.severity = "unhandled_severity"
        
        # Get intervention
        intervention = self.registry.get_intervention(unhandled_alert)
        
        # Verify no intervention was returned
        self.assertIsNone(intervention)
        
    def test_standard_interventions(self):
        """Test that standard interventions are registered."""
        # Registry is initialized with standard interventions
        
        # Test we have handlers for common categories
        self.assertTrue(any(
            AlertCategory.COMPLETENESS in key 
            for key in self.registry.intervention_handlers.keys()
        ))
        
        self.assertTrue(any(
            AlertCategory.CONFORMANCE in key 
            for key in self.registry.intervention_handlers.keys()
        ))
        
        self.assertTrue(any(
            AlertCategory.VALIDATION in key 
            for key in self.registry.intervention_handlers.keys()
        ))


class TestInterventionManager(unittest.TestCase):
    """Tests for the InterventionManager class."""

    def setUp(self):
        """Set up test resources."""
        # Create a temporary directory for storing interventions
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock registry
        self.mock_registry = MagicMock(spec=InterventionRegistry)
        
        # Create manager
        self.manager = InterventionManager(
            registry=self.mock_registry,
            storage_dir=self.temp_dir
        )
        
        # Mock alert
        self.mock_alert = MagicMock(spec=QualityAlert)
        self.mock_alert.id = "test_alert_id"
        self.mock_alert.name = "Test Alert"
        
        # Mock intervention
        self.mock_intervention = MagicMock(spec=QualityIntervention)
        self.mock_intervention.alert = self.mock_alert
        self.mock_intervention.to_dict.return_value = {
            "alert_id": "test_alert_id",
            "description": "Test intervention"
        }
        
    def tearDown(self):
        """Clean up resources."""
        # Remove temp directory
        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)
        
    def test_create_intervention(self):
        """Test creating an intervention for an alert."""
        # Set up registry mock to return our mock intervention
        self.mock_registry.get_intervention.return_value = self.mock_intervention
        
        # Create intervention
        intervention = self.manager.create_intervention(self.mock_alert)
        
        # Verify
        self.assertEqual(intervention, self.mock_intervention)
        self.mock_registry.get_intervention.assert_called_once_with(self.mock_alert)
        self.assertIn(self.mock_intervention, self.manager.interventions)
        
    def test_create_intervention_no_handler(self):
        """Test creating an intervention when no handler is available."""
        # Set up registry mock to return None
        self.mock_registry.get_intervention.return_value = None
        
        # Create intervention
        intervention = self.manager.create_intervention(self.mock_alert)
        
        # Verify
        self.assertIsNone(intervention)
        self.mock_registry.get_intervention.assert_called_once_with(self.mock_alert)
        self.assertEqual(len(self.manager.interventions), 0)
        
    def test_execute_intervention(self):
        """Test executing an intervention."""
        # Set up intervention mock to return success
        self.mock_intervention.execute.return_value = True
        
        # Execute intervention
        result = self.manager.execute_intervention(self.mock_intervention)
        
        # Verify
        self.assertTrue(result)
        self.mock_intervention.execute.assert_called_once()
        
        # Check if intervention was stored
        json_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.json')]
        self.assertEqual(len(json_files), 1)
        
    def test_process_alert(self):
        """Test processing an alert (create + execute)."""
        # Set up registry mock to return our mock intervention
        self.mock_registry.get_intervention.return_value = self.mock_intervention
        
        # Set up intervention mock to return success
        self.mock_intervention.execute.return_value = True
        
        # Process alert
        intervention = self.manager.process_alert(self.mock_alert)
        
        # Verify intervention was created and executed
        self.assertEqual(intervention, self.mock_intervention)
        self.mock_registry.get_intervention.assert_called_once_with(self.mock_alert)
        self.mock_intervention.execute.assert_called_once()
        

class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions in the interventions module."""

    def test_create_intervention_for_completeness_issue(self):
        """Test creating an intervention for a completeness issue."""
        # Create resource with missing fields
        resource = {
            "resourceType": "Patient",
            "id": "test-patient"
        }
        missing_fields = ["name", "gender"]
        
        # Create intervention for critical issue
        intervention = create_intervention_for_completeness_issue(
            resource=resource,
            missing_fields=missing_fields,
            severity=AlertSeverity.CRITICAL
        )
        
        # Verify intervention type and properties
        self.assertIsInstance(intervention, ManualReviewIntervention)
        self.assertEqual(intervention.priority, 1)  # Critical priority
        self.assertEqual(intervention.alert.category, AlertCategory.COMPLETENESS)
        self.assertEqual(intervention.alert.severity, AlertSeverity.CRITICAL)
        
        # Create intervention for medium issue
        intervention = create_intervention_for_completeness_issue(
            resource=resource,
            missing_fields=missing_fields,
            severity=AlertSeverity.MEDIUM
        )
        
        # Verify intervention type changed based on severity
        self.assertIsInstance(intervention, NotificationIntervention)
        self.assertEqual(intervention.priority, 3)  # Medium priority
        
    def test_create_intervention_for_conformance_issue(self):
        """Test creating an intervention for a conformance issue."""
        # Create resource with conformance issues
        resource = {
            "resourceType": "Observation",
            "id": "test-observation"
        }
        issues = [
            {"severity": "error", "message": "Missing required code element"}
        ]
        
        # Create intervention for critical issue
        intervention = create_intervention_for_conformance_issue(
            resource=resource,
            issues=issues,
            severity=AlertSeverity.CRITICAL
        )
        
        # Verify intervention type and properties
        self.assertIsInstance(intervention, EscalationIntervention)
        self.assertEqual(intervention.priority, 1)
        self.assertEqual(intervention.alert.category, AlertCategory.CONFORMANCE)
        self.assertEqual(intervention.alert.severity, AlertSeverity.CRITICAL)
        
        # Create intervention for high severity issue
        intervention = create_intervention_for_conformance_issue(
            resource=resource,
            issues=issues,
            severity=AlertSeverity.HIGH
        )
        
        # Verify intervention type changed based on severity
        self.assertIsInstance(intervention, ManualReviewIntervention)
        
        # Create intervention for medium severity issue
        intervention = create_intervention_for_conformance_issue(
            resource=resource,
            issues=issues,
            severity=AlertSeverity.MEDIUM
        )
        
        # Verify intervention type changed based on severity
        self.assertIsInstance(intervention, NotificationIntervention)


if __name__ == "__main__":
    unittest.main() 