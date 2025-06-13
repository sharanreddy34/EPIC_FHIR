"""
Validation metrics module for tracking FHIR validation results.

This module provides functionality for capturing, tracking, and reporting
on FHIR validation results across different phases of the pipeline.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from epic_fhir_integration.metrics.collector import MetricsCollector

logger = logging.getLogger(__name__)

class ValidationSeverity(str, Enum):
    """Enumeration of validation issue severities."""
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"

class ValidationCategory(str, Enum):
    """Common categories of validation issues."""
    STRUCTURE = "structure"  # Structural issues with the resource
    REFERENCE = "reference"  # Issues with resource references
    PROFILE = "profile"      # Profile conformance issues
    VALUE = "value"          # Value constraint issues
    INVARIANT = "invariant"  # Constraint violations
    TERMINOLOGY = "terminology"  # Issues with codes/terminologies
    SECURITY = "security"    # Security-related issues
    CONSISTENCY = "consistency" # Issues related to consistency between fields
    UNKNOWN = "unknown"      # Uncategorized issues

class ValidationType(str, Enum):
    """Types of validation performed."""
    SCHEMA = "schema"            # Basic JSON Schema validation
    PROFILE = "profile"          # FHIR profile validation
    BUSINESS_RULE = "business"   # Custom business rule validation
    TERMINOLOGY = "terminology"  # Terminology validation
    REFERENCE = "reference"      # Reference validation
    CUSTOM = "custom"            # Custom validation

class ValidationMetricsRecorder:
    """Records metrics related to FHIR resource validation."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize the validation metrics recorder.
        
        Args:
            metrics_collector: Optional metrics collector to record metrics
        """
        self.metrics_collector = metrics_collector
        
    def record_validation_result(
        self,
        resource_type: str,
        is_valid: bool,
        validation_type: Union[ValidationType, str],
        pipeline_stage: str,
        issues: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a validation result.
        
        Args:
            resource_type: The FHIR resource type
            is_valid: Whether the resource is valid
            validation_type: Type of validation performed
            pipeline_stage: Stage in the pipeline (e.g., "bronze", "silver", "gold")
            issues: Optional list of validation issues
            metadata: Additional metadata about the validation
        """
        if not self.metrics_collector:
            logger.debug("No metrics collector available, skipping validation metric recording")
            return
            
        issues = issues or []
        metadata = metadata or {}
        
        # Record overall validation success/failure
        self.metrics_collector.record_metric(
            f"validation.{resource_type}.{validation_type}.valid",
            1.0 if is_valid else 0.0,
            {
                "pipeline_stage": pipeline_stage,
                "resource_type": resource_type,
                "validation_type": validation_type,
                **metadata
            }
        )
        
        # Record issue count
        self.metrics_collector.record_metric(
            f"validation.{resource_type}.{validation_type}.issue_count",
            len(issues),
            {
                "pipeline_stage": pipeline_stage,
                "resource_type": resource_type,
                "validation_type": validation_type,
                **metadata
            }
        )
        
        # Record statistics by severity
        severity_counts = self._count_issues_by_severity(issues)
        for severity, count in severity_counts.items():
            self.metrics_collector.record_metric(
                f"validation.{resource_type}.{validation_type}.{severity}_count",
                count,
                {
                    "pipeline_stage": pipeline_stage,
                    "resource_type": resource_type,
                    "validation_type": validation_type,
                    "severity": severity,
                    **metadata
                }
            )
            
        # Record statistics by category
        category_counts = self._count_issues_by_category(issues)
        for category, count in category_counts.items():
            self.metrics_collector.record_metric(
                f"validation.{resource_type}.{validation_type}.category.{category}_count",
                count,
                {
                    "pipeline_stage": pipeline_stage,
                    "resource_type": resource_type,
                    "validation_type": validation_type,
                    "category": category,
                    **metadata
                }
            )
    
    def record_batch_validation_results(
        self,
        results: List[Dict[str, Any]],
        validation_type: Union[ValidationType, str],
        pipeline_stage: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record validation results for a batch of resources.
        
        Args:
            results: List of validation results, each with:
                - resource_type: The FHIR resource type
                - is_valid: Whether the resource is valid
                - issues: Optional list of validation issues
            validation_type: Type of validation performed
            pipeline_stage: Stage in the pipeline
            metadata: Additional metadata about the validation
            
        Returns:
            Dictionary with summary statistics
        """
        metadata = metadata or {}
        
        if not results:
            return {"error": "No validation results provided"}
            
        # Track statistics
        total_resources = len(results)
        valid_resources = sum(1 for r in results if r.get("is_valid", False))
        resource_types = {}
        all_issues = []
        
        # Process individual results
        for result in results:
            resource_type = result.get("resource_type", "Unknown")
            is_valid = result.get("is_valid", False)
            issues = result.get("issues", [])
            
            # Track by resource type
            if resource_type not in resource_types:
                resource_types[resource_type] = {"total": 0, "valid": 0, "issues": []}
            
            resource_types[resource_type]["total"] += 1
            if is_valid:
                resource_types[resource_type]["valid"] += 1
            resource_types[resource_type]["issues"].extend(issues)
            all_issues.extend(issues)
            
            # Record individual result
            self.record_validation_result(
                resource_type=resource_type,
                is_valid=is_valid,
                validation_type=validation_type,
                pipeline_stage=pipeline_stage,
                issues=issues,
                metadata=metadata
            )
        
        # Record batch-level metrics
        if self.metrics_collector:
            # Overall validation rate
            self.metrics_collector.record_metric(
                f"validation.batch.{validation_type}.validation_rate",
                valid_resources / total_resources if total_resources > 0 else 0,
                {
                    "pipeline_stage": pipeline_stage,
                    "validation_type": validation_type,
                    "resource_count": total_resources,
                    **metadata
                }
            )
            
            # Issue rate
            issue_count = len(all_issues)
            self.metrics_collector.record_metric(
                f"validation.batch.{validation_type}.issue_rate",
                issue_count / total_resources if total_resources > 0 else 0,
                {
                    "pipeline_stage": pipeline_stage,
                    "validation_type": validation_type,
                    "resource_count": total_resources,
                    **metadata
                }
            )
        
        # Create summary statistics
        type_stats = {}
        for resource_type, stats in resource_types.items():
            validation_rate = stats["valid"] / stats["total"] if stats["total"] > 0 else 0
            issue_count = len(stats["issues"])
            
            type_stats[resource_type] = {
                "validation_rate": validation_rate,
                "resources_valid": stats["valid"],
                "resources_total": stats["total"],
                "issue_count": issue_count,
                "issues_per_resource": issue_count / stats["total"] if stats["total"] > 0 else 0
            }
        
        # Return summary
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_stage": pipeline_stage,
            "validation_type": validation_type,
            "resources_total": total_resources,
            "resources_valid": valid_resources,
            "validation_rate": valid_resources / total_resources if total_resources > 0 else 0,
            "total_issues": len(all_issues),
            "issues_per_resource": len(all_issues) / total_resources if total_resources > 0 else 0,
            "by_resource_type": type_stats,
            "metadata": metadata
        }
    
    def _count_issues_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count validation issues by severity.
        
        Args:
            issues: List of validation issues
            
        Returns:
            Dictionary with counts by severity
        """
        severity_counts = {
            ValidationSeverity.ERROR.value: 0,
            ValidationSeverity.WARNING.value: 0,
            ValidationSeverity.INFORMATION.value: 0
        }
        
        for issue in issues:
            severity = issue.get("severity", "unknown").lower()
            if severity == "fatal":
                severity = ValidationSeverity.ERROR.value
                
            if severity in severity_counts:
                severity_counts[severity] += 1
            else:
                # Default unknown severities to warnings
                severity_counts[ValidationSeverity.WARNING.value] += 1
                
        return severity_counts
    
    def _count_issues_by_category(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count validation issues by category.
        
        Args:
            issues: List of validation issues
            
        Returns:
            Dictionary with counts by category
        """
        category_counts = {category.value: 0 for category in ValidationCategory}
        
        for issue in issues:
            # Try to determine category from the issue details
            category = self._categorize_issue(issue)
            category_counts[category] += 1
                
        return category_counts
    
    def _categorize_issue(self, issue: Dict[str, Any]) -> str:
        """Determine the category of a validation issue.
        
        Args:
            issue: Validation issue details
            
        Returns:
            Category string
        """
        # Use explicit category if available
        if "category" in issue:
            return issue["category"]
            
        # Check common patterns in the message or code
        message = issue.get("message", "").lower()
        code = issue.get("code", "").lower()
        
        # Check for structure issues
        if any(term in message for term in ["structure", "property", "required", "missing"]):
            return ValidationCategory.STRUCTURE.value
            
        # Check for reference issues
        if any(term in message for term in ["reference", "unknown target", "target"]):
            return ValidationCategory.REFERENCE.value
            
        # Check for profile issues
        if any(term in message for term in ["profile", "conform"]):
            return ValidationCategory.PROFILE.value
            
        # Check for value issues
        if any(term in message for term in ["value", "invalid", "minimum", "maximum"]):
            return ValidationCategory.VALUE.value
            
        # Check for invariant issues
        if any(term in message for term in ["invariant", "constraint", "violated"]):
            return ValidationCategory.INVARIANT.value
            
        # Check for terminology issues
        if any(term in message for term in ["terminology", "code", "system", "binding"]):
            return ValidationCategory.TERMINOLOGY.value
            
        # Check for security issues
        if any(term in message for term in ["security", "access", "permission"]):
            return ValidationCategory.SECURITY.value
            
        # Check for consistency issues
        if any(term in message for term in ["consistency", "inconsistent", "conflict"]):
            return ValidationCategory.CONSISTENCY.value
            
        # Default to unknown
        return ValidationCategory.UNKNOWN.value


class ValidationReporter:
    """Generates reports from validation metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize the validation reporter.
        
        Args:
            metrics_collector: Metrics collector with recorded metrics
        """
        self.metrics_collector = metrics_collector
        
    def generate_validation_summary(
        self,
        resource_types: Optional[List[str]] = None,
        validation_types: Optional[List[Union[ValidationType, str]]] = None,
        pipeline_stages: Optional[List[str]] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """Generate a validation summary report.
        
        Args:
            resource_types: Optional list of resource types to include
            validation_types: Optional list of validation types to include
            pipeline_stages: Optional list of pipeline stages to include
            time_range: Optional time range for metrics
            
        Returns:
            Dictionary with validation summary statistics
        """
        # Convert enum values to strings if needed
        if validation_types:
            validation_types = [
                vt.value if hasattr(vt, "value") else vt 
                for vt in validation_types
            ]
        
        # Build filter for metrics
        filter_dict = {}
        if resource_types:
            filter_dict["resource_type"] = resource_types
        if validation_types:
            filter_dict["validation_type"] = validation_types
        if pipeline_stages:
            filter_dict["pipeline_stage"] = pipeline_stages
            
        # Get relevant metrics for validation rates
        valid_metrics = self.metrics_collector.query_metrics(
            metric_pattern="validation.*.*.valid",
            filter_dict=filter_dict,
            time_range=time_range
        )
        
        # Get relevant metrics for issue counts
        issue_metrics = self.metrics_collector.query_metrics(
            metric_pattern="validation.*.*.issue_count",
            filter_dict=filter_dict,
            time_range=time_range
        )
        
        # Process metrics into summary statistics
        summary = self._process_validation_metrics(valid_metrics, issue_metrics)
        
        # Add timestamp and query parameters to the report
        summary["generated_at"] = datetime.utcnow().isoformat()
        summary["query_parameters"] = {
            "resource_types": resource_types,
            "validation_types": validation_types,
            "pipeline_stages": pipeline_stages,
            "time_range": {
                "start": time_range["start"].isoformat() if time_range and "start" in time_range else None,
                "end": time_range["end"].isoformat() if time_range and "end" in time_range else None
            } if time_range else None
        }
        
        return summary
    
    def _process_validation_metrics(
        self,
        valid_metrics: List[Dict[str, Any]],
        issue_metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process validation metrics into a summary report.
        
        Args:
            valid_metrics: Metrics for validation success/failure
            issue_metrics: Metrics for issue counts
            
        Returns:
            Dictionary with summary statistics
        """
        # Group metrics by resource type, validation type, and pipeline stage
        grouped_valid_metrics = {}
        for metric in valid_metrics:
            resource_type = metric["labels"].get("resource_type", "unknown")
            validation_type = metric["labels"].get("validation_type", "unknown")
            pipeline_stage = metric["labels"].get("pipeline_stage", "unknown")
            
            key = (resource_type, validation_type, pipeline_stage)
            if key not in grouped_valid_metrics:
                grouped_valid_metrics[key] = []
            
            grouped_valid_metrics[key].append(metric)
        
        # Group issue metrics similarly
        grouped_issue_metrics = {}
        for metric in issue_metrics:
            resource_type = metric["labels"].get("resource_type", "unknown")
            validation_type = metric["labels"].get("validation_type", "unknown")
            pipeline_stage = metric["labels"].get("pipeline_stage", "unknown")
            
            key = (resource_type, validation_type, pipeline_stage)
            if key not in grouped_issue_metrics:
                grouped_issue_metrics[key] = []
            
            grouped_issue_metrics[key].append(metric)
        
        # Initialize summary structure
        summary = {
            "overall": {
                "total_validations": 0,
                "valid_count": 0,
                "validation_rate": 0,
                "total_issues": 0,
                "issues_per_validation": 0
            },
            "by_resource_type": {},
            "by_validation_type": {},
            "by_pipeline_stage": {},
            "detailed": {}
        }
        
        # Process grouped metrics
        for key, metrics in grouped_valid_metrics.items():
            resource_type, validation_type, pipeline_stage = key
            
            # Calculate validation statistics
            valid_count = sum(1 for m in metrics if m["value"] > 0.5)
            total_count = len(metrics)
            validation_rate = valid_count / total_count if total_count > 0 else 0
            
            # Get corresponding issue metrics
            issue_metrics_for_key = grouped_issue_metrics.get(key, [])
            total_issues = sum(m["value"] for m in issue_metrics_for_key)
            issues_per_validation = total_issues / total_count if total_count > 0 else 0
            
            # Update overall statistics
            summary["overall"]["total_validations"] += total_count
            summary["overall"]["valid_count"] += valid_count
            summary["overall"]["total_issues"] += total_issues
            
            # Update resource type statistics
            if resource_type not in summary["by_resource_type"]:
                summary["by_resource_type"][resource_type] = {
                    "total_validations": 0,
                    "valid_count": 0,
                    "validation_rate": 0,
                    "total_issues": 0,
                    "issues_per_validation": 0
                }
            summary["by_resource_type"][resource_type]["total_validations"] += total_count
            summary["by_resource_type"][resource_type]["valid_count"] += valid_count
            summary["by_resource_type"][resource_type]["total_issues"] += total_issues
            
            # Update validation type statistics
            if validation_type not in summary["by_validation_type"]:
                summary["by_validation_type"][validation_type] = {
                    "total_validations": 0,
                    "valid_count": 0,
                    "validation_rate": 0,
                    "total_issues": 0,
                    "issues_per_validation": 0
                }
            summary["by_validation_type"][validation_type]["total_validations"] += total_count
            summary["by_validation_type"][validation_type]["valid_count"] += valid_count
            summary["by_validation_type"][validation_type]["total_issues"] += total_issues
            
            # Update pipeline stage statistics
            if pipeline_stage not in summary["by_pipeline_stage"]:
                summary["by_pipeline_stage"][pipeline_stage] = {
                    "total_validations": 0,
                    "valid_count": 0,
                    "validation_rate": 0,
                    "total_issues": 0,
                    "issues_per_validation": 0
                }
            summary["by_pipeline_stage"][pipeline_stage]["total_validations"] += total_count
            summary["by_pipeline_stage"][pipeline_stage]["valid_count"] += valid_count
            summary["by_pipeline_stage"][pipeline_stage]["total_issues"] += total_issues
            
            # Add detailed statistics
            detailed_key = f"{resource_type}.{validation_type}.{pipeline_stage}"
            summary["detailed"][detailed_key] = {
                "resource_type": resource_type,
                "validation_type": validation_type,
                "pipeline_stage": pipeline_stage,
                "total_validations": total_count,
                "valid_count": valid_count,
                "validation_rate": validation_rate,
                "total_issues": total_issues,
                "issues_per_validation": issues_per_validation
            }
        
        # Calculate rates for overall statistics
        if summary["overall"]["total_validations"] > 0:
            summary["overall"]["validation_rate"] = (
                summary["overall"]["valid_count"] / 
                summary["overall"]["total_validations"]
            )
            summary["overall"]["issues_per_validation"] = (
                summary["overall"]["total_issues"] / 
                summary["overall"]["total_validations"]
            )
        
        # Calculate rates for resource type statistics
        for resource_type, stats in summary["by_resource_type"].items():
            if stats["total_validations"] > 0:
                stats["validation_rate"] = stats["valid_count"] / stats["total_validations"]
                stats["issues_per_validation"] = stats["total_issues"] / stats["total_validations"]
        
        # Calculate rates for validation type statistics
        for validation_type, stats in summary["by_validation_type"].items():
            if stats["total_validations"] > 0:
                stats["validation_rate"] = stats["valid_count"] / stats["total_validations"]
                stats["issues_per_validation"] = stats["total_issues"] / stats["total_validations"]
        
        # Calculate rates for pipeline stage statistics
        for pipeline_stage, stats in summary["by_pipeline_stage"].items():
            if stats["total_validations"] > 0:
                stats["validation_rate"] = stats["valid_count"] / stats["total_validations"]
                stats["issues_per_validation"] = stats["total_issues"] / stats["total_validations"]
        
        return summary 

# -----------------------------------------------------------------------------
# Backwards-compatibility shim
# -----------------------------------------------------------------------------

class ValidationMetrics:  # pragma: no cover
    """Lightweight container for validation batch summaries.

    Current dashboards only expect a `.to_dict()` method or attribute access to
    basic fields such as `timestamp`, `pipeline_stage`, etc.  We provide a very
    small wrapper so that dashboards do not crash when the full implementation
    is not present.
    """

    def __init__(self, data: dict):
        self._data = data or {}
        # expose keys as attributes for simple dot access
        for k, v in self._data.items():
            setattr(self, k, v)

    def to_dict(self) -> dict:  # noqa: D401 – simple
        """Return the underlying dictionary representation."""
        return self._data 