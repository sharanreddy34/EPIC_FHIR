"""
Quality alerts module for generating threshold-based alerts for data quality issues.

This module provides functionality for defining quality alert thresholds,
evaluating metrics against those thresholds, and generating alerts when
quality issues are detected.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from epic_fhir_integration.metrics.collector import MetricsCollector

logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """Enumeration of alert severities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertStatus(str, Enum):
    """Enumeration of alert statuses."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"

class AlertCategory(str, Enum):
    """Categories for quality alerts."""
    COMPLETENESS = "completeness"
    CONFORMANCE = "conformance"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    PIPELINE = "pipeline"

class QualityAlertDefinition:
    """Definition of a quality alert based on metrics thresholds."""
    
    def __init__(
        self,
        name: str,
        description: str,
        metric_pattern: str,
        severity: AlertSeverity,
        category: AlertCategory,
        threshold_fn: Callable[[float], bool],
        resource_types: Optional[List[str]] = None,
        pipeline_stages: Optional[List[str]] = None,
        lookback_hours: int = 24,
        min_sample_size: int = 1,
        cooldown_minutes: int = 60
    ):
        """Initialize a quality alert definition.
        
        Args:
            name: Alert name
            description: Alert description
            metric_pattern: Pattern to match metric names
            severity: Alert severity
            category: Alert category
            threshold_fn: Function that evaluates a metric value against threshold
            resource_types: Optional list of resource types to alert on
            pipeline_stages: Optional list of pipeline stages to alert on
            lookback_hours: Hours to look back for metrics
            min_sample_size: Minimum sample size for triggering alert
            cooldown_minutes: Minutes between repeated alerts
        """
        self.name = name
        self.description = description
        self.metric_pattern = metric_pattern
        self.severity = severity
        self.category = category
        self.threshold_fn = threshold_fn
        self.resource_types = resource_types
        self.pipeline_stages = pipeline_stages
        self.lookback_hours = lookback_hours
        self.min_sample_size = min_sample_size
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = None
    
    @property
    def in_cooldown(self) -> bool:
        """Check if the alert is in cooldown period."""
        if self.last_triggered is None:
            return False
            
        now = datetime.utcnow()
        cooldown_delta = timedelta(minutes=self.cooldown_minutes)
        return (now - self.last_triggered) < cooldown_delta
    
    def evaluate(self, metric_value: float, sample_size: int = None) -> bool:
        """Evaluate if the alert should trigger.
        
        Args:
            metric_value: The metric value to evaluate
            sample_size: Optional sample size for the metric
            
        Returns:
            True if alert conditions are met, False otherwise
        """
        # Check sample size if provided
        if sample_size is not None and sample_size < self.min_sample_size:
            return False
            
        # Check if in cooldown period
        if self.in_cooldown:
            return False
            
        # Evaluate threshold
        return self.threshold_fn(metric_value)
    
    def mark_triggered(self) -> None:
        """Mark the alert as triggered now."""
        self.last_triggered = datetime.utcnow()


class QualityAlert:
    """An instance of a triggered quality alert."""
    
    def __init__(
        self,
        definition: QualityAlertDefinition,
        metric_value: float,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """Initialize a quality alert.
        
        Args:
            definition: Alert definition that triggered this alert
            metric_value: The metric value that triggered the alert
            details: Additional details about the alert
            timestamp: Optional timestamp for the alert, defaults to now
        """
        self.id = f"{definition.name.lower().replace(' ', '_')}_{datetime.utcnow().isoformat()}"
        self.name = definition.name
        self.description = definition.description
        self.severity = definition.severity
        self.category = definition.category
        self.metric_pattern = definition.metric_pattern
        self.metric_value = metric_value
        self.details = details
        self.timestamp = timestamp or datetime.utcnow()
        self.status = AlertStatus.ACTIVE
        self.resolution_timestamp = None
        self.resolution_note = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the alert to a dictionary.
        
        Returns:
            Dictionary representation of the alert
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "metric_pattern": self.metric_pattern,
            "metric_value": self.metric_value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "resolution_timestamp": self.resolution_timestamp.isoformat() if self.resolution_timestamp else None,
            "resolution_note": self.resolution_note
        }
    
    def resolve(self, note: str = None) -> None:
        """Resolve the alert.
        
        Args:
            note: Optional resolution note
        """
        self.status = AlertStatus.RESOLVED
        self.resolution_timestamp = datetime.utcnow()
        self.resolution_note = note
    
    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
    
    def silence(self) -> None:
        """Silence the alert."""
        self.status = AlertStatus.SILENCED


class QualityAlertManager:
    """Manages quality alert definitions and generation."""
    
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        alert_definitions: Optional[List[QualityAlertDefinition]] = None
    ):
        """Initialize the quality alert manager.
        
        Args:
            metrics_collector: Metrics collector with metrics data
            alert_definitions: Optional list of alert definitions
        """
        self.metrics_collector = metrics_collector
        self.alert_definitions = alert_definitions or []
        self.alerts: List[QualityAlert] = []
        
    def add_alert_definition(self, definition: QualityAlertDefinition) -> None:
        """Add an alert definition.
        
        Args:
            definition: The alert definition to add
        """
        self.alert_definitions.append(definition)
    
    def remove_alert_definition(self, name: str) -> bool:
        """Remove an alert definition.
        
        Args:
            name: Name of the alert definition to remove
            
        Returns:
            True if the definition was removed, False otherwise
        """
        for i, definition in enumerate(self.alert_definitions):
            if definition.name == name:
                self.alert_definitions.pop(i)
                return True
        return False
    
    def check_alerts(self) -> List[QualityAlert]:
        """Check all alert definitions against recent metrics.
        
        Returns:
            List of new alerts triggered
        """
        new_alerts = []
        
        for definition in self.alert_definitions:
            # Skip if in cooldown
            if definition.in_cooldown:
                logger.debug(f"Alert '{definition.name}' is in cooldown, skipping")
                continue
                
            # Build filter for metrics query
            filter_dict = {}
            if definition.resource_types:
                filter_dict["resource_type"] = definition.resource_types
            if definition.pipeline_stages:
                filter_dict["pipeline_stage"] = definition.pipeline_stages
            
            # Calculate time range
            now = datetime.utcnow()
            start_time = now - timedelta(hours=definition.lookback_hours)
            time_range = {"start": start_time, "end": now}
            
            # Query metrics
            metrics = self.metrics_collector.query_metrics(
                metric_pattern=definition.metric_pattern,
                filter_dict=filter_dict,
                time_range=time_range
            )
            
            # Skip if no metrics
            if not metrics:
                logger.debug(f"No metrics found for alert '{definition.name}'")
                continue
            
            # Calculate aggregate and sample size
            values = [m["value"] for m in metrics]
            aggregate_value = sum(values) / len(values)
            sample_size = len(values)
            
            # Evaluate alert condition
            if definition.evaluate(aggregate_value, sample_size):
                # Create alert details
                details = {
                    "metric_count": sample_size,
                    "lookback_hours": definition.lookback_hours,
                    "resource_types": definition.resource_types,
                    "pipeline_stages": definition.pipeline_stages,
                    "metrics": metrics[:10]  # Include first 10 metrics as examples
                }
                
                # Create and record alert
                alert = QualityAlert(
                    definition=definition,
                    metric_value=aggregate_value,
                    details=details
                )
                self.alerts.append(alert)
                new_alerts.append(alert)
                
                # Mark definition as triggered
                definition.mark_triggered()
                
                logger.info(f"Quality alert triggered: {definition.name}")
        
        return new_alerts
    
    def get_active_alerts(self) -> List[QualityAlert]:
        """Get all active alerts.
        
        Returns:
            List of active alerts
        """
        return [alert for alert in self.alerts if alert.status == AlertStatus.ACTIVE]
    
    def get_alerts_by_status(self, status: AlertStatus) -> List[QualityAlert]:
        """Get alerts by status.
        
        Args:
            status: Alert status to filter by
            
        Returns:
            List of alerts with the specified status
        """
        return [alert for alert in self.alerts if alert.status == status]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[QualityAlert]:
        """Get alerts by severity.
        
        Args:
            severity: Alert severity to filter by
            
        Returns:
            List of alerts with the specified severity
        """
        return [alert for alert in self.alerts if alert.severity == severity]
    
    def get_alerts_by_category(self, category: AlertCategory) -> List[QualityAlert]:
        """Get alerts by category.
        
        Args:
            category: Alert category to filter by
            
        Returns:
            List of alerts with the specified category
        """
        return [alert for alert in self.alerts if alert.category == category]
    
    def resolve_alert(self, alert_id: str, note: str = None) -> bool:
        """Resolve an alert.
        
        Args:
            alert_id: ID of the alert to resolve
            note: Optional resolution note
            
        Returns:
            True if the alert was resolved, False otherwise
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolve(note)
                return True
        return False
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            
        Returns:
            True if the alert was acknowledged, False otherwise
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledge()
                return True
        return False
    
    def silence_alert(self, alert_id: str) -> bool:
        """Silence an alert.
        
        Args:
            alert_id: ID of the alert to silence
            
        Returns:
            True if the alert was silenced, False otherwise
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.silence()
                return True
        return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of all alerts.
        
        Returns:
            Dictionary with alert summary
        """
        by_status = {status.value: 0 for status in AlertStatus}
        by_severity = {severity.value: 0 for severity in AlertSeverity}
        by_category = {category.value: 0 for category in AlertCategory}
        
        for alert in self.alerts:
            by_status[alert.status] += 1
            by_severity[alert.severity] += 1
            by_category[alert.category] += 1
        
        return {
            "total_alerts": len(self.alerts),
            "active_alerts": len(self.get_active_alerts()),
            "by_status": by_status,
            "by_severity": by_severity,
            "by_category": by_category,
            "generated_at": datetime.utcnow().isoformat()
        }


# Common threshold functions
def threshold_lt(threshold: float) -> Callable[[float], bool]:
    """Create a less-than threshold function.
    
    Args:
        threshold: The threshold value
        
    Returns:
        Function that returns True if value < threshold
    """
    return lambda value: value < threshold

def threshold_lte(threshold: float) -> Callable[[float], bool]:
    """Create a less-than-or-equal threshold function.
    
    Args:
        threshold: The threshold value
        
    Returns:
        Function that returns True if value <= threshold
    """
    return lambda value: value <= threshold

def threshold_gt(threshold: float) -> Callable[[float], bool]:
    """Create a greater-than threshold function.
    
    Args:
        threshold: The threshold value
        
    Returns:
        Function that returns True if value > threshold
    """
    return lambda value: value > threshold

def threshold_gte(threshold: float) -> Callable[[float], bool]:
    """Create a greater-than-or-equal threshold function.
    
    Args:
        threshold: The threshold value
        
    Returns:
        Function that returns True if value >= threshold
    """
    return lambda value: value >= threshold

def threshold_eq(threshold: float, tolerance: float = 0.0001) -> Callable[[float], bool]:
    """Create an approximately-equal threshold function.
    
    Args:
        threshold: The threshold value
        tolerance: Tolerance for floating-point comparison
        
    Returns:
        Function that returns True if value ≈ threshold
    """
    return lambda value: abs(value - threshold) <= tolerance

def threshold_between(
    lower: float,
    upper: float,
    inclusive: bool = True
) -> Callable[[float], bool]:
    """Create a between threshold function.
    
    Args:
        lower: Lower bound
        upper: Upper bound
        inclusive: Whether bounds are inclusive
        
    Returns:
        Function that returns True if value is between bounds
    """
    if inclusive:
        return lambda value: lower <= value <= upper
    else:
        return lambda value: lower < value < upper

def threshold_not_between(
    lower: float,
    upper: float,
    inclusive: bool = True
) -> Callable[[float], bool]:
    """Create a not-between threshold function.
    
    Args:
        lower: Lower bound
        upper: Upper bound
        inclusive: Whether bounds are inclusive
        
    Returns:
        Function that returns True if value is not between bounds
    """
    if inclusive:
        return lambda value: not (lower <= value <= upper)
    else:
        return lambda value: not (lower < value < upper)


# Predefined alert definitions
def create_standard_alert_definitions() -> List[QualityAlertDefinition]:
    """Create a list of standard alert definitions.
    
    Returns:
        List of standard alert definitions
    """
    return [
        # Completeness alerts
        QualityAlertDefinition(
            name="Low Completeness Alert",
            description="Data completeness score is below threshold",
            metric_pattern="data_quality.*.completeness",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.COMPLETENESS,
            threshold_fn=threshold_lt(0.8),
            min_sample_size=10,
            lookback_hours=24
        ),
        
        # Validation alerts
        QualityAlertDefinition(
            name="High Validation Failure Rate",
            description="Validation failure rate exceeds threshold",
            metric_pattern="validation.batch.*.validation_rate",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.VALIDATION,
            threshold_fn=threshold_lt(0.9),
            min_sample_size=10,
            lookback_hours=24
        ),
        
        # Timeliness alerts
        QualityAlertDefinition(
            name="Low Data Timeliness",
            description="Data timeliness score is below threshold",
            metric_pattern="data_quality.*.timeliness",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.TIMELINESS,
            threshold_fn=threshold_lt(0.7),
            min_sample_size=10,
            lookback_hours=24
        ),
        
        # Pipeline alerts
        QualityAlertDefinition(
            name="High Error Rate",
            description="Error rate exceeds threshold in pipeline",
            metric_pattern="pipeline.*.error_rate",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.PIPELINE,
            threshold_fn=threshold_gt(0.05),
            min_sample_size=100,
            lookback_hours=24
        ),
        
        # Extraction alerts
        QualityAlertDefinition(
            name="Low Extraction Success Rate",
            description="Extraction success rate is below threshold",
            metric_pattern="extraction.*.success_rate",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.EXTRACTION,
            threshold_fn=threshold_lt(0.95),
            min_sample_size=10,
            lookback_hours=24
        ),
        
        # Transformation alerts
        QualityAlertDefinition(
            name="High Transformation Failure Rate",
            description="Transformation failure rate exceeds threshold",
            metric_pattern="transformation.*.failure_rate",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.TRANSFORMATION,
            threshold_fn=threshold_gt(0.05),
            min_sample_size=10,
            lookback_hours=24
        )
    ] 