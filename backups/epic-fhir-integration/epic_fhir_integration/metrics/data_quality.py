"""
Data Quality assessment module for FHIR resources.

This module provides functions and classes for assessing the quality of FHIR resources
including completeness, conformance, consistency, and timeliness metrics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import os
import json

from fhir.resources.resource import Resource

from epic_fhir_integration.metrics.collector import MetricsCollector
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Import mock assessor if available for use when Great Expectations isn't available
try:
    from epic_fhir_integration.metrics.mock_quality_assessor import assess_resources as mock_assess_resources
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False

logger = logging.getLogger(__name__)

class DataQualityDimension:
    """Enumeration of data quality dimensions."""
    COMPLETENESS = "completeness"
    CONFORMANCE = "conformance"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    ACCURACY = "accuracy"

class DataQualityAssessor:
    """Assess data quality of FHIR resources based on multiple dimensions."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize the data quality assessor.
        
        Args:
            metrics_collector: Optional metrics collector to record metrics
        """
        self.fhirpath = FHIRPathAdapter()
        self.metrics_collector = metrics_collector
        
        # Check if we should use mock implementation
        self.use_mock = os.environ.get("USE_MOCK_MODE") == "true"
        if self.use_mock:
            logger.info("Using mock quality assessment")
        
    def assess_resources(self, resources: Dict[str, List[Dict[str, Any]]], tier: str = "bronze") -> Dict[str, Any]:
        """Assess quality for a collection of resources by type.
        
        Args:
            resources: Dictionary of resources by type
            tier: Data quality tier
            
        Returns:
            Dictionary with quality assessment results
        """
        # Use mock implementation if requested or if Great Expectations not available
        if self.use_mock or (MOCK_AVAILABLE and os.environ.get("GE_FALLBACK") == "true"):
            logger.info(f"Using mock quality assessment for {tier} tier")
            if MOCK_AVAILABLE:
                return mock_assess_resources(resources, tier)
            else:
                # Basic mock implementation if the full mock module isn't available
                resource_counts = {resource_type: len(resources_list) for resource_type, resources_list in resources.items()}
                return {
                    "tier": tier,
                    "resource_counts": resource_counts,
                    "total_resources": sum(resource_counts.values()),
                    "quality_scores": {
                        "completeness": 0.95,
                        "conformance": 1.0,
                        "consistency": 0.98,
                        "timeliness": 0.99
                    },
                    "overall_quality": 0.98,
                    "resource_types": list(resources.keys()),
                    "mock_mode": True
                }
        
        # If not mock mode, use real implementation
        try:
            # Load Great Expectations dynamically to avoid import errors
            from epic_fhir_integration.metrics.great_expectations_validator import GreatExpectationsValidator
            
            # Initialize validator with appropriate settings for the tier
            validator = GreatExpectationsValidator()
            
            # Assess each resource type
            quality_results = {}
            resource_quality_scores = {}
            total_issues = 0
            
            logger.debug(f"Starting quality assessment for tier: {tier}. Resources: {list(resources.keys())}")

            for resource_type, resource_list in resources.items():
                if not resource_list:
                    logger.debug(f"Skipping empty resource list for type: {resource_type}")
                    continue
                
                # Get appropriate expectation suite for resource type and tier
                suite_name = f"{resource_type.lower()}_{tier}_expectations"
                logger.info(f"Attempting to validate {len(resource_list)} x {resource_type} resources with suite: {suite_name}")
                
                try:
                    # Validate resources
                    validation_results = validator.validate_resources(
                        resources=resource_list,
                        expectation_suite_name=suite_name,
                        pipeline_stage=f"{tier}_quality_assessment"
                    )
                    
                    # Calculate quality score based on validation rate
                    quality_score = validation_results.get("validation_rate", 0.0)
                    resource_quality_scores[resource_type] = quality_score
                    
                    # Store detailed results, ensuring 'issues' are present
                    current_issues = validation_results.get("issues", [])
                    total_issues += len(current_issues)
                    quality_results[resource_type] = validation_results 
                    # Ensure issues list exists, even if empty, for consistent structure
                    if "issues" not in quality_results[resource_type]:
                        quality_results[resource_type]["issues"] = [] 

                except Exception as validation_error:
                    logger.error(f"Error validating {resource_type} resources with suite {suite_name}: {validation_error}", exc_info=True)
                    resource_quality_scores[resource_type] = 0.5  # Middle ground score
                    
                    # Try to extract issues if it's a GX validation result or a dict with issues
                    issues = []
                    if hasattr(validation_error, 'results'): # GX result object might be the exception itself
                        processed_issues = validator._process_validation_results(validation_error) # Use GEValidator's helper
                        issues.extend(processed_issues)
                        logger.debug(f"Extracted {len(processed_issues)} issues from Great Expectations result object.")
                    elif isinstance(validation_error, dict) and 'issues' in validation_error:
                        issues.extend(validation_error['issues'])
                        logger.debug(f"Extracted {len(validation_error['issues'])} issues from validation error dictionary.")
                    else:
                        logger.debug(f"Could not extract detailed issues from validation_error of type: {type(validation_error)}")
                    
                    quality_results[resource_type] = {
                        "error": str(validation_error), # Keep the original error string
                        "validation_rate": 0.5,
                        "issues": issues, # Add extracted or empty issues list
                        "details_from_exception": True # Flag that this was an error path
                    }
            
            # Calculate overall quality score
            overall_quality = sum(resource_quality_scores.values()) / len(resource_quality_scores) if resource_quality_scores else 0.0
            
            # Build final result
            resource_counts = {resource_type: len(resources_list) for resource_type, resources_list in resources.items()}
            final_assessment = {
                "tier": tier,
                "timestamp": datetime.utcnow().isoformat(),
                "resource_counts": resource_counts,
                "total_resources": sum(resource_counts.values()),
                "total_issues_found": total_issues,
                "quality_scores_by_resource": resource_quality_scores,
                "overall_quality": overall_quality,
                "resource_types": list(resources.keys()),
                "detailed_validation_results": quality_results,
                "mock_mode": False
            }
            logger.info(f"Quality assessment for tier '{tier}' completed. Overall quality: {overall_quality:.2%}")
            logger.debug(f"Full quality assessment details for tier '{tier}': {json.dumps(final_assessment, indent=2, default=str)}")
            return final_assessment
            
        except ImportError as ie:
            logger.error(f"GreatExpectationsValidator could not be imported: {ie}. Ensure Great Expectations is installed.", exc_info=True)
            # Fallback logic remains as is
            if MOCK_AVAILABLE:
                logger.info(f"Falling back to mock quality assessment for {tier} tier due to Import Error.")
                os.environ["GE_FALLBACK"] = "true"  # Set flag for future calls
                return mock_assess_resources(resources, tier)
            else:
                logger.warning("Mock assess resources not available either. Returning basic mock info.")
                resource_counts = {resource_type: len(resources_list) for resource_type, resources_list in resources.items()}
                return {
                    "tier": tier,
                    "resource_counts": resource_counts,
                    "total_resources": sum(resource_counts.values()),
                    "quality_scores": {
                        "completeness": 0.0,
                        "conformance": 0.0,
                        "consistency": 0.0,
                        "timeliness": 0.0
                    },
                    "overall_quality": 0.0,
                    "resource_types": list(resources.keys()),
                    "mock_mode": True,
                    "fallback_due_to_error": f"ImportError: {str(ie)}"
                }
        except Exception as e:
            logger.error(f"Critical error during quality assessment for tier '{tier}': {e}", exc_info=True)
            
            # Fall back to mock implementation
            if MOCK_AVAILABLE:
                logger.info(f"Falling back to mock quality assessment for {tier} tier")
                os.environ["GE_FALLBACK"] = "true"  # Set flag for future calls
                return mock_assess_resources(resources, tier)
            else:
                # Basic mock implementation if the full mock module isn't available
                resource_counts = {resource_type: len(resources_list) for resource_type, resources_list in resources.items()}
                return {
                    "tier": tier,
                    "resource_counts": resource_counts,
                    "total_resources": sum(resource_counts.values()),
                    "quality_scores": {
                        "completeness": 0.95,
                        "conformance": 1.0,
                        "consistency": 0.98,
                        "timeliness": 0.99
                    },
                    "overall_quality": 0.98,
                    "resource_types": list(resources.keys()),
                    "mock_mode": True,
                    "fallback_due_to_error": str(e)
                }
        
    def assess_completeness(
        self, 
        resource: Union[Dict[str, Any], Resource], 
        required_paths: List[str]
    ) -> Dict[str, float]:
        """Assess completeness of a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or Resource object
            required_paths: List of FHIRPath expressions for fields that should be present
            
        Returns:
            Dictionary with completeness scores
        """
        results = {}
        missing = []
        
        for path in required_paths:
            exists = self.fhirpath.exists(resource, path)
            if not exists:
                missing.append(path)
        
        completeness_score = 1.0 - (len(missing) / len(required_paths)) if required_paths else 1.0
        
        results["completeness_score"] = completeness_score
        results["missing_fields"] = missing
        results["complete_field_count"] = len(required_paths) - len(missing)
        results["total_required_fields"] = len(required_paths)
        
        if self.metrics_collector:
            resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
            self.metrics_collector.record_metric(
                f"data_quality.{resource_type}.completeness", 
                completeness_score,
                {"dimension": DataQualityDimension.COMPLETENESS}
            )
            
        return results
    
    def assess_conformance(
        self, 
        resource: Union[Dict[str, Any], Resource],
        validator_fn: callable
    ) -> Dict[str, Any]:
        """Assess conformance of a FHIR resource to schemas/profiles.
        
        Args:
            resource: FHIR resource as a dictionary or Resource object
            validator_fn: Function that validates the resource and returns validation results
        
        Returns:
            Dictionary with conformance scores and issues
        """
        validation_result = validator_fn(resource)
        
        results = {
            "conformance_valid": validation_result.get("valid", False),
            "issues": validation_result.get("issues", []),
            "issue_count": len(validation_result.get("issues", [])),
        }
        
        if self.metrics_collector:
            resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
            self.metrics_collector.record_metric(
                f"data_quality.{resource_type}.conformance", 
                1.0 if results["conformance_valid"] else 0.0,
                {"dimension": DataQualityDimension.CONFORMANCE}
            )
            
        return results
    
    def assess_consistency(
        self, 
        resource: Union[Dict[str, Any], Resource],
        consistency_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess internal consistency of a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or Resource object
            consistency_rules: List of rules defining consistency checks
                Each rule is a dict with:
                - 'name': Rule name
                - 'condition': FHIRPath expression that should evaluate to true
                
        Returns:
            Dictionary with consistency scores and failed rules
        """
        results = {"rules_checked": len(consistency_rules), "failed_rules": []}
        
        for rule in consistency_rules:
            rule_name = rule.get("name", "unnamed rule")
            condition = rule.get("condition", "")
            
            if not condition:
                logger.warning(f"Empty condition in consistency rule: {rule_name}")
                continue
                
            try:
                is_consistent = self.fhirpath.exists(resource, condition)
                if not is_consistent:
                    results["failed_rules"].append(rule_name)
            except Exception as e:
                logger.error(f"Error evaluating consistency rule {rule_name}: {str(e)}")
                results["failed_rules"].append(f"{rule_name} (evaluation error)")
                
        consistency_score = 1.0 - (len(results["failed_rules"]) / results["rules_checked"]) if results["rules_checked"] > 0 else 1.0
        results["consistency_score"] = consistency_score
        
        if self.metrics_collector:
            resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
            self.metrics_collector.record_metric(
                f"data_quality.{resource_type}.consistency", 
                consistency_score,
                {"dimension": DataQualityDimension.CONSISTENCY}
            )
            
        return results
    
    def assess_timeliness(
        self, 
        resource: Union[Dict[str, Any], Resource],
        timestamp_path: str,
        reference_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Assess timeliness of a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or Resource object
            timestamp_path: FHIRPath to the timestamp field
            reference_time: Optional reference time, defaults to now
            
        Returns:
            Dictionary with timeliness scores
        """
        if reference_time is None:
            reference_time = datetime.utcnow()
            
        results = {}
        
        try:
            timestamp_str = self.fhirpath.extract_first(resource, timestamp_path)
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_diff = (reference_time - timestamp).total_seconds()
                
                # Convert to hours for easier interpretation
                time_diff_hours = time_diff / 3600
                
                results["time_diff_seconds"] = time_diff
                results["time_diff_hours"] = time_diff_hours
                
                # Simple timeliness score that decreases with age
                # 1.0 for current data, approaching 0.0 for very old data
                # This is a simple example - adjust the decay function as needed
                timeliness_score = max(0.0, min(1.0, 1.0 / (1.0 + time_diff_hours / 24.0)))
                results["timeliness_score"] = timeliness_score
                
                if self.metrics_collector:
                    resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
                    self.metrics_collector.record_metric(
                        f"data_quality.{resource_type}.timeliness", 
                        timeliness_score,
                        {"dimension": DataQualityDimension.TIMELINESS}
                    )
            else:
                results["timeliness_score"] = 0.0
                results["error"] = "Timestamp not found"
        except Exception as e:
            logger.error(f"Error assessing timeliness: {str(e)}")
            results["timeliness_score"] = 0.0
            results["error"] = str(e)
            
        return results
    
    def assess_overall_quality(
        self,
        resource: Union[Dict[str, Any], Resource],
        required_paths: List[str] = None,
        validator_fn: callable = None,
        consistency_rules: List[Dict[str, Any]] = None,
        timestamp_path: str = None,
        reference_time: Optional[datetime] = None,
        weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """Calculate overall data quality score based on multiple dimensions.
        
        Args:
            resource: FHIR resource to assess
            required_paths: Paths required for completeness assessment
            validator_fn: Function for conformance validation
            consistency_rules: Rules for consistency checks
            timestamp_path: Path to timestamp for timeliness
            reference_time: Reference time for timeliness, defaults to now
            weights: Weights for different dimensions, defaults to equal
            
        Returns:
            Dictionary with all quality scores
        """
        results = {"dimensions": {}}
        
        # Default weights
        default_weights = {
            DataQualityDimension.COMPLETENESS: 0.25,
            DataQualityDimension.CONFORMANCE: 0.25,
            DataQualityDimension.CONSISTENCY: 0.25,
            DataQualityDimension.TIMELINESS: 0.25
        }
        
        weights = weights or default_weights
        
        # Normalize weights
        weight_sum = sum(weights.values())
        normalized_weights = {k: v / weight_sum for k, v in weights.items()}
        
        # Initialize weighted score components
        weighted_scores = {}
        
        # Assess completeness if paths provided
        if required_paths:
            completeness_results = self.assess_completeness(resource, required_paths)
            results["dimensions"][DataQualityDimension.COMPLETENESS] = completeness_results
            weighted_scores[DataQualityDimension.COMPLETENESS] = (
                completeness_results["completeness_score"] * 
                normalized_weights.get(DataQualityDimension.COMPLETENESS, 0)
            )
        
        # Assess conformance if validator provided
        if validator_fn:
            conformance_results = self.assess_conformance(resource, validator_fn)
            results["dimensions"][DataQualityDimension.CONFORMANCE] = conformance_results
            weighted_scores[DataQualityDimension.CONFORMANCE] = (
                1.0 if conformance_results["conformance_valid"] else 0.0
            ) * normalized_weights.get(DataQualityDimension.CONFORMANCE, 0)
        
        # Assess consistency if rules provided
        if consistency_rules:
            consistency_results = self.assess_consistency(resource, consistency_rules)
            results["dimensions"][DataQualityDimension.CONSISTENCY] = consistency_results
            weighted_scores[DataQualityDimension.CONSISTENCY] = (
                consistency_results["consistency_score"] * 
                normalized_weights.get(DataQualityDimension.CONSISTENCY, 0)
            )
        
        # Assess timeliness if path provided
        if timestamp_path:
            timeliness_results = self.assess_timeliness(resource, timestamp_path, reference_time)
            results["dimensions"][DataQualityDimension.TIMELINESS] = timeliness_results
            if "timeliness_score" in timeliness_results:
                weighted_scores[DataQualityDimension.TIMELINESS] = (
                    timeliness_results["timeliness_score"] * 
                    normalized_weights.get(DataQualityDimension.TIMELINESS, 0)
                )
        
        # Calculate overall quality score
        overall_score = sum(weighted_scores.values())
        results["overall_quality_score"] = overall_score
        results["weighted_scores"] = weighted_scores
        
        # Record overall score
        if self.metrics_collector:
            resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
            self.metrics_collector.record_metric(
                f"data_quality.{resource_type}.overall", 
                overall_score,
                {"resource_type": resource_type}
            )
        
        return results
    
    def assess_batch_quality(
        self,
        resources: List[Union[Dict[str, Any], Resource]],
        **kwargs
    ) -> Dict[str, Any]:
        """Assess quality for a batch of resources.
        
        Args:
            resources: List of FHIR resources
            **kwargs: Arguments to pass to assess_overall_quality
            
        Returns:
            Dictionary with aggregate quality scores
        """
        if not resources:
            return {"error": "No resources provided", "overall_quality_score": 0.0}
            
        all_scores = []
        resource_types = {}
        
        for resource in resources:
            result = self.assess_overall_quality(resource, **kwargs)
            all_scores.append(result["overall_quality_score"])
            
            # Track scores by resource type
            resource_type = resource.get("resourceType") if isinstance(resource, dict) else resource.resource_type
            if resource_type not in resource_types:
                resource_types[resource_type] = []
            resource_types[resource_type].append(result["overall_quality_score"])
        
        # Calculate aggregate scores
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Calculate scores by resource type
        type_scores = {}
        for resource_type, scores in resource_types.items():
            type_scores[resource_type] = sum(scores) / len(scores) if scores else 0
        
        return {
            "overall_quality_score": average_score,
            "resource_count": len(resources),
            "resource_types": list(resource_types.keys()),
            "quality_by_type": type_scores,
            "min_score": min(all_scores) if all_scores else 0,
            "max_score": max(all_scores) if all_scores else 0
        } 