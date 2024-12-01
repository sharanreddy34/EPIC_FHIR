"""
FHIR-specific validation for resources.
"""

import json
from typing import Dict, Any, List

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, expr, udf
from pyspark.sql.types import BooleanType, StringType

from fhir_pipeline.validation.schema_validator import ValidationResult


class FHIRValidator:
    """
    Validates FHIR resources according to the FHIR specification.
    
    Performs validation on resource structure, required fields,
    and value constraints according to the FHIR standard.
    """
    
    def __init__(self, resource_type: str):
        """
        Initialize the FHIR validator.
        
        Args:
            resource_type: The FHIR resource type to validate (e.g., "Patient", "Observation")
        """
        self.resource_type = resource_type
        self._load_validation_rules()
    
    def _load_validation_rules(self):
        """Load validation rules for the resource type."""
        # This would typically load from a JSON schema or rules file
        # For this implementation, we'll define some basic rules in-memory
        self.required_fields = self._get_required_fields(self.resource_type)
        self.value_constraints = self._get_value_constraints(self.resource_type)
    
    def _get_required_fields(self, resource_type: str) -> List[str]:
        """Get required fields for a resource type."""
        # Basic required fields by resource type
        required_fields = {
            "Patient": ["id", "resourceType", "name"],
            "Observation": ["id", "resourceType", "status", "code", "subject"],
            "Practitioner": ["id", "resourceType", "name"],
            "Encounter": ["id", "resourceType", "status", "class", "subject"],
            # Add more resource types as needed
        }
        return required_fields.get(resource_type, ["id", "resourceType"])
    
    def _get_value_constraints(self, resource_type: str) -> Dict[str, List[str]]:
        """Get value constraints for fields in a resource type."""
        # Basic value constraints by resource type and field
        value_constraints = {
            "Patient": {
                "gender": ["male", "female", "other", "unknown"]
            },
            "Observation": {
                "status": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]
            },
            "Encounter": {
                "status": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"]
            }
        }
        return value_constraints.get(resource_type, {})
    
    def validate(self, df: DataFrame) -> ValidationResult:
        """
        Validate the DataFrame against FHIR rules.
        
        Args:
            df: DataFrame containing FHIR resources
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        invalid_rows = 0
        total_rows = df.count()
        
        # Check required fields
        for field in self.required_fields:
            if field not in df.columns:
                errors.append(f"Required field missing from schema: {field}")
                continue
                
            # Count records with null values in required fields
            null_count = df.filter(col(field).isNull()).count()
            if null_count > 0:
                errors.append(f"Required field '{field}' has {null_count} null values")
                invalid_rows += null_count
        
        # Check value constraints
        for field, allowed_values in self.value_constraints.items():
            if field not in df.columns:
                continue
                
            # Count records with invalid values
            invalid_count = df.filter(
                ~col(field).isNull() & ~col(field).isin(allowed_values)
            ).count()
            
            if invalid_count > 0:
                errors.append(
                    f"Field '{field}' has {invalid_count} values outside allowed values: {allowed_values}"
                )
                invalid_rows += invalid_count
        
        # Adjust invalid count in case we double-counted some rows
        invalid_rows = min(invalid_rows, total_rows)
        valid_rows = total_rows - invalid_rows
        
        return ValidationResult(
            is_valid=len(errors) == 0 and invalid_rows == 0,
            errors=errors,
            valid_count=valid_rows,
            invalid_count=invalid_rows
        )
    
    def get_validation_report(self, result: ValidationResult) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            result: ValidationResult from validation
            
        Returns:
            Formatted validation report as a string
        """
        report = [
            f"FHIR Validation Report for {self.resource_type}",
            f"----------------------------------------",
            f"Valid records: {result.valid_count}",
            f"Invalid records: {result.invalid_count}",
            f"Validation passed: {result.is_valid}",
            f"",
            f"Validation errors:",
        ]
        
        if not result.errors:
            report.append("  None")
        else:
            for i, error in enumerate(result.errors, 1):
                report.append(f"  {i}. {error}")
        
        return "\n".join(report) 