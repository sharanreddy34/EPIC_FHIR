import json
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, Tuple

import pyspark
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, udf, lit, struct
from pyspark.sql.types import StringType, BooleanType, ArrayType, StructType, StructField

try:
    from pydantic import BaseModel, ValidationError, Field, validator
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    logging.warning("Pydantic not available; validation functionality limited")

logger = logging.getLogger(__name__)

# Issue levels
LEVEL_FATAL = "fatal"
LEVEL_WARNING = "warning"
LEVEL_INFO = "info"

class ValidationIssue:
    """Represents a validation issue found during validation."""
    
    def __init__(
        self,
        level: str,
        resource_type: str,
        resource_id: str,
        field: str,
        message: str,
        validation_rule: str
    ):
        """
        Initialize a validation issue.
        
        Args:
            level: Severity level (fatal, warning, info)
            resource_type: FHIR resource type
            resource_id: ID of the resource with issue
            field: The field path with the issue
            message: Description of the issue
            validation_rule: The rule that was violated
        """
        self.level = level
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.field = field
        self.message = message
        self.validation_rule = validation_rule
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "level": self.level,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "field": self.field,
            "message": self.message,
            "validation_rule": self.validation_rule,
            "timestamp": self.timestamp
        }

def _create_schema_for_resource(resource_type: str) -> Optional[Type[BaseModel]]:
    """
    Create or load a Pydantic model for validating a specific resource type.
    
    Args:
        resource_type: FHIR resource type
        
    Returns:
        Pydantic model class or None if no schema available
    """
    if not HAS_PYDANTIC:
        return None
    
    # Simple example schemas - in a real implementation, these would be
    # comprehensive, loaded from external schemas, or auto-generated
    if resource_type == "Patient":
        class PatientSchema(BaseModel):
            patient_id: str
            birth_date: Optional[str] = None
            gender: Optional[str] = None
            name_text: Optional[str] = None
            
            @validator('gender')
            def gender_values(cls, v):
                if v and v not in ['male', 'female', 'other', 'unknown']:
                    raise ValueError(f"Gender must be one of: male, female, other, unknown, got {v}")
                return v
                
            @validator('birth_date')
            def birth_date_format(cls, v):
                if v:
                    try:
                        datetime.fromisoformat(v.replace('Z', '+00:00'))
                    except ValueError:
                        raise ValueError(f"Invalid ISO date format: {v}")
                return v
        
        return PatientSchema
    
    elif resource_type == "Observation":
        class ObservationSchema(BaseModel):
            observation_id: str
            patient_id: str
            issued_datetime: Optional[str] = None
            
            @validator('issued_datetime')
            def issued_datetime_format(cls, v):
                if v:
                    try:
                        datetime.fromisoformat(v.replace('Z', '+00:00'))
                    except ValueError:
                        raise ValueError(f"Invalid ISO datetime format: {v}")
                return v
        
        return ObservationSchema
    
    elif resource_type == "Encounter":
        class EncounterSchema(BaseModel):
            encounter_id: str
            patient_id: str
            status: Optional[str] = None
            
            @validator('status')
            def status_values(cls, v):
                valid_statuses = [
                    'planned', 'arrived', 'triaged', 'in-progress', 
                    'onleave', 'finished', 'cancelled'
                ]
                if v and v not in valid_statuses:
                    raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
                return v
        
        return EncounterSchema
    
    # Return None if no schema available for this resource type
    return None

def _validate_row(
    row_dict: Dict[str, Any], 
    schema_cls: Type[BaseModel],
    resource_type: str
) -> List[ValidationIssue]:
    """
    Validate a single row using a Pydantic model.
    
    Args:
        row_dict: Row data as dictionary
        schema_cls: Pydantic model class to use for validation
        resource_type: FHIR resource type
        
    Returns:
        List of validation issues found
    """
    issues = []
    
    try:
        # Validate against schema
        schema_cls(**row_dict)
        # No issues found
    except ValidationError as e:
        # Extract validation errors
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            issues.append(ValidationIssue(
                level=LEVEL_FATAL,
                resource_type=resource_type,
                resource_id=row_dict.get("id", "unknown"),
                field=field_path,
                message=error["msg"],
                validation_rule="schema_validation"
            ))
    except Exception as e:
        # Catch any other exceptions during validation
        issues.append(ValidationIssue(
            level=LEVEL_FATAL,
            resource_type=resource_type,
            resource_id=row_dict.get("id", "unknown"),
            field="_all",
            message=f"Unexpected error during validation: {str(e)}",
            validation_rule="schema_validation"
        ))
    
    return issues

class ValidationContext:
    """
    Context for validating transformed FHIR resources.
    
    Validates rows against Pydantic schemas and custom rules,
    tracks validation statistics, and writes issues to output.
    """
    
    def __init__(
        self, 
        resource_type: str, 
        dataframe: DataFrame,
        sample_rate: float = 0.1,  # Sample 10% for performance
        output_path: Optional[str] = None
    ):
        """
        Initialize the validation context.
        
        Args:
            resource_type: FHIR resource type being validated
            dataframe: DataFrame containing the resources to validate
            sample_rate: Percentage of rows to validate (0.0-1.0)
            output_path: Path to write validation issues
        """
        self.resource_type = resource_type
        self.dataframe = dataframe
        self.sample_rate = sample_rate
        self.output_path = output_path or f"/metrics/validation_results/{resource_type.lower()}"
        
        # Get the validation schema for this resource type
        self.schema_cls = _create_schema_for_resource(resource_type)
        
        # Validation statistics
        self.total_rows = dataframe.count()
        self.sampled_rows = 0
        self.failed_rows = 0
        self.fatal_issues = 0
        self.warning_issues = 0
        self.info_issues = 0
        
        # List to collect validation issues for reporting
        self.issues: List[ValidationIssue] = []
    
    def validate(self) -> DataFrame:
        """
        Validate the DataFrame against schema and rules.
        
        Returns:
            The input DataFrame, unmodified
        
        Raises:
            ValueError: If fatal validation issues are found
        """
        logger.info(f"Validating {self.resource_type} data")
        
        if not HAS_PYDANTIC:
            logger.warning("Pydantic not available, skipping schema validation")
            return self.dataframe
        
        if not self.schema_cls:
            logger.warning(f"No validation schema for {self.resource_type}, skipping validation")
            return self.dataframe
        
        # Sample rows for validation (for large datasets)
        if self.sample_rate < 1.0:
            sample_df = self.dataframe.sample(withReplacement=False, fraction=self.sample_rate)
        else:
            sample_df = self.dataframe
        
        # Convert to Rows for easier validation
        sample_rows = sample_df.collect()
        self.sampled_rows = len(sample_rows)
        
        # Validate each sampled row
        for row in sample_rows:
            row_dict = row.asDict()
            row_issues = _validate_row(row_dict, self.schema_cls, self.resource_type)
            
            for issue in row_issues:
                if issue.level == LEVEL_FATAL:
                    self.fatal_issues += 1
                elif issue.level == LEVEL_WARNING:
                    self.warning_issues += 1
                elif issue.level == LEVEL_INFO:
                    self.info_issues += 1
            
            if row_issues:
                self.failed_rows += 1
                self.issues.extend(row_issues)
        
        # Report validation results
        logger.info(f"Validation results for {self.resource_type}:")
        logger.info(f"  Total rows: {self.total_rows}")
        logger.info(f"  Sampled rows: {self.sampled_rows}")
        logger.info(f"  Failed rows: {self.failed_rows}")
        logger.info(f"  Fatal issues: {self.fatal_issues}")
        logger.info(f"  Warning issues: {self.warning_issues}")
        logger.info(f"  Info issues: {self.info_issues}")
        
        # Write validation issues to output if any found
        if self.issues:
            self._write_validation_issues()
        
        # Fail if fatal issues found
        if self.fatal_issues > 0:
            issue_rate = self.fatal_issues / self.sampled_rows
            estimated_total_issues = int(issue_rate * self.total_rows)
            raise ValueError(
                f"Validation failed: {self.fatal_issues} fatal issues found in sample. "
                f"Estimated {estimated_total_issues} issues in full dataset."
            )
        
        return self.dataframe
    
    def _write_validation_issues(self) -> None:
        """Write validation issues to the output path."""
        if not self.issues:
            return
        
        # Convert issues to DataFrame
        spark = self.dataframe.sparkSession
        issue_dicts = [issue.to_dict() for issue in self.issues]
        
        # Create schema for issues
        schema = StructType([
            StructField("level", StringType(), False),
            StructField("resource_type", StringType(), False),
            StructField("resource_id", StringType(), False),
            StructField("field", StringType(), False),
            StructField("message", StringType(), False),
            StructField("validation_rule", StringType(), False),
            StructField("timestamp", StringType(), False)
        ])
        
        # Create DataFrame from issues
        issues_df = spark.createDataFrame(issue_dicts, schema)
        
        # Write to output
        try:
            issues_df.write.mode("append").format("json").save(self.output_path)
            logger.info(f"Wrote {len(self.issues)} validation issues to {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to write validation issues: {e}")

# Simplified UDF for row validation in Spark
# This would be used for validating entire DataFrame without collecting rows
def _validate_row_udf_factory(resource_type: str, schema_cls: Type[BaseModel]):
    """Create a UDF for validating rows in Spark."""
    
    def _validate_row_udf(fields):
        """UDF to validate a row and return a list of issues."""
        row_dict = fields.asDict()
        issues = _validate_row(row_dict, schema_cls, resource_type)
        if not issues:
            return None
        
        # Return simplified issue format for Spark
        return [
            {
                "level": issue.level,
                "field": issue.field,
                "message": issue.message
            }
            for issue in issues
        ]
    
    # Return the UDF
    return udf(_validate_row_udf, ArrayType(
        StructType([
            StructField("level", StringType(), True),
            StructField("field", StringType(), True),
            StructField("message", StringType(), True)
        ])
    )) 