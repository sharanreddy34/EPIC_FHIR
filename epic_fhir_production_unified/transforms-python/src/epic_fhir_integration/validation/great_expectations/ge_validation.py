"""
Great Expectations validation for FHIR data quality.

This module provides a framework for validating FHIR data quality using Great Expectations.
It integrates with Foundry transforms to provide data quality gates.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import great_expectations as ge
from great_expectations.dataset import SparkDFDataset, PandasDataset
from pyspark.sql import DataFrame as SparkDataFrame

try:
    from transforms.api import transform_df, Input, Output, Check
    FOUNDRY_AVAILABLE = True
except ImportError:
    FOUNDRY_AVAILABLE = False

from epic_fhir_integration.utils.logging import get_logger
from epic_fhir_integration.utils.config import get_validation_config, ResourceType

logger = get_logger(__name__)


class FHIRDataValidator:
    """Validates FHIR data quality using Great Expectations."""
    
    def __init__(self, resource_type: Union[str, ResourceType], transform_context=None):
        """Initialize validator.
        
        Args:
            resource_type: FHIR resource type to validate
            transform_context: Optional transform context
        """
        if isinstance(resource_type, str):
            self.resource_type = ResourceType(resource_type)
        else:
            self.resource_type = resource_type
            
        self.config = get_validation_config(self.resource_type, transform_context)
        self.expectations = []
        self._load_default_expectations()
    
    def _load_default_expectations(self):
        """Load default expectations for the resource type."""
        # Common expectations for all resource types
        self.add_expectation("expect_column_to_exist", "id")
        self.add_expectation("expect_column_values_to_not_be_null", "id")
        
        # Resource-specific expectations
        if self.resource_type == ResourceType.PATIENT:
            self._load_patient_expectations()
        elif self.resource_type == ResourceType.ENCOUNTER:
            self._load_encounter_expectations()
        elif self.resource_type == ResourceType.CONDITION:
            self._load_condition_expectations()
        elif self.resource_type == ResourceType.OBSERVATION:
            self._load_observation_expectations()
        elif self.resource_type == ResourceType.MEDICATION_REQUEST:
            self._load_medication_request_expectations()
    
    def _load_patient_expectations(self):
        """Load Patient-specific expectations."""
        self.add_expectation("expect_column_to_exist", "gender")
        self.add_expectation("expect_column_to_exist", "birthDate")
        self.add_expectation("expect_column_values_to_be_in_set", "gender", ["male", "female", "unknown", "other"])
    
    def _load_encounter_expectations(self):
        """Load Encounter-specific expectations."""
        self.add_expectation("expect_column_to_exist", "status")
        self.add_expectation("expect_column_to_exist", "subject_reference")
        self.add_expectation("expect_column_values_to_not_be_null", "status")
    
    def _load_condition_expectations(self):
        """Load Condition-specific expectations."""
        self.add_expectation("expect_column_to_exist", "subject_reference")
        self.add_expectation("expect_column_values_to_not_be_null", "subject_reference")
    
    def _load_observation_expectations(self):
        """Load Observation-specific expectations."""
        self.add_expectation("expect_column_to_exist", "subject_reference")
        self.add_expectation("expect_column_to_exist", "status")
        self.add_expectation("expect_column_values_to_not_be_null", "subject_reference")
    
    def _load_medication_request_expectations(self):
        """Load MedicationRequest-specific expectations."""
        self.add_expectation("expect_column_to_exist", "subject_reference")
        self.add_expectation("expect_column_to_exist", "status")
        self.add_expectation("expect_column_values_to_not_be_null", "subject_reference")
    
    def add_expectation(self, expectation_type: str, column_name: str, *args, **kwargs):
        """Add an expectation to the validator.
        
        Args:
            expectation_type: Type of expectation (e.g., 'expect_column_to_exist')
            column_name: Column to apply expectation to
            *args: Additional positional arguments for the expectation
            **kwargs: Additional keyword arguments for the expectation
        """
        self.expectations.append({
            "expectation_type": expectation_type,
            "column": column_name,
            "args": args,
            "kwargs": kwargs
        })
    
    def validate_spark_dataframe(self, df: SparkDataFrame) -> Dict[str, Any]:
        """Validate a Spark DataFrame against the expectations.
        
        Args:
            df: Spark DataFrame to validate
            
        Returns:
            Validation results dictionary
        """
        # Convert to GE Dataset
        ge_df = SparkDFDataset(df)
        
        # Run validations
        results = []
        for exp in self.expectations:
            exp_type = exp["expectation_type"]
            column = exp["column"]
            args = exp["args"]
            kwargs = exp["kwargs"]
            
            try:
                # Get the expectation method
                expectation_method = getattr(ge_df, exp_type)
                
                # Call the method with the column and any additional args/kwargs
                if exp_type.startswith("expect_column_"):
                    result = expectation_method(column, *args, **kwargs)
                else:
                    result = expectation_method(*args, **kwargs)
                
                results.append(result)
                
                # Log the result
                if not result["success"]:
                    logger.warning(
                        f"Validation failed: {exp_type}",
                        column=column,
                        result=result
                    )
            except Exception as e:
                logger.error(
                    f"Error validating {exp_type}",
                    column=column,
                    error=str(e)
                )
                results.append({
                    "expectation_type": exp_type,
                    "success": False,
                    "exception_info": {
                        "raised_exception": True,
                        "exception_message": str(e),
                        "exception_traceback": None
                    }
                })
        
        # Aggregate results
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        success_ratio = success_count / total_count if total_count > 0 else 0
        
        validation_results = {
            "resource_type": self.resource_type.value,
            "success": success_ratio >= (1 - self.config.error_threshold),
            "success_ratio": success_ratio,
            "success_count": success_count,
            "total_count": total_count,
            "expectations": results,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Check if validation should fail the transform
        if self.config.fail_on_error and not validation_results["success"]:
            error_msg = f"Validation failed for {self.resource_type.value}: success ratio {success_ratio:.2f} below threshold {1 - self.config.error_threshold:.2f}"
            logger.error(error_msg)
            
            if FOUNDRY_AVAILABLE:
                raise ValueError(error_msg)
        
        return validation_results
    
    def validate_pandas_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate a Pandas DataFrame against the expectations.
        
        Args:
            df: Pandas DataFrame to validate
            
        Returns:
            Validation results dictionary
        """
        # Convert to GE Dataset
        ge_df = PandasDataset(df)
        
        # Run validations
        results = []
        for exp in self.expectations:
            exp_type = exp["expectation_type"]
            column = exp["column"]
            args = exp["args"]
            kwargs = exp["kwargs"]
            
            try:
                # Get the expectation method
                expectation_method = getattr(ge_df, exp_type)
                
                # Call the method with the column and any additional args/kwargs
                if exp_type.startswith("expect_column_"):
                    result = expectation_method(column, *args, **kwargs)
                else:
                    result = expectation_method(*args, **kwargs)
                
                results.append(result)
                
                # Log the result
                if not result["success"]:
                    logger.warning(
                        f"Validation failed: {exp_type}",
                        column=column,
                        result=result
                    )
            except Exception as e:
                logger.error(
                    f"Error validating {exp_type}",
                    column=column,
                    error=str(e)
                )
                results.append({
                    "expectation_type": exp_type,
                    "success": False,
                    "exception_info": {
                        "raised_exception": True,
                        "exception_message": str(e),
                        "exception_traceback": None
                    }
                })
        
        # Aggregate results
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        success_ratio = success_count / total_count if total_count > 0 else 0
        
        validation_results = {
            "resource_type": self.resource_type.value,
            "success": success_ratio >= (1 - self.config.error_threshold),
            "success_ratio": success_ratio,
            "success_count": success_count,
            "total_count": total_count,
            "expectations": results,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Check if validation should fail the transform
        if self.config.fail_on_error and not validation_results["success"]:
            error_msg = f"Validation failed for {self.resource_type.value}: success ratio {success_ratio:.2f} below threshold {1 - self.config.error_threshold:.2f}"
            logger.error(error_msg)
            
            if FOUNDRY_AVAILABLE:
                raise ValueError(error_msg)
        
        return validation_results


# Foundry transform wrapper for validation
if FOUNDRY_AVAILABLE:
    @transform_df(
        Output("datasets/validation/results"),
        Input("datasets/source"),
        Check(assert_true="success_ratio > 0.95", description="Data quality must be at least 95%")
    )
    def validate_resource(ctx, output, source):
        """Validate a FHIR resource using Great Expectations.
        
        Args:
            ctx: Transform context
            output: Output dataset
            source: Source dataset to validate
            
        Returns:
            DataFrame with validation results
        """
        # Get resource type from configuration
        resource_type = ctx.resource_type
        
        # Create validator
        validator = FHIRDataValidator(resource_type, ctx)
        
        # Run validation
        df = source.dataframe()
        results = validator.validate_spark_dataframe(df)
        
        # Convert results to DataFrame
        results_json = json.dumps(results)
        results_df = ctx.spark_session.createDataFrame([(results_json,)], ["validation_results"])
        
        return results_df 