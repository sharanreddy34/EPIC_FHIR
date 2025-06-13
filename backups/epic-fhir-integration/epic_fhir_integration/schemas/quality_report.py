"""
Schema definitions for data quality reports.

This module provides Pydantic models for representing quality reports,
metrics, validation results, and alerts.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class QualityDimension(str, Enum):
    """Quality dimensions tracked in reports."""
    COMPLETENESS = "completeness"
    CONFORMANCE = "conformance"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    ACCURACY = "accuracy"


class ValidationSeverity(str, Enum):
    """Validation issue severities."""
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class ValidationCategory(str, Enum):
    """Categories of validation issues."""
    STRUCTURE = "structure"
    REFERENCE = "reference"
    PROFILE = "profile"
    VALUE = "value"
    INVARIANT = "invariant"
    TERMINOLOGY = "terminology"
    SECURITY = "security"
    UNKNOWN = "unknown"


class ValidationType(str, Enum):
    """Types of validation performed."""
    SCHEMA = "schema"
    PROFILE = "profile"
    BUSINESS_RULE = "business"
    TERMINOLOGY = "terminology"
    REFERENCE = "reference"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    """Alert severities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert statuses."""
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


class TrendDirection(str, Enum):
    """Trend directions."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


class ValidationIssue(BaseModel):
    """Model for validation issues."""
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    location: Optional[str] = None
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """Model for validation results."""
    resource_type: str
    resource_id: Optional[str] = None
    is_valid: bool
    validation_type: ValidationType
    issues: List[ValidationIssue] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_stage: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchValidationResult(BaseModel):
    """Model for batch validation results."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_stage: str
    validation_type: ValidationType
    resources_total: int
    resources_valid: int
    validation_rate: float
    total_issues: int
    issues_per_resource: float
    by_resource_type: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QualityAlert(BaseModel):
    """Model for quality alerts."""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    metric_pattern: str
    metric_value: float
    details: Dict[str, Any]
    timestamp: datetime
    status: AlertStatus
    resolution_timestamp: Optional[datetime] = None
    resolution_note: Optional[str] = None


class QualityMetricEntry(BaseModel):
    """Model for a quality metric time series entry."""
    timestamp: str
    value: float


class DimensionStats(BaseModel):
    """Model for dimension statistics."""
    mean: float
    min: float
    max: float
    median: float
    std_dev: float
    count: int


class ResourceTypeStats(BaseModel):
    """Model for resource type statistics."""
    dimensions: Dict[str, DimensionStats]
    overall: Optional[DimensionStats] = None


class TrendInfo(BaseModel):
    """Model for trend information."""
    slope: float
    intercept: float
    r_squared: float
    direction: TrendDirection
    initial_value: float
    final_value: float
    change: float
    percent_change: float


class QualityReport(BaseModel):
    """Model for a quality report."""
    report_name: str
    generated_at: datetime
    filter: Dict[str, Any]
    time_range: Optional[Dict[str, Optional[str]]] = None
    interval: str
    metrics_count: int
    tracked_metrics: Dict[str, Dict[str, List[QualityMetricEntry]]]
    statistics: Dict[str, Any]
    trends: Dict[str, Any]
    charts: Optional[List[str]] = None


class ComparisonResult(BaseModel):
    """Model for quality comparison results."""
    mean_change: float
    mean_percent_change: float
    min_change: float
    max_change: float
    direction: TrendDirection


class QualityComparison(BaseModel):
    """Model for quality comparison between time periods."""
    generated_at: datetime
    baseline_time_range: Dict[str, str]
    comparison_time_range: Dict[str, str]
    filter: Dict[str, Any]
    interval: str
    baseline: Dict[str, Any]
    comparison: Dict[str, Any]
    comparison_results: Dict[str, Any]


class AlertSummary(BaseModel):
    """Model for alert summary."""
    total_alerts: int
    active_alerts: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    generated_at: str


class QualityActionPlan(BaseModel):
    """Model for quality improvement action plan."""
    id: str
    name: str
    description: str
    created_at: datetime
    status: str
    priority: str
    owner: Optional[str] = None
    target_date: Optional[datetime] = None
    related_alerts: List[str] = Field(default_factory=list)
    related_dimensions: List[QualityDimension] = Field(default_factory=list)
    related_resource_types: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    progress: float = 0.0
    notes: List[Dict[str, Any]] = Field(default_factory=list) 