"""
Data Quality Assessment Module.

This module provides tools for assessing the quality of FHIR resources
across multiple dimensions including completeness, conformance, consistency,
and timeliness.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.validation.validator import FHIRValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class QualityDimension:
    """A dimension of data quality with a score and details."""
    
    name: str             # Name of the dimension
    score: float          # Score from 0.0 to 1.0
    details: Dict[str, Any]  # Detailed information about the score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the quality dimension to a dictionary.
        
        Returns:
            Dictionary representation of the quality dimension.
        """
        return {
            "name": self.name,
            "score": self.score,
            "details": self.details,
        }


@dataclass
class QualityReport:
    """A comprehensive quality report for FHIR resources."""
    
    resource_type: str                   # Type of the assessed resources
    resource_count: int                  # Number of resources assessed
    overall_score: float                 # Overall quality score (0.0 to 1.0)
    dimensions: List[QualityDimension]   # Quality dimensions
    timestamp: str                       # ISO-formatted timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the quality report to a dictionary.
        
        Returns:
            Dictionary representation of the quality report.
        """
        return {
            "resource_type": self.resource_type,
            "resource_count": self.resource_count,
            "overall_score": self.overall_score,
            "dimensions": [dim.to_dict() for dim in self.dimensions],
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert the quality report to a JSON string.
        
        Returns:
            JSON string representation of the quality report.
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def save(self, filepath: str) -> None:
        """Save the quality report to a file.
        
        Args:
            filepath: Path to save the report to.
        """
        with open(filepath, "w") as f:
            f.write(self.to_json())


class DataQualityAssessor:
    """Assessor for FHIR data quality.
    
    This class provides methods for assessing the quality of FHIR resources
    across multiple dimensions.
    """
    
    def __init__(
        self,
        adapter: Optional[FHIRPathAdapter] = None,
        validator: Optional[FHIRValidator] = None,
    ):
        """Initialize the data quality assessor.
        
        Args:
            adapter: FHIRPathAdapter instance for extracting data from resources.
            validator: FHIRValidator instance for validating resources.
        """
        self.adapter = adapter or FHIRPathAdapter()
        self.validator = validator or FHIRValidator()
        
        # Default weights for quality dimensions
        self.dimension_weights = {
            "completeness": 0.25,
            "conformance": 0.25,
            "consistency": 0.25,
            "timeliness": 0.25,
        }
    
    def set_dimension_weights(self, weights: Dict[str, float]) -> None:
        """Set the weights for quality dimensions.
        
        Args:
            weights: Dictionary mapping dimension names to weights.
                Weights should sum to 1.0.
        """
        # Normalize weights if they don't sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            normalized = {k: v / total for k, v in weights.items()}
            logger.warning(f"Weights don't sum to 1.0, normalizing: {weights} -> {normalized}")
            weights = normalized
            
        self.dimension_weights = weights
    
    def assess_quality(
        self,
        resources: List[Dict[str, Any]],
        required_fields: Optional[Dict[str, List[str]]] = None,
    ) -> QualityReport:
        """Assess the quality of FHIR resources.
        
        Args:
            resources: List of FHIR resources to assess.
            required_fields: Dictionary mapping resource types to lists of
                required fields. Fields can be FHIRPath expressions.
                
        Returns:
            Quality report.
        """
        if not resources:
            logger.warning("No resources to assess")
            return QualityReport(
                resource_type="unknown",
                resource_count=0,
                overall_score=0.0,
                dimensions=[],
                timestamp=datetime.now().isoformat(),
            )
            
        # Determine resource type
        resource_type = resources[0].get("resourceType", "unknown")
        
        # Get default required fields if not specified
        if not required_fields:
            required_fields = self._get_default_required_fields(resource_type)
            
        # Assess each dimension
        start_time = time.time()
        completeness = self._assess_completeness(resources, required_fields.get(resource_type, []))
        conformance = self._assess_conformance(resources)
        consistency = self._assess_consistency(resources, resource_type)
        timeliness = self._assess_timeliness(resources)
        
        # Calculate overall score
        dimensions = [
            QualityDimension("completeness", completeness["score"], completeness),
            QualityDimension("conformance", conformance["score"], conformance),
            QualityDimension("consistency", consistency["score"], consistency),
            QualityDimension("timeliness", timeliness["score"], timeliness),
        ]
        
        overall_score = sum(
            dim.score * self.dimension_weights.get(dim.name, 0.25)
            for dim in dimensions
        )
        
        # Create the report
        report = QualityReport(
            resource_type=resource_type,
            resource_count=len(resources),
            overall_score=overall_score,
            dimensions=dimensions,
            timestamp=datetime.now().isoformat(),
        )
        
        duration = time.time() - start_time
        logger.info(f"Quality assessment completed in {duration:.2f}s for {len(resources)} resources")
        logger.info(f"Overall quality score: {overall_score:.2f}")
        
        return report
    
    def _get_default_required_fields(self, resource_type: str) -> Dict[str, List[str]]:
        """Get default required fields for common resource types.
        
        Args:
            resource_type: FHIR resource type.
            
        Returns:
            Dictionary mapping resource types to lists of required fields.
        """
        # Default required fields for common resource types
        defaults = {
            "Patient": [
                "id",
                "name",
                "gender",
                "birthDate",
            ],
            "Observation": [
                "id",
                "status",
                "code",
                "subject",
                "effectiveDateTime",
                "valueQuantity",
            ],
            "Encounter": [
                "id",
                "status",
                "class",
                "subject",
                "period",
            ],
            "Condition": [
                "id",
                "clinicalStatus",
                "code",
                "subject",
                "onsetDateTime",
            ],
            "MedicationRequest": [
                "id",
                "status",
                "intent",
                "medicationCodeableConcept",
                "subject",
                "authoredOn",
            ],
        }
        
        # Return defaults or empty list if resource type not found
        return defaults
    
    def _assess_completeness(
        self,
        resources: List[Dict[str, Any]],
        required_fields: List[str],
    ) -> Dict[str, Any]:
        """Assess the completeness of FHIR resources.
        
        Args:
            resources: List of FHIR resources to assess.
            required_fields: List of required fields. Fields can be FHIRPath expressions.
            
        Returns:
            Dictionary with completeness score and details.
        """
        # Count total required fields
        total_fields = len(required_fields) * len(resources)
        if total_fields == 0:
            logger.warning("No required fields specified for completeness assessment")
            return {"score": 1.0, "missing_fields": {}}
            
        # Count missing fields
        missing_fields = {}
        for field in required_fields:
            missing_count = 0
            
            for resource in resources:
                try:
                    # Check if the field exists using FHIRPath
                    if not self.adapter.exists(resource, field):
                        missing_count += 1
                except Exception as e:
                    logger.error(f"Error checking field '{field}': {str(e)}")
                    missing_count += 1
                    
            if missing_count > 0:
                missing_fields[field] = missing_count
                
        # Calculate completeness score
        total_missing = sum(missing_fields.values())
        completeness_score = 1.0 - (total_missing / total_fields) if total_fields > 0 else 1.0
        
        return {
            "score": completeness_score,
            "missing_fields": missing_fields,
            "total_fields": total_fields,
            "total_missing": total_missing,
        }
    
    def _assess_conformance(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assess the conformance of FHIR resources to profiles.
        
        Args:
            resources: List of FHIR resources to assess.
            
        Returns:
            Dictionary with conformance score and details.
        """
        # Validate resources
        if not self.validator:
            logger.warning("No validator available for conformance assessment")
            return {"score": 0.0, "validation_results": []}
            
        validation_results = self.validator.validate_batch(resources)
        
        # Calculate conformance score
        valid_count = sum(1 for result in validation_results if result.is_valid)
        conformance_score = valid_count / len(resources) if resources else 1.0
        
        # Count issues by severity
        issue_counts = {
            "error": sum(len(result.get_errors()) for result in validation_results),
            "warning": sum(len(result.get_warnings()) for result in validation_results),
            "information": sum(len(result.get_information()) for result in validation_results),
        }
        
        return {
            "score": conformance_score,
            "valid_count": valid_count,
            "total_count": len(resources),
            "issue_counts": issue_counts,
            "validation_results": [result.to_dict() for result in validation_results],
        }
    
    def _assess_consistency(
        self,
        resources: List[Dict[str, Any]],
        resource_type: str,
    ) -> Dict[str, Any]:
        """Assess the consistency of FHIR resources.
        
        Args:
            resources: List of FHIR resources to assess.
            resource_type: FHIR resource type.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Consistency checks depend on resource type
        consistency_checks = {
            "Patient": self._check_patient_consistency,
            "Observation": self._check_observation_consistency,
            "Encounter": self._check_encounter_consistency,
            "Condition": self._check_condition_consistency,
            "MedicationRequest": self._check_medication_request_consistency,
        }
        
        # Use the appropriate check function or a generic one
        check_function = consistency_checks.get(resource_type, self._check_generic_consistency)
        return check_function(resources)
    
    def _check_patient_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of Patient resources.
        
        Args:
            resources: List of Patient resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Check for consistent name format
        inconsistencies = []
        
        # Check if all patients have consistent name structure
        for resource in resources:
            # Check if name is an array
            name = resource.get("name", [])
            if not isinstance(name, list):
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "name is not an array",
                })
                continue
                
            # Check if all names have given and family
            for name_item in name:
                if not isinstance(name_item, dict):
                    inconsistencies.append({
                        "id": resource.get("id"),
                        "issue": "name item is not an object",
                    })
                    continue
                    
                if "given" not in name_item:
                    inconsistencies.append({
                        "id": resource.get("id"),
                        "issue": "name missing given",
                    })
                    
                if "family" not in name_item:
                    inconsistencies.append({
                        "id": resource.get("id"),
                        "issue": "name missing family",
                    })
        
        # Calculate consistency score
        consistency_score = 1.0 - (len(inconsistencies) / len(resources)) if resources else 1.0
        
        return {
            "score": consistency_score,
            "inconsistencies": inconsistencies,
            "total_count": len(resources),
            "inconsistent_count": len(inconsistencies),
        }
    
    def _check_observation_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of Observation resources.
        
        Args:
            resources: List of Observation resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Check for consistent value structure
        inconsistencies = []
        
        for resource in resources:
            # Check that only one value[x] is present
            value_fields = [f for f in resource.keys() if f.startswith("value")]
            if len(value_fields) > 1:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": f"multiple value fields: {value_fields}",
                })
                
            # Check that code has proper structure
            code = resource.get("code", {})
            if not isinstance(code, dict) or "coding" not in code:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "code missing coding array",
                })
                
            # Check subject reference format
            subject = resource.get("subject", {})
            if not isinstance(subject, dict) or "reference" not in subject:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "subject missing reference",
                })
        
        # Calculate consistency score
        consistency_score = 1.0 - (len(inconsistencies) / len(resources)) if resources else 1.0
        
        return {
            "score": consistency_score,
            "inconsistencies": inconsistencies,
            "total_count": len(resources),
            "inconsistent_count": len(inconsistencies),
        }
    
    def _check_encounter_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of Encounter resources.
        
        Args:
            resources: List of Encounter resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Check for consistent period structure
        inconsistencies = []
        
        for resource in resources:
            # Check period has start and end
            period = resource.get("period", {})
            if not isinstance(period, dict):
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "period is not an object",
                })
                continue
                
            if "start" not in period:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "period missing start",
                })
                
            # Check subject reference format
            subject = resource.get("subject", {})
            if not isinstance(subject, dict) or "reference" not in subject:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": "subject missing reference",
                })
        
        # Calculate consistency score
        consistency_score = 1.0 - (len(inconsistencies) / len(resources)) if resources else 1.0
        
        return {
            "score": consistency_score,
            "inconsistencies": inconsistencies,
            "total_count": len(resources),
            "inconsistent_count": len(inconsistencies),
        }
    
    def _check_condition_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of Condition resources.
        
        Args:
            resources: List of Condition resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Generic implementation for now
        return self._check_generic_consistency(resources)
    
    def _check_medication_request_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of MedicationRequest resources.
        
        Args:
            resources: List of MedicationRequest resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # Generic implementation for now
        return self._check_generic_consistency(resources)
    
    def _check_generic_consistency(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Check consistency of generic FHIR resources.
        
        Args:
            resources: List of FHIR resources.
            
        Returns:
            Dictionary with consistency score and details.
        """
        # For generic resources, just check if all resources have the same fields
        if not resources:
            return {
                "score": 1.0,
                "inconsistencies": [],
                "total_count": 0,
                "inconsistent_count": 0,
            }
            
        # Get the fields from the first resource
        first_resource = resources[0]
        expected_fields = set(first_resource.keys())
        
        # Check that all resources have the same fields
        inconsistencies = []
        for resource in resources[1:]:
            resource_fields = set(resource.keys())
            
            # Check for missing fields
            missing_fields = expected_fields - resource_fields
            if missing_fields:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": f"missing fields: {missing_fields}",
                })
                
            # Check for extra fields
            extra_fields = resource_fields - expected_fields
            if extra_fields:
                inconsistencies.append({
                    "id": resource.get("id"),
                    "issue": f"unexpected fields: {extra_fields}",
                })
        
        # Calculate consistency score
        consistency_score = 1.0 - (len(inconsistencies) / len(resources)) if resources else 1.0
        
        return {
            "score": consistency_score,
            "inconsistencies": inconsistencies,
            "total_count": len(resources),
            "inconsistent_count": len(inconsistencies),
        }
    
    def _assess_timeliness(
        self,
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assess the timeliness of FHIR resources.
        
        Args:
            resources: List of FHIR resources to assess.
            
        Returns:
            Dictionary with timeliness score and details.
        """
        # Check for meta.lastUpdated timestamp
        timeliness_issues = []
        now = datetime.now()
        
        for resource in resources:
            # Check if meta.lastUpdated exists
            meta = resource.get("meta", {})
            if not isinstance(meta, dict) or "lastUpdated" not in meta:
                timeliness_issues.append({
                    "id": resource.get("id"),
                    "issue": "missing meta.lastUpdated",
                })
                continue
                
            # Check if lastUpdated is recent
            try:
                last_updated = datetime.fromisoformat(meta["lastUpdated"].replace("Z", "+00:00"))
                days_ago = (now - last_updated).days
                
                if days_ago > 365:  # More than a year old
                    timeliness_issues.append({
                        "id": resource.get("id"),
                        "issue": f"lastUpdated is {days_ago} days old",
                        "days_ago": days_ago,
                    })
            except (ValueError, TypeError) as e:
                timeliness_issues.append({
                    "id": resource.get("id"),
                    "issue": f"invalid lastUpdated format: {meta['lastUpdated']}",
                })
        
        # Calculate timeliness score
        timeliness_score = 1.0 - (len(timeliness_issues) / len(resources)) if resources else 1.0
        
        return {
            "score": timeliness_score,
            "timeliness_issues": timeliness_issues,
            "total_count": len(resources),
            "issues_count": len(timeliness_issues),
        } 