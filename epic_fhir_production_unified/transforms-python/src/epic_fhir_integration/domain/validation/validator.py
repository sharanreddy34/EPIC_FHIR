"""
FHIR validation module for Epic FHIR integration.

This module provides validation capabilities for FHIR resources.
"""

import enum
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationLevel(enum.Enum):
    """Validation levels for FHIR resources."""
    
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of validating a FHIR resource."""
    
    resource_type: str
    resource_id: Optional[str]
    level: ValidationLevel
    message: str
    location: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the validation result.
        """
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "level": self.level.value,
            "message": self.message,
            "location": self.location,
            "details": self.details,
        }


class FHIRValidator:
    """Validator for FHIR resources."""
    
    def __init__(self, fhir_version: str = "R4"):
        """Initialize a FHIR validator.
        
        Args:
            fhir_version: FHIR version to validate against.
        """
        self.fhir_version = fhir_version
        logger.info("Initialized FHIR validator", fhir_version=fhir_version)
    
    def validate(self, resource: Union[Dict[str, Any], str]) -> List[ValidationResult]:
        """Validate a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or JSON string.
            
        Returns:
            List of validation results.
        """
        # Convert string to dictionary if needed
        if isinstance(resource, str):
            try:
                resource = json.loads(resource)
            except json.JSONDecodeError as e:
                return [
                    ValidationResult(
                        resource_type="Unknown",
                        resource_id=None,
                        level=ValidationLevel.ERROR,
                        message=f"Invalid JSON: {str(e)}",
                    )
                ]
        
        # Get resource type and ID
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id")
        
        # Basic validation results
        results = []
        
        # Check for required fields
        if not resource_type or resource_type == "Unknown":
            results.append(
                ValidationResult(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    level=ValidationLevel.ERROR,
                    message="Missing required field: resourceType",
                )
            )
        
        # For Patient resources, check for additional required fields
        if resource_type == "Patient":
            # Check for identifier
            identifiers = resource.get("identifier", [])
            if not identifiers:
                results.append(
                    ValidationResult(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        level=ValidationLevel.ERROR,
                        message="Missing required field: identifier",
                    )
                )
            
            # Check for at least one name
            names = resource.get("name", [])
            if not names:
                results.append(
                    ValidationResult(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        level=ValidationLevel.ERROR,
                        message="Missing required field: name",
                    )
                )
            
            # Check for gender
            if "gender" not in resource:
                results.append(
                    ValidationResult(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        level=ValidationLevel.WARNING,
                        message="Missing recommended field: gender",
                    )
                )
        
        return results
    
    def validate_batch(self, resources: List[Union[Dict[str, Any], str]]) -> List[Dict[str, Any]]:
        """Validate a batch of FHIR resources.
        
        Args:
            resources: List of FHIR resources as dictionaries or JSON strings.
            
        Returns:
            List of validation results as dictionaries.
        """
        results = []
        
        for resource in resources:
            validation_results = self.validate(resource)
            for result in validation_results:
                results.append(result.to_dict())
        
        return results 