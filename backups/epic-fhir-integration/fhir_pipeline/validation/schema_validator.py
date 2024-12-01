"""
Schema validation for FHIR resources.
"""

from dataclasses import dataclass
from typing import List, Optional

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    valid_count: int = 0
    invalid_count: int = 0


class SchemaValidator:
    """
    Validates that a DataFrame matches an expected schema.
    
    Checks field names, types, and nullability to ensure data quality.
    """
    
    def __init__(self, expected_schema: StructType):
        """
        Initialize the schema validator.
        
        Args:
            expected_schema: The expected schema to validate against
        """
        self.expected_schema = expected_schema
    
    def validate(self, df: DataFrame) -> ValidationResult:
        """
        Validate that the DataFrame matches the expected schema.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        actual_schema = df.schema
        errors = []
        
        # Check for missing fields
        for field in self.expected_schema.fields:
            if field.name not in [f.name for f in actual_schema.fields]:
                errors.append(f"Missing field: {field.name}")
                continue
                
            # Get the actual field with the same name
            actual_field = next(f for f in actual_schema.fields if f.name == field.name)
            
            # Check data type
            if str(field.dataType) != str(actual_field.dataType):
                errors.append(f"Field {field.name} has incorrect type: expected {field.dataType}, got {actual_field.dataType}")
            
            # Check nullability if the expected field is not nullable
            if not field.nullable and actual_field.nullable:
                errors.append(f"Field {field.name} should not be nullable")
        
        # Return validation result
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors) 