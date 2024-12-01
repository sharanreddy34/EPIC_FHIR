"""
Quality interventions module for defining standard procedures to address data quality issues.

This module provides standardized intervention procedures for different types of 
quality issues, including automated remediation, manual fix guidelines, and escalation paths.
"""

import logging
import os
import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from epic_fhir_integration.metrics.quality_alerts import (
    QualityAlert, 
    AlertCategory, 
    AlertSeverity
)
from epic_fhir_integration.metrics.data_quality import DataQualityDimension
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

logger = logging.getLogger(__name__)

class InterventionType(str, Enum):
    """Types of quality interventions."""
    AUTOMATED_FIX = "automated_fix"
    MANUAL_REVIEW = "manual_review"
    IGNORE = "ignore"
    ESCALATE = "escalate"
    NOTIFY = "notify"

class InterventionStatus(str, Enum):
    """Status of intervention implementation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class QualityIntervention:
    """Base class for quality interventions."""
    
    def __init__(
        self,
        alert: QualityAlert,
        intervention_type: InterventionType,
        description: str,
        priority: int = 2,  # 1 (highest) to 5 (lowest)
    ):
        """Initialize intervention.
        
        Args:
            alert: The quality alert triggering this intervention
            intervention_type: Type of intervention
            description: Description of the intervention procedure
            priority: Priority level (1-5)
        """
        self.alert = alert
        self.intervention_type = intervention_type
        self.description = description
        self.priority = priority
        self.status = InterventionStatus.PENDING
        self.result = None
        self.notes = []
        self.created_at = datetime.utcnow()
        self.completed_at = None
        
    def execute(self) -> bool:
        """Execute the intervention.
        
        Returns:
            True if successful, False otherwise
        """
        # Default implementation to be overridden by subclasses
        logger.warning(f"Base execute method called for {self.__class__.__name__}")
        self.status = InterventionStatus.FAILED
        return False
    
    def add_note(self, note: str) -> None:
        """Add a note to the intervention record.
        
        Args:
            note: Note text
        """
        self.notes.append({
            "timestamp": datetime.utcnow().isoformat(),
            "text": note
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert intervention to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "alert_id": self.alert.id,
            "alert_name": self.alert.name,
            "intervention_type": self.intervention_type,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class AutomatedFixIntervention(QualityIntervention):
    """Intervention that applies an automated fix for quality issues."""
    
    def __init__(
        self,
        alert: QualityAlert,
        description: str,
        fix_function: Callable,
        fix_args: Dict[str, Any] = None,
        priority: int = 1
    ):
        """Initialize automated fix intervention.
        
        Args:
            alert: The quality alert triggering this intervention
            description: Description of the intervention procedure
            fix_function: Function to call for the fix
            fix_args: Arguments to pass to the fix function
            priority: Priority level (1-5)
        """
        super().__init__(
            alert=alert,
            intervention_type=InterventionType.AUTOMATED_FIX,
            description=description,
            priority=priority
        )
        self.fix_function = fix_function
        self.fix_args = fix_args or {}
    
    def execute(self) -> bool:
        """Execute the automated fix.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.status = InterventionStatus.IN_PROGRESS
            self.add_note(f"Starting automated fix: {self.description}")
            
            # Execute the fix function
            result = self.fix_function(**self.fix_args)
            
            self.result = result
            self.status = InterventionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            self.add_note(f"Automated fix completed successfully")
            return True
        except Exception as e:
            self.status = InterventionStatus.FAILED
            self.add_note(f"Error during automated fix: {str(e)}")
            logger.error(f"Error executing automated fix: {str(e)}")
            return False


class ManualReviewIntervention(QualityIntervention):
    """Intervention that requires manual review and action."""
    
    def __init__(
        self,
        alert: QualityAlert,
        description: str,
        review_steps: List[str],
        assigned_to: Optional[str] = None,
        deadline_hours: Optional[int] = None,
        priority: int = 2
    ):
        """Initialize manual review intervention.
        
        Args:
            alert: The quality alert triggering this intervention
            description: Description of the intervention procedure
            review_steps: List of steps for manual review
            assigned_to: Person assigned to the review
            deadline_hours: Optional deadline in hours
            priority: Priority level (1-5)
        """
        super().__init__(
            alert=alert,
            intervention_type=InterventionType.MANUAL_REVIEW,
            description=description,
            priority=priority
        )
        self.review_steps = review_steps
        self.assigned_to = assigned_to
        self.deadline_hours = deadline_hours
        self.deadline = datetime.utcnow() + timedelta(hours=deadline_hours) if deadline_hours else None
    
    def execute(self) -> bool:
        """Record the manual review requirement.
        
        For manual reviews, execution just means recording the task.
        
        Returns:
            True if successfully recorded
        """
        try:
            self.status = InterventionStatus.IN_PROGRESS
            self.add_note(f"Manual review requested: {self.description}")
            if self.assigned_to:
                self.add_note(f"Assigned to: {self.assigned_to}")
            if self.deadline:
                self.add_note(f"Deadline: {self.deadline.isoformat()}")
            return True
        except Exception as e:
            self.status = InterventionStatus.FAILED
            self.add_note(f"Error recording manual review: {str(e)}")
            logger.error(f"Error recording manual review: {str(e)}")
            return False
    
    def complete_review(
        self,
        resolution_notes: str,
        successful: bool = True
    ) -> None:
        """Mark the manual review as completed.
        
        Args:
            resolution_notes: Notes on resolution
            successful: Whether the intervention was successful
        """
        self.status = InterventionStatus.COMPLETED if successful else InterventionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.add_note(resolution_notes)
        self.result = {
            "successful": successful,
            "resolution_notes": resolution_notes
        }


class NotificationIntervention(QualityIntervention):
    """Intervention that sends notification about quality issues."""
    
    def __init__(
        self,
        alert: QualityAlert,
        description: str,
        recipients: List[str],
        notification_method: str = "email",
        template_name: Optional[str] = None,
        priority: int = 3
    ):
        """Initialize notification intervention.
        
        Args:
            alert: The quality alert triggering this intervention
            description: Description of the notification
            recipients: List of recipient identifiers (emails, usernames, etc.)
            notification_method: Method of notification (email, slack, etc.)
            template_name: Optional template name for notification
            priority: Priority level (1-5)
        """
        super().__init__(
            alert=alert,
            intervention_type=InterventionType.NOTIFY,
            description=description,
            priority=priority
        )
        self.recipients = recipients
        self.notification_method = notification_method
        self.template_name = template_name
        
    def execute(self) -> bool:
        """Send the notification.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.status = InterventionStatus.IN_PROGRESS
            self.add_note(f"Sending notification to {len(self.recipients)} recipients via {self.notification_method}")
            
            # Placeholder for notification logic - would integrate with notification system
            # For now, log but don't actually send
            logger.info(f"Would send notification about '{self.alert.name}' to {self.recipients}")
            
            self.status = InterventionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            self.add_note(f"Notification recorded (not actually sent in this version)")
            self.result = {
                "recipients": self.recipients,
                "method": self.notification_method,
                "template": self.template_name
            }
            return True
        except Exception as e:
            self.status = InterventionStatus.FAILED
            self.add_note(f"Error sending notification: {str(e)}")
            logger.error(f"Error sending notification: {str(e)}")
            return False


class EscalationIntervention(QualityIntervention):
    """Intervention that escalates severe quality issues to leadership."""
    
    def __init__(
        self,
        alert: QualityAlert,
        description: str,
        escalation_level: str,
        escalation_path: List[str],
        priority: int = 1
    ):
        """Initialize escalation intervention.
        
        Args:
            alert: The quality alert triggering this intervention
            description: Description of the issue requiring escalation
            escalation_level: Level of escalation (team, department, executive, etc.)
            escalation_path: Ordered list of people/roles in the escalation path
            priority: Priority level (1-5)
        """
        super().__init__(
            alert=alert,
            intervention_type=InterventionType.ESCALATE,
            description=description,
            priority=priority
        )
        self.escalation_level = escalation_level
        self.escalation_path = escalation_path
        
    def execute(self) -> bool:
        """Execute the escalation process.
        
        Returns:
            True if successfully initiated
        """
        try:
            self.status = InterventionStatus.IN_PROGRESS
            self.add_note(f"Initiating {self.escalation_level} level escalation")
            
            # Record escalation details
            self.result = {
                "escalation_level": self.escalation_level,
                "escalation_path": self.escalation_path,
                "escalation_time": datetime.utcnow().isoformat()
            }
            
            # In a real implementation, this would trigger escalation processes
            logger.info(f"Escalation initiated for alert {self.alert.id}: {self.alert.name}")
            
            self.status = InterventionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            return True
        except Exception as e:
            self.status = InterventionStatus.FAILED
            self.add_note(f"Error initiating escalation: {str(e)}")
            logger.error(f"Error initiating escalation: {str(e)}")
            return False


class InterventionRegistry:
    """Registry of standard interventions for different types of quality issues."""
    
    def __init__(self):
        """Initialize the intervention registry."""
        self.intervention_handlers = {}
        self.register_standard_interventions()
    
    def register_intervention(
        self,
        alert_category: Union[AlertCategory, str],
        severity_level: Union[AlertSeverity, str],
        intervention_creator: Callable[[QualityAlert], QualityIntervention]
    ) -> None:
        """Register an intervention handler for a specific alert type.
        
        Args:
            alert_category: Category of alert to handle
            severity_level: Severity level of alert to handle
            intervention_creator: Function that creates appropriate intervention
        """
        # Convert enum values to strings if needed
        if hasattr(alert_category, "value"):
            alert_category = alert_category.value
            
        if hasattr(severity_level, "value"):
            severity_level = severity_level.value
            
        key = f"{alert_category}:{severity_level}"
        self.intervention_handlers[key] = intervention_creator
        logger.debug(f"Registered intervention handler for {key}")
        
    def get_intervention(self, alert: QualityAlert) -> Optional[QualityIntervention]:
        """Get appropriate intervention for an alert.
        
        Args:
            alert: The quality alert to handle
            
        Returns:
            QualityIntervention instance or None if no handler
        """
        key = f"{alert.category}:{alert.severity}"
        handler = self.intervention_handlers.get(key)
        
        if handler:
            return handler(alert)
            
        # If no exact match, try category with any severity
        key = f"{alert.category}:*"
        handler = self.intervention_handlers.get(key)
        
        if handler:
            return handler(alert)
            
        # If still no match, try any category with this severity
        key = f"*:{alert.severity}"
        handler = self.intervention_handlers.get(key)
        
        if handler:
            return handler(alert)
            
        logger.warning(f"No intervention handler found for alert: {alert.name} ({alert.category}:{alert.severity})")
        return None
    
    def register_standard_interventions(self) -> None:
        """Register standard intervention handlers for common quality issues."""
        # COMPLETENESS handlers
        self.register_intervention(
            AlertCategory.COMPLETENESS,
            AlertSeverity.HIGH,
            lambda alert: ManualReviewIntervention(
                alert=alert,
                description="Review and fix missing critical data elements",
                review_steps=[
                    "1. Identify missing fields from the alert details",
                    "2. Check source systems for the missing data",
                    "3. Add missing data if available",
                    "4. If not available, document the reason"
                ],
                priority=1
            )
        )
        
        self.register_intervention(
            AlertCategory.COMPLETENESS,
            AlertSeverity.MEDIUM,
            lambda alert: NotificationIntervention(
                alert=alert,
                description="Notify data stewards about incomplete data",
                recipients=["data-stewards@example.org"],
                notification_method="email",
                template_name="incomplete_data_notification",
                priority=2
            )
        )
        
        # CONFORMANCE handlers
        self.register_intervention(
            AlertCategory.CONFORMANCE,
            AlertSeverity.HIGH, 
            lambda alert: ManualReviewIntervention(
                alert=alert,
                description="Fix FHIR conformance issues",
                review_steps=[
                    "1. Review conformance errors in the report",
                    "2. Check if the issue is in the mapping logic",
                    "3. Correct the mapping or transformation logic",
                    "4. Verify fix with test data"
                ],
                priority=1
            )
        )
        
        # CONSISTENCY handlers
        self.register_intervention(
            AlertCategory.CONSISTENCY,
            AlertSeverity.MEDIUM,
            lambda alert: AutomatedFixIntervention(
                alert=alert,
                description="Apply consistency rules to fix inconsistent data",
                fix_function=self._apply_consistency_rules,
                fix_args={"alert": alert},
                priority=2
            )
        )
        
        # VALIDATION handlers
        self.register_intervention(
            AlertCategory.VALIDATION,
            AlertSeverity.CRITICAL,
            lambda alert: EscalationIntervention(
                alert=alert,
                description="Critical validation failures requiring immediate attention",
                escalation_level="team-lead",
                escalation_path=["team-lead@example.org", "department-head@example.org"],
                priority=1
            )
        )
        
        # PIPELINE handlers
        self.register_intervention(
            AlertCategory.PIPELINE,
            AlertSeverity.CRITICAL,
            lambda alert: EscalationIntervention(
                alert=alert,
                description="Critical pipeline failure",
                escalation_level="operations",
                escalation_path=["devops@example.org", "oncall@example.org"],
                priority=1
            )
        )
        
        # Fallback handler for any unhandled critical alerts
        self.register_intervention(
            "*",  # Any category
            AlertSeverity.CRITICAL,
            lambda alert: NotificationIntervention(
                alert=alert,
                description="Critical quality alert requiring attention",
                recipients=["data-quality@example.org", "oncall@example.org"],
                notification_method="sms",
                priority=1
            )
        )
    
    def _apply_consistency_rules(self, alert: QualityAlert) -> Dict[str, Any]:
        """Apply consistency rules to fix inconsistent data.
        
        This is a placeholder implementation that would be replaced
        with actual logic in a real system.
        
        Args:
            alert: The alert with details about the consistency issue
            
        Returns:
            Results of applying consistency rules
        """
        # This would contain actual fix logic in a real implementation
        logger.info(f"Would apply consistency rules for alert: {alert.name}")
        return {
            "fixed": True,
            "applied_rules": ["sample_consistency_rule"],
            "timestamp": datetime.utcnow().isoformat()
        }


class InterventionManager:
    """Manages the creation, execution and tracking of quality interventions."""
    
    def __init__(
        self,
        registry: Optional[InterventionRegistry] = None,
        storage_dir: Optional[str] = None
    ):
        """Initialize the intervention manager.
        
        Args:
            registry: Optional intervention registry
            storage_dir: Optional directory for storing intervention records
        """
        self.registry = registry or InterventionRegistry()
        self.storage_dir = storage_dir
        self.interventions = []
        
        # Create storage directory if specified and doesn't exist
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
    
    def create_intervention(self, alert: QualityAlert) -> Optional[QualityIntervention]:
        """Create an appropriate intervention for an alert.
        
        Args:
            alert: The quality alert to handle
            
        Returns:
            Created intervention or None if no appropriate handler
        """
        intervention = self.registry.get_intervention(alert)
        
        if intervention:
            self.interventions.append(intervention)
            logger.info(f"Created intervention for alert {alert.id}: {intervention.intervention_type}")
        
        return intervention
    
    def execute_intervention(
        self, 
        intervention: QualityIntervention
    ) -> bool:
        """Execute an intervention.
        
        Args:
            intervention: The intervention to execute
            
        Returns:
            True if execution was successful
        """
        result = intervention.execute()
        
        # Store the intervention record if storage_dir specified
        if self.storage_dir:
            self._store_intervention(intervention)
            
        return result
    
    def process_alert(self, alert: QualityAlert) -> Optional[QualityIntervention]:
        """Process an alert by creating and executing an intervention.
        
        Args:
            alert: The quality alert to process
            
        Returns:
            The executed intervention or None if no appropriate handler
        """
        intervention = self.create_intervention(alert)
        
        if intervention:
            self.execute_intervention(intervention)
            
        return intervention
    
    def get_pending_interventions(self) -> List[QualityIntervention]:
        """Get all pending interventions.
        
        Returns:
            List of pending interventions
        """
        return [i for i in self.interventions if i.status == InterventionStatus.PENDING]
    
    def get_active_interventions(self) -> List[QualityIntervention]:
        """Get all active (pending or in-progress) interventions.
        
        Returns:
            List of active interventions
        """
        return [
            i for i in self.interventions 
            if i.status in [InterventionStatus.PENDING, InterventionStatus.IN_PROGRESS]
        ]
    
    def get_intervention_by_alert_id(self, alert_id: str) -> Optional[QualityIntervention]:
        """Get an intervention by its associated alert ID.
        
        Args:
            alert_id: ID of the alert
            
        Returns:
            Intervention or None if not found
        """
        for intervention in self.interventions:
            if intervention.alert.id == alert_id:
                return intervention
        return None
    
    def _store_intervention(self, intervention: QualityIntervention) -> None:
        """Store an intervention record.
        
        Args:
            intervention: The intervention to store
        """
        if not self.storage_dir:
            return
            
        try:
            # Create a filename based on alert ID and timestamp
            filename = f"intervention_{intervention.alert.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.storage_dir, filename)
            
            # Store as JSON
            with open(filepath, "w") as f:
                json.dump(intervention.to_dict(), f, indent=2)
                
            logger.debug(f"Stored intervention record to {filepath}")
        except Exception as e:
            logger.error(f"Error storing intervention record: {str(e)}")
    
    def load_interventions(self) -> None:
        """Load previously stored intervention records.
        
        Note: This would require additional logic to reconstruct 
        full intervention objects from the stored data.
        """
        if not self.storage_dir or not os.path.exists(self.storage_dir):
            logger.warning("No storage directory for interventions")
            return
            
        try:
            # Find all JSON files in the storage directory
            files = list(Path(self.storage_dir).glob("intervention_*.json"))
            
            logger.info(f"Found {len(files)} stored intervention records")
            
            # In a real implementation, this would reconstruct the interventions
            # For now, just log the count
        except Exception as e:
            logger.error(f"Error loading intervention records: {str(e)}")


# Example usage for creating an intervention procedure

def create_intervention_for_completeness_issue(
    resource: Dict[str, Any],
    missing_fields: List[str],
    severity: AlertSeverity
) -> QualityIntervention:
    """Create an intervention for a completeness issue.
    
    Args:
        resource: The resource with completeness issues
        missing_fields: List of missing fields
        severity: Severity of the issue
        
    Returns:
        Appropriate intervention
    """
    resource_type = resource.get("resourceType", "Unknown")
    resource_id = resource.get("id", "unknown")
    
    # Create an alert (would typically come from the alert system)
    alert = QualityAlert(
        definition=None,  # This would normally be set
        metric_value=0.0,
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "missing_fields": missing_fields
        },
        timestamp=datetime.utcnow()
    )
    alert.id = f"completeness_{resource_type}_{resource_id}"
    alert.name = f"Completeness issue in {resource_type}"
    alert.description = f"Missing required fields in {resource_type}"
    alert.severity = severity
    alert.category = AlertCategory.COMPLETENESS
    
    # Create appropriate intervention based on severity
    if severity == AlertSeverity.CRITICAL or severity == AlertSeverity.HIGH:
        return ManualReviewIntervention(
            alert=alert,
            description=f"Fix missing fields in {resource_type} {resource_id}",
            review_steps=[
                f"1. Locate {resource_type} resource with ID {resource_id}",
                f"2. Add the following missing fields: {', '.join(missing_fields)}",
                "3. Verify the data is accurate",
                "4. Update the resource"
            ],
            priority=1 if severity == AlertSeverity.CRITICAL else 2
        )
    else:
        return NotificationIntervention(
            alert=alert,
            description=f"Notify about incomplete {resource_type} data",
            recipients=[f"{resource_type.lower()}-stewards@example.org"],
            priority=3
        )


def create_intervention_for_conformance_issue(
    resource: Dict[str, Any],
    issues: List[Dict[str, Any]],
    severity: AlertSeverity
) -> QualityIntervention:
    """Create an intervention for a conformance issue.
    
    Args:
        resource: The resource with conformance issues
        issues: List of conformance issues
        severity: Severity of the issue
        
    Returns:
        Appropriate intervention
    """
    resource_type = resource.get("resourceType", "Unknown")
    resource_id = resource.get("id", "unknown")
    
    # Create an alert
    alert = QualityAlert(
        definition=None,
        metric_value=0.0,
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "issues": issues
        },
        timestamp=datetime.utcnow()
    )
    alert.id = f"conformance_{resource_type}_{resource_id}"
    alert.name = f"Conformance issue in {resource_type}"
    alert.description = f"Resource does not conform to profile"
    alert.severity = severity
    alert.category = AlertCategory.CONFORMANCE
    
    # Create intervention based on severity
    if severity == AlertSeverity.CRITICAL:
        return EscalationIntervention(
            alert=alert,
            description=f"Critical conformance issue in {resource_type} {resource_id}",
            escalation_level="team-lead",
            escalation_path=["fhir-team@example.org", "data-quality@example.org"],
            priority=1
        )
    elif severity == AlertSeverity.HIGH:
        return ManualReviewIntervention(
            alert=alert,
            description=f"Fix conformance issues in {resource_type} {resource_id}",
            review_steps=[
                f"1. Review the following issues: {', '.join(issue['message'] for issue in issues[:3])}...",
                "2. Check the resource against the profile requirements",
                "3. Update the resource to conform to the profile"
            ],
            priority=2
        )
    else:
        return NotificationIntervention(
            alert=alert,
            description=f"Minor conformance issues in {resource_type}",
            recipients=["fhir-validators@example.org"],
            priority=3
        ) 