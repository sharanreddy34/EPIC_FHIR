"""
Great Expectations validator adapter for FHIR resources.

This module provides an adapter for using Great Expectations to validate
FHIR resources and integrate with the quality metrics framework.
"""

import json
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import time
from uuid import uuid4

import great_expectations as ge
import pandas as pd
from great_expectations.core import ExpectationConfiguration, ExpectationSuite
from great_expectations.dataset import PandasDataset
from great_expectations.exceptions import (
    DataContextError,
    ValidationError
)

from epic_fhir_integration.metrics.data_quality import DataQualityDimension
from epic_fhir_integration.metrics.validation_metrics import (
    ValidationMetricsRecorder,
    ValidationSeverity,
    ValidationCategory,
    ValidationType
)

logger = logging.getLogger(__name__)

# Debug levels for more granular logging control
DEBUG_BASIC = 10      # Basic debug info (existing DEBUG level)
DEBUG_DETAILED = 5    # More detailed debug info
DEBUG_TRACE = 3       # Trace-level debugging with full context

# Add custom log levels to the logging module
logging.addLevelName(DEBUG_DETAILED, "DETAILED")
logging.addLevelName(DEBUG_TRACE, "TRACE")

# Add logging methods to the logger class for custom levels
def detailed(self, message, *args, **kwargs):
    if self.isEnabledFor(DEBUG_DETAILED):
        self._log(DEBUG_DETAILED, message, args, **kwargs)

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(DEBUG_TRACE):
        self._log(DEBUG_TRACE, message, args, **kwargs)

# Add methods to Logger class
logging.Logger.detailed = detailed
logging.Logger.trace = trace


class GreatExpectationsValidator:
    """Validates FHIR resources using Great Expectations."""

    def __init__(
        self,
        validation_metrics_recorder: Optional[ValidationMetricsRecorder] = None,
        context_root_dir: Optional[str] = None,
        expectation_suite_dir: Optional[str] = None,
        debug_level: int = logging.INFO
    ):
        """Initialize the Great Expectations validator.
        
        Args:
            validation_metrics_recorder: Optional validation metrics recorder
            context_root_dir: Optional root directory for Great Expectations context
            expectation_suite_dir: Optional directory containing expectation suites
            debug_level: Logging level for this validator instance
        """
        self.validation_metrics_recorder = validation_metrics_recorder
        self._init_timer = time.time()
        self._log_with_context("Initializing Great Expectations validator", level=logging.INFO)
        
        # Track init params for debugging context
        self._debug_context = {
            "context_root_dir": context_root_dir,
            "expectation_suite_dir": expectation_suite_dir,
            "debug_level": debug_level
        }
        
        # Determine default paths if not provided
        if not context_root_dir:
            # First try to find GX directory starting with current module's location
            module_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(module_dir))  # Go up two levels
            
            self._log_with_context(f"No context root provided, searching from {project_root}", level=DEBUG_DETAILED)
            
            # Check if GX directory exists at project root or inside epic-fhir-integration
            possible_locations = [
                os.path.join(project_root, "great_expectations"),
                os.path.join(project_root, "epic-fhir-integration", "great_expectations"),
                os.path.join(os.path.dirname(project_root), "great_expectations")
            ]
            
            for location in possible_locations:
                self._log_with_context(f"Checking for Great Expectations directory at: {location}", level=DEBUG_DETAILED)
                if os.path.exists(location):
                    context_root_dir = location
                    self._log_with_context(f"Found Great Expectations directory at: {context_root_dir}", level=logging.INFO)
                    break
                
        if context_root_dir:
            self._log_with_context(f"Using Great Expectations context root: {context_root_dir}", level=logging.INFO)
            
        # Determine expectation suite directory if not provided
        if not expectation_suite_dir and context_root_dir:
            self.expectation_suite_dir = os.path.join(context_root_dir, "expectations")
            self._log_with_context(f"Using expectations directory: {self.expectation_suite_dir}", level=logging.INFO)
        else:
            self.expectation_suite_dir = expectation_suite_dir
        
        try:
            # Try to initialize context from standard location
            if context_root_dir and os.path.exists(os.path.join(context_root_dir, "great_expectations.yml")):
                self._log_with_context(f"Initializing context from {context_root_dir}", level=DEBUG_DETAILED)
                start_time = time.time()
                self.context = ge.get_context(context_root_dir=context_root_dir)
                self._log_with_context(
                    f"Initialized Great Expectations context from {context_root_dir} using get_context() "
                    f"in {time.time() - start_time:.2f}s", 
                    level=logging.INFO
                )
            else:
                # Fallback to an in-memory context if no valid project found
                self._log_with_context(
                    f"No valid Great Expectations project found at {context_root_dir}. "
                    f"Using ephemeral DataContext - expectation suites may not be persisted if not loaded manually.",
                    level=logging.WARNING
                )
                start_time = time.time()
                self.context = ge.get_context(project_config=self._create_default_project_config())
                self._log_with_context(
                    f"Initialized ephemeral Great Expectations context in {time.time() - start_time:.2f}s", 
                    level=logging.INFO
                )

            # Ensure a runtime datasource exists
            self._init_datasource_with_fallbacks()

            # If we successfully initialized the context but expectation_suite_dir wasn't set,
            # try to get it from the context
            if not self.expectation_suite_dir:
                try:
                    self.expectation_suite_dir = self.context.stores["expectations_store"].store_backend.root_directory
                    self._log_with_context(f"Using expectation suite directory from context: {self.expectation_suite_dir}", level=logging.INFO)
                except (AttributeError, KeyError, TypeError) as e: # Added TypeError
                    self._log_with_context(f"Could not determine expectation suite directory from context: {e}", level=logging.WARNING)
        
        except Exception as e: # Broader exception catch for context initialization
            self._log_exception(
                f"Failed to initialize Great Expectations context critically", 
                e, 
                level=logging.ERROR,
                exc_info=True
            )
            self._log_with_context("Falling back to a very basic ephemeral DataContext", level=logging.WARNING)
            self.context = ge.get_context(project_config=self._create_default_project_config())
            try:
                self.context.sources.add_pandas(name="runtime_datasource") # Ensure datasource for ephemeral
                self._log_with_context("Added 'runtime_datasource' (Pandas) to the critical fallback ephemeral DataContext", level=logging.INFO)
            except Exception as final_ds_error:
                self._log_exception("Could not add datasource to critical fallback context", final_ds_error, level=logging.ERROR)
        
        # Load expectation suites
        self.expectation_suites = {}
        self._load_expectation_suites()
        
        total_init_time = time.time() - self._init_timer
        self._log_with_context(f"Validator initialization completed in {total_init_time:.2f}s", level=logging.INFO)

    def _init_datasource_with_fallbacks(self) -> None:
        """Initialize datasource with multiple fallback approaches."""
        try:
            datasources = self.context.list_datasources()
            if not any(ds["name"] == "runtime_datasource" for ds in datasources):
                self._log_with_context("Adding 'runtime_datasource' (Pandas) to the DataContext", level=DEBUG_DETAILED)
                start_time = time.time()
                self.context.sources.add_pandas(name="runtime_datasource")
                self._log_with_context(
                    f"Added 'runtime_datasource' (Pandas) in {time.time() - start_time:.2f}s", 
                    level=logging.INFO
                )
        except Exception as ds_error:
            self._log_exception("Error ensuring runtime_datasource", ds_error, level=logging.ERROR)
            self._log_with_context("Attempting to add with older API", level=logging.INFO)
            
            # Fallback for older versions or different context types
            try:
                if "runtime_datasource" not in self.context.list_datasources(): # Check again if previous failed
                    self._log_with_context("Adding datasource using fallback API", level=DEBUG_DETAILED)
                    start_time = time.time()
                    self.context.add_datasource(
                        name="runtime_datasource",
                        class_name="Datasource", # Generic Datasource
                        execution_engine={"class_name": "PandasExecutionEngine"},
                        data_connectors={
                            "runtime_data_connector": {
                                "class_name": "RuntimeDataConnector",
                                "batch_identifiers": ["default_identifier_name"],
                            }
                        }
                    )
                    self._log_with_context(
                        f"Added 'runtime_datasource' (Fallback API) in {time.time() - start_time:.2f}s", 
                        level=logging.INFO
                    )
            except Exception as fallback_ds_error:
                self._log_exception("Fallback API for adding datasource also failed", fallback_ds_error, level=logging.ERROR, exc_info=True)
    
    def _log_with_context(self, message: str, level: int = logging.DEBUG, **kwargs) -> None:
        """Log a message with contextual information.
        
        Args:
            message: The message to log
            level: The logging level
            **kwargs: Additional context to include in the log
        """
        if not logger.isEnabledFor(level):
            return
            
        # Add standard context information
        context = {
            "class": self.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add any caller-provided context
        context.update(kwargs)
        
        # Format the log message with context
        formatted_context = " | ".join([f"{k}={v}" for k, v in context.items()])
        full_message = f"{message} [{formatted_context}]"
        
        # Log at the appropriate level
        logger.log(level, full_message)
    
    def _log_exception(self, message: str, exception: Exception, level: int = logging.ERROR, exc_info: bool = False, **kwargs) -> None:
        """Log an exception with detailed information.
        
        Args:
            message: The error message
            exception: The exception that was caught
            level: The logging level
            exc_info: Whether to include exception info in the log
            **kwargs: Additional context parameters to include in the log
        """
        error_context = {
            "exception_type": exception.__class__.__name__,
            "exception_msg": str(exception),
        }
        
        # Add traceback info for detailed debugging
        if level <= DEBUG_TRACE or exc_info: # Ensure traceback is included if exc_info is True
            error_context["traceback"] = traceback.format_exc()
        
        # Add any additional context from kwargs
        error_context.update(kwargs)
        
        self._log_with_context(message, level=level, **error_context)
        
        # Also log with exc_info if requested (for standard error logging)
        if exc_info and level == logging.ERROR:
            logger.error(message, exc_info=True)

    def _create_default_project_config(self) -> Dict[str, Any]:
        """Create a default Great Expectations project config.
        
        Returns:
            Dictionary with default project config
        """
        return {
            "datasources": {},
            "expectations_store_name": "expectations_store",
            "validations_store_name": "validations_store",
            "evaluation_parameter_store_name": "evaluation_parameter_store",
            "stores": {
                "expectations_store": {
                    "class_name": "ExpectationsStore",
                    "store_backend": {
                        "class_name": "InMemoryStoreBackend"
                    }
                },
                "validations_store": {
                    "class_name": "ValidationsStore",
                    "store_backend": {
                        "class_name": "InMemoryStoreBackend"
                    }
                },
                "evaluation_parameter_store": {
                    "class_name": "EvaluationParameterStore"
                }
            },
            "data_docs_sites": {},
            "config_version": 2,
            "plugins_directory": None
        }

    def _load_expectation_suites(self) -> None:
        """Load expectation suites from the expectation suite directory."""
        load_start = time.time()
        
        if not self.expectation_suite_dir:
            self._log_with_context("No expectation suite directory specified", level=logging.WARNING)
            return
            
        if not os.path.exists(self.expectation_suite_dir):
            self._log_with_context(
                f"Expectation suite directory not found: {self.expectation_suite_dir}", 
                level=logging.WARNING
            )
            return
            
        # Find all JSON files in the directory
        self._log_with_context(
            f"Searching for expectation suite files in {self.expectation_suite_dir}", 
            level=logging.INFO
        )
        
        search_start = time.time()
        suite_files = list(Path(self.expectation_suite_dir).glob("*.json"))
        search_time = time.time() - search_start
        
        self._log_with_context(
            f"Found {len(suite_files)} expectation suite files in {search_time:.3f}s", 
            level=logging.INFO,
            file_count=len(suite_files)
        )
        
        if not suite_files:
            self._log_with_context(
                f"No expectation suite files found in {self.expectation_suite_dir}", 
                level=logging.WARNING
            )
            return
            
        # Prepare a progress tracking mechanism
        total_files = len(suite_files)
        loaded_success = 0
        loaded_failed = 0
        load_errors = {}
        progress_interval = max(1, min(50, total_files // 5))  # Report progress at most 5 times
        
        for i, suite_file in enumerate(suite_files):
            # Log progress at intervals
            if (i % progress_interval == 0) or (i == total_files - 1):
                self._log_with_context(
                    f"Loading suites progress: {i+1}/{total_files} files ({(i+1)/total_files:.1%})",
                    level=logging.INFO,
                    success_count=loaded_success,
                    failure_count=loaded_failed
                )
                
            suite_name = suite_file.stem
            file_start = time.time()
            
            try:
                self._log_with_context(
                    f"Loading expectation suite from {suite_file}", 
                    level=DEBUG_DETAILED,
                    suite_name=suite_name
                )
                
                # Measure file reading time
                read_start = time.time()
                with open(suite_file, "r") as f:
                    suite_data = json.load(f)
                read_time = time.time() - read_start
                
                # Measure expectation processing time
                processing_start = time.time()
                
                # Count expectations for logging
                expectation_count = len(suite_data.get("expectations", []))
                
                # Create expectation suite from JSON
                suite = ExpectationSuite(
                    expectation_suite_name=suite_name,
                    expectations=suite_data.get("expectations", []),
                    meta=suite_data.get("meta", {})
                )
                
                processing_time = time.time() - processing_start
                
                # Basic validation of the loaded suite
                valid_suite = len(suite.expectations) > 0 or expectation_count == 0
                    
                if valid_suite:
                    self.expectation_suites[suite_name] = suite
                    loaded_success += 1
                    
                    self._log_with_context(
                        f"Loaded expectation suite: {suite_name} with {len(suite.expectations)} expectations",
                        level=DEBUG_DETAILED,
                        suite_name=suite_name,
                        expectation_count=len(suite.expectations),
                        file_size=os.path.getsize(suite_file),
                        read_time=f"{read_time:.3f}s",
                        processing_time=f"{processing_time:.3f}s"
                    )
                else:
                    loaded_failed += 1
                    error_msg = f"Suite validation failed - expected {expectation_count} expectations but parsed {len(suite.expectations)}"
                    load_errors[suite_name] = error_msg
                    
                    self._log_with_context(
                        f"Suite validation failed for {suite_name}: {error_msg}", 
                        level=logging.WARNING,
                        suite_name=suite_name,
                        expected=expectation_count,
                        parsed=len(suite.expectations)
                    )
                
                file_time = time.time() - file_start
                if file_time > 1.0:  # Log slow-loading files
                    self._log_with_context(
                        f"Suite {suite_name} loaded slowly in {file_time:.2f}s", 
                        level=logging.WARNING,
                        suite_name=suite_name,
                        load_time=file_time
                    )
                
            except Exception as e:
                loaded_failed += 1
                error_msg = str(e)
                load_errors[suite_name] = error_msg
                
                self._log_exception(
                    f"Failed to load expectation suite {suite_file}", 
                    e, 
                    level=logging.ERROR,
                    exc_info=True, # Ensure exc_info is passed for full traceback on ERROR
                    suite_name=suite_name,
                    file_path=str(suite_file)
                )
        
        # Log summary of loaded suites
        total_load_time = time.time() - load_start
        avg_load_time = total_load_time / total_files if total_files > 0 else 0
        
        if self.expectation_suites:
            self._log_with_context(
                f"Successfully loaded {loaded_success}/{total_files} expectation suites in {total_load_time:.2f}s ({avg_load_time:.3f}s per suite)",
                level=logging.INFO,
                success_count=loaded_success,
                failure_count=loaded_failed,
                total_files=total_files,
                total_time=total_load_time,
                avg_time=avg_load_time
            )
            
            # Log available suites for debugging
            suite_names = ", ".join(sorted(self.expectation_suites.keys()))
            self._log_with_context(
                f"Available expectation suites: {suite_names}",
                level=DEBUG_DETAILED,
                suite_count=len(self.expectation_suites)
            )
        else:
            self._log_with_context(
                f"No expectation suites were successfully loaded (attempted {total_files} files)",
                level=logging.WARNING,
                attempted=total_files,
                failures=loaded_failed
            )
            
        # If there were errors, log them in detail
        if load_errors:
            error_summary = "; ".join([f"{name}: {error}" for name, error in load_errors.items()])
            self._log_with_context(
                f"Encountered errors loading {len(load_errors)} suites: {error_summary}",
                level=logging.WARNING if len(load_errors) < total_files else logging.ERROR,
                error_count=len(load_errors)
            )

    def get_expectation_suite(self, suite_name: str) -> Optional[ExpectationSuite]:
        """Get an expectation suite by name.
        
        Args:
            suite_name: Name of the expectation suite
            
        Returns:
            ExpectationSuite object or None if not found
        """
        # First check our loaded suites
        if suite_name in self.expectation_suites:
            return self.expectation_suites[suite_name]
            
        # Then try to get from context
        try:
            return self.context.get_expectation_suite(suite_name)
        except Exception as e:
            logger.warning(f"Could not find expectation suite '{suite_name}': {str(e)}")
            return None

    def validate_resource(
        self,
        resource: Dict[str, Any],
        expectation_suite_name: str,
        resource_id: Optional[str] = None,
        pipeline_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate a FHIR resource against an expectation suite.
        
        Args:
            resource: FHIR resource as a dictionary
            expectation_suite_name: Name of the expectation suite to validate against
            resource_id: Optional resource ID for reporting
            pipeline_stage: Optional pipeline stage for reporting
            
        Returns:
            Dictionary with validation results
        """
        validation_start = time.time()
        
        # Get resource type and ID
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource_id or resource.get("id", "unknown")
        
        self._log_with_context(
            f"Starting validation of {resource_type}/{resource_id} against suite '{expectation_suite_name}'",
            level=logging.INFO,
            resource_type=resource_type,
            resource_id=resource_id,
            suite=expectation_suite_name,
            pipeline_stage=pipeline_stage
        )
        
        # Get expectation suite
        suite_timer = time.time()
        suite = self.get_expectation_suite(expectation_suite_name)
        suite_time = time.time() - suite_timer
        
        if not suite:
            # Log and return if suite not found
            self._log_with_context(
                f"Expectation suite '{expectation_suite_name}' not found", 
                level=logging.ERROR,
                resource_type=resource_type,
                resource_id=resource_id,
                suite=expectation_suite_name
            )
            return {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "is_valid": False,
                "validation_type": ValidationType.CUSTOM.value,
                "issues": [
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "category": ValidationCategory.UNKNOWN.value,
                        "message": f"Expectation suite '{expectation_suite_name}' not found"
                    }
                ]
            }
        
        self._log_with_context(
            f"Retrieved expectation suite '{expectation_suite_name}' in {suite_time:.3f}s with {len(suite.expectations)} expectations",
            level=DEBUG_DETAILED,
            resource_type=resource_type,
            resource_id=resource_id,
            expectation_count=len(suite.expectations)
        )
        
        # Flatten resource for validation
        flatten_timer = time.time()
        df = self._resource_to_dataframe(resource)
        flatten_time = time.time() - flatten_timer
        
        self._log_with_context(
            f"Flattened resource to DataFrame in {flatten_time:.3f}s with {len(df.columns)} columns",
            level=DEBUG_DETAILED,
            resource_type=resource_type,
            resource_id=resource_id,
            column_count=len(df.columns)
        )
        
        # Modern way to validate with a Validator
        try:
            # Define a dynamic asset name for this validation
            # This helps ensure we are referencing a specific in-memory table
            data_asset_name = f"rt_{resource_type}_{uuid4().hex}"
            
            validation_timer = time.time()
            result = self._perform_validation_with_fallbacks(df, data_asset_name, expectation_suite_name, resource_type, resource_id)
            validation_time = time.time() - validation_timer

            self._log_with_context(
                f"Validation completed in {validation_time:.3f}s",
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id,
                is_valid=result.success
            )

        except Exception as e: # Catch a broader range of GX exceptions
            self._log_exception(
                f"Error validating resource '{resource_id}' of type '{resource_type}' with suite '{expectation_suite_name}'", 
                e,
                level=logging.ERROR,
                exc_info=True, # Ensure exc_info is passed for full traceback on ERROR
                resource_type=resource_type, # Added context
                resource_id=resource_id,     # Added context
                suite=expectation_suite_name # Added context
            )
            return {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "is_valid": False,
                "validation_type": ValidationType.CUSTOM.value,
                "issues": [
                    {
                        "severity": ValidationSeverity.ERROR.value,
                        "category": ValidationCategory.UNKNOWN.value,
                        "message": f"Validation error: {str(e)}"
                    }
                ]
            }
        
        # Process validation results
        process_timer = time.time()
        is_valid = result.success
        issues = self._process_validation_results(result)
        process_time = time.time() - process_timer
        
        self._log_with_context(
            f"Processed validation results in {process_time:.3f}s, found {len(issues)} issues",
            level=DEBUG_DETAILED,
            resource_type=resource_type,
            resource_id=resource_id,
            issue_count=len(issues)
        )
        
        # Record validation metrics
        validation_result = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "is_valid": is_valid,
            "validation_type": ValidationType.CUSTOM.value,
            "issues": issues
        }
        
        if self.validation_metrics_recorder and pipeline_stage:
            metrics_timer = time.time()
            self.validation_metrics_recorder.record_validation_result(
                resource_type=resource_type,
                is_valid=is_valid,
                validation_type=ValidationType.CUSTOM,
                pipeline_stage=pipeline_stage,
                issues=issues,
                metadata={"expectation_suite": expectation_suite_name}
            )
            metrics_time = time.time() - metrics_timer
            
            self._log_with_context(
                f"Recorded validation metrics in {metrics_time:.3f}s",
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id
            )
        
        total_validation_time = time.time() - validation_start
        
        self._log_with_context(
            f"Completed validation of {resource_type}/{resource_id} in {total_validation_time:.3f}s - Valid: {is_valid}, Issues: {len(issues)}",
            level=logging.INFO,
            resource_type=resource_type,
            resource_id=resource_id,
            is_valid=is_valid,
            issue_count=len(issues),
            total_time=total_validation_time
        )
        
        return validation_result

    def _perform_validation_with_fallbacks(
        self, 
        df: pd.DataFrame, 
        data_asset_name: str, 
        expectation_suite_name: str,
        resource_type: str,
        resource_id: str
    ):
        """Perform validation with fallback approaches if needed.
        
        Args:
            df: DataFrame to validate
            data_asset_name: Name for the data asset
            expectation_suite_name: Name of the expectation suite
            resource_type: Resource type for logging
            resource_id: Resource ID for logging
            
        Returns:
            Validation result
        """
        # Try with modern Validator API first
        try:
            self._log_with_context(
                f"Attempting validation with modern Validator API", 
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            # Try to get existing datasource first
            ds = self.context.get_datasource("runtime_datasource")
            
            # Add asset to existing datasource
            ds_timer = time.time()
            ds.add_dataframe_asset(name=data_asset_name, dataframe=df)
            ds_time = time.time() - ds_timer
            
            self._log_with_context(
                f"Added DataFrame asset to datasource in {ds_time:.3f}s", 
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            # Create a BatchRequest referencing the newly added asset
            batch_timer = time.time()
            batch_request = ds.get_asset(data_asset_name).build_batch_request()
            batch_time = time.time() - batch_timer
            
            self._log_with_context(
                f"Built batch request in {batch_time:.3f}s", 
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id
            )

            # Get a Validator instance
            validator_timer = time.time()
            validator = self.context.get_validator(
                batch_request=batch_request,
                expectation_suite_name=expectation_suite_name 
            )
            validator_time = time.time() - validator_timer
            
            self._log_with_context(
                f"Created validator in {validator_time:.3f}s", 
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            # Validate the dataset using the validator
            result_timer = time.time()
            result = validator.validate()
            result_time = time.time() - result_timer
            
            self._log_with_context(
                f"Executed validation in {result_time:.3f}s", 
                level=DEBUG_DETAILED,
                resource_type=resource_type,
                resource_id=resource_id,
                expectation_count=len(result.results) if hasattr(result, 'results') else 'unknown'
            )
            
            return result
            
        except Exception as e:
            self._log_exception(
                f"Error using modern Validator API", 
                e, 
                level=logging.WARNING,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            # Fallback for older versions or if above fails
            self._log_with_context(
                f"Trying alternative legacy approach for validation", 
                level=logging.INFO,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            try:
                suite_timer = time.time()
                self.context.create_expectation_suite(
                    expectation_suite_name=expectation_suite_name, 
                    overwrite_existing=False
                )
                suite_time = time.time() - suite_timer
                
                self._log_with_context(
                    f"Created/ensured expectation suite in {suite_time:.3f}s", 
                    level=DEBUG_DETAILED,
                    resource_type=resource_type,
                    resource_id=resource_id
                )
                
                batch_kwargs = {
                    "datasource": "runtime_datasource",
                    "dataset": data_asset_name,
                    "dataframe": df
                }
                
                batch_timer = time.time()
                batch = self.context.get_batch(
                    batch_kwargs=batch_kwargs, 
                    expectation_suite_name=expectation_suite_name
                )
                batch_time = time.time() - batch_timer
                
                self._log_with_context(
                    f"Got batch in legacy mode in {batch_time:.3f}s", 
                    level=DEBUG_DETAILED,
                    resource_type=resource_type,
                    resource_id=resource_id
                )
                
                validate_timer = time.time()
                result = batch.validate()
                validate_time = time.time() - validate_timer
                
                self._log_with_context(
                    f"Executed legacy validation in {validate_time:.3f}s", 
                    level=DEBUG_DETAILED,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    expectation_count=len(result.results) if hasattr(result, 'results') else 'unknown'
                )
                
                return result
                
            except Exception as fallback_e:
                self._log_exception(
                    f"Legacy validation approach also failed for {resource_type}/{resource_id} with suite {expectation_suite_name}", 
                    fallback_e, 
                    level=logging.ERROR,
                    exc_info=True, # Ensure exc_info is passed for full traceback on ERROR
                    resource_type=resource_type, # Added context
                    resource_id=resource_id,     # Added context
                    suite=expectation_suite_name # Added context
                )
                raise fallback_e

    def validate_resources(
        self,
        resources: List[Dict[str, Any]],
        expectation_suite_name: str,
        pipeline_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate multiple FHIR resources against an expectation suite.
        
        Args:
            resources: List of FHIR resources as dictionaries
            expectation_suite_name: Name of the expectation suite to validate against
            pipeline_stage: Optional pipeline stage for reporting
            
        Returns:
            Dictionary with batch validation results
        """
        batch_start = time.time()
        total_resources = len(resources)
        
        self._log_with_context(
            f"Starting batch validation of {total_resources} resources against suite '{expectation_suite_name}'",
            level=logging.INFO,
            resource_count=total_resources,
            suite=expectation_suite_name,
            pipeline_stage=pipeline_stage
        )
        
        results = []
        valid_count = 0
        issue_count = 0
        progress_interval = max(1, min(100, total_resources // 10))  # Report progress at most 10 times
        
        for i, resource in enumerate(resources):
            # Get resource type and ID for logging
            resource_type = resource.get("resourceType", "Unknown")
            resource_id = resource.get("id", "unknown")
            
            # Log progress at intervals
            if (i % progress_interval == 0) or (i == total_resources - 1):
                self._log_with_context(
                    f"Validation progress: {i+1}/{total_resources} resources ({(i+1)/total_resources:.1%})",
                    level=logging.INFO,
                    progress_percent=round((i+1)/total_resources * 100, 1),
                    resource_type=resource_type,
                    valid_so_far=valid_count,
                    issues_so_far=issue_count
                )
            
            # Validate individual resource
            result = self.validate_resource(
                resource=resource,
                expectation_suite_name=expectation_suite_name,
                pipeline_stage=pipeline_stage
            )
            
            # Track validation outcomes
            if result.get("is_valid", False):
                valid_count += 1
            
            current_issues = len(result.get("issues", []))
            issue_count += current_issues
            
            # Log significant validation failures
            if current_issues > 0:
                self._log_with_context(
                    f"Resource {resource_type}/{resource_id} validation failed with {current_issues} issues",
                    level=DEBUG_DETAILED if current_issues < 5 else logging.WARNING,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    issue_count=current_issues
                )
            
            results.append(result)
        
        batch_time = time.time() - batch_start
        avg_time_per_resource = batch_time / total_resources if total_resources > 0 else 0
        
        self._log_with_context(
            f"Completed batch validation in {batch_time:.2f}s ({avg_time_per_resource:.3f}s per resource)",
            level=logging.INFO,
            resource_count=total_resources,
            valid_count=valid_count,
            validation_rate=f"{valid_count/total_resources:.1%}" if total_resources > 0 else "N/A",
            issue_count=issue_count,
            avg_issues=f"{issue_count/total_resources:.2f}" if total_resources > 0 else "N/A",
            elapsed_time=batch_time,
            avg_time=avg_time_per_resource
        )
        
        # Record batch validation results if metrics recorder available
        if self.validation_metrics_recorder and pipeline_stage:
            metrics_timer = time.time()
            summary = self.validation_metrics_recorder.record_batch_validation_results(
                results=results,
                validation_type=ValidationType.CUSTOM,
                pipeline_stage=pipeline_stage,
                metadata={"expectation_suite": expectation_suite_name}
            )
            metrics_time = time.time() - metrics_timer
            
            self._log_with_context(
                f"Recorded batch validation metrics in {metrics_time:.3f}s",
                level=logging.INFO
            )
            
            return summary
        else:
            # Create summary manually
            summary_timer = time.time()
            
            all_issues = []
            for result in results:
                all_issues.extend(result.get("issues", []))
            
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline_stage": pipeline_stage,
                "validation_type": ValidationType.CUSTOM.value,
                "resources_total": total_resources,
                "resources_valid": valid_count,
                "validation_rate": valid_count / total_resources if total_resources > 0 else 0,
                "total_issues": len(all_issues),
                "issues_per_resource": len(all_issues) / total_resources if total_resources > 0 else 0,
                "results": results
            }
            
            summary_time = time.time() - summary_timer
            
            self._log_with_context(
                f"Created manual validation summary in {summary_time:.3f}s",
                level=DEBUG_DETAILED
            )
            
            return summary

    def create_expectation_suite(
        self,
        name: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> ExpectationSuite:
        """Create a new expectation suite.
        
        Args:
            name: Name of the expectation suite
            meta: Optional metadata for the suite
            
        Returns:
            New ExpectationSuite object
        """
        meta = meta or {}
        
        # Create suite
        suite = ExpectationSuite(
            expectation_suite_name=name,
            meta=meta
        )
        
        # Store in local cache
        self.expectation_suites[name] = suite
        
        # Try to store in context
        try:
            self.context.add_expectation_suite(suite)
            logger.info(f"Created expectation suite: {name}")
        except Exception as e:
            logger.warning(f"Could not store expectation suite '{name}' in Great Expectations context: {str(e)}", exc_info=True)
        
        return suite

    def add_expectation(
        self,
        suite_name: str,
        expectation_type: str,
        kwargs: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add an expectation to an expectation suite.
        
        Args:
            suite_name: Name of the expectation suite
            expectation_type: Type of expectation to add
            kwargs: Arguments for the expectation
            meta: Optional metadata for the expectation
            
        Returns:
            True if the expectation was added, False otherwise
        """
        # Get or create suite
        suite = self.get_expectation_suite(suite_name)
        if not suite:
            suite = self.create_expectation_suite(suite_name)
        
        # Create expectation configuration
        config = ExpectationConfiguration(
            expectation_type=expectation_type,
            kwargs=kwargs,
            meta=meta or {}
        )
        
        # Add to suite
        suite.add_expectation(config)
        
        # Try to update in context
        try:
            self.context.add_expectation_suite(suite)
            logger.info(f"Added expectation to suite {suite_name}: {expectation_type}")
            return True
        except Exception as e:
            logger.warning(f"Could not update expectation suite '{suite_name}' in Great Expectations context: {str(e)}", exc_info=True)
            # We still added it to our local cache
            return True

    def save_expectation_suite(
        self,
        suite_name: str,
        directory: Optional[str] = None
    ) -> Optional[str]:
        """Save an expectation suite to a file.
        
        Args:
            suite_name: Name of the expectation suite
            directory: Optional directory to save to, defaults to self.expectation_suite_dir
            
        Returns:
            Path to the saved file or None if it could not be saved
        """
        # Get suite
        suite = self.get_expectation_suite(suite_name)
        if not suite:
            logger.warning(f"Expectation suite '{suite_name}' not found")
            return None
        
        # Determine directory
        save_dir = directory or self.expectation_suite_dir
        if not save_dir:
            logger.warning("No directory specified for saving expectation suite")
            return None
            
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Create file path
        file_path = os.path.join(save_dir, f"{suite_name}.json")
        
        # Convert suite to dictionary
        suite_dict = {
            "expectations": [exp.to_json_dict() for exp in suite.expectations],
            "meta": suite.meta
        }
        
        # Save to file
        try:
            with open(file_path, "w") as f:
                json.dump(suite_dict, f, indent=2)
            logger.info(f"Saved expectation suite to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save expectation suite '{suite_name}' to {file_path}: {str(e)}", exc_info=True)
            return None

    def _resource_to_dataframe(self, resource: Dict[str, Any]) -> pd.DataFrame:
        """Convert a FHIR resource to a DataFrame for validation.
        
        Args:
            resource: FHIR resource as a dictionary
            
        Returns:
            Pandas DataFrame with flattened resource
        """
        # Flatten the resource
        flat_data = self._flatten_resource(resource)
        
        # Convert to DataFrame
        df = pd.DataFrame([flat_data])
        return df

    def _flatten_resource(
        self,
        resource: Dict[str, Any],
        prefix: str = "",
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """Flatten a FHIR resource into a dictionary with dot-separated keys.
        
        Args:
            resource: FHIR resource as a dictionary
            prefix: Prefix for keys
            max_depth: Maximum depth to flatten
            
        Returns:
            Dictionary with flattened resource
        """
        if max_depth <= 0:
            return {}
            
        result = {}
        
        if isinstance(resource, dict):
            for key, value in resource.items():
                new_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, (dict, list)):
                    flattened = self._flatten_resource(value, new_key, max_depth - 1)
                    result.update(flattened)
                else:
                    result[new_key] = value
        elif isinstance(resource, list):
            for i, item in enumerate(resource):
                new_key = f"{prefix}[{i}]"
                
                if isinstance(item, (dict, list)):
                    flattened = self._flatten_resource(item, new_key, max_depth - 1)
                    result.update(flattened)
                else:
                    result[new_key] = item
        
        return result

    def _process_validation_results(
        self,
        result
    ) -> List[Dict[str, Any]]:
        """Process validation results into a list of issues.
        
        Args:
            result: Great Expectations validation result
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Process each expectation result
        for res in result.results:
            # Skip if successful
            if res.success:
                continue
                
            # Get expectation info
            expectation_type = res.expectation_config.expectation_type
            kwargs = res.expectation_config.kwargs
            
            # Create issue
            issue = {
                "severity": ValidationSeverity.ERROR.value,
                "category": self._get_issue_category(expectation_type),
                "message": f"Failed expectation: {expectation_type}",
                "details": {
                    "expectation_type": expectation_type,
                    "kwargs": kwargs,
                    "result": res.result
                }
            }
            
            issues.append(issue)
        
        return issues

    def _get_issue_category(self, expectation_type: str) -> str:
        """Get the validation category for an expectation type.
        
        Args:
            expectation_type: Great Expectations expectation type
            
        Returns:
            Validation category
        """
        # Map expectation types to categories
        mapping = {
            "expect_column_to_exist": ValidationCategory.STRUCTURE.value,
            "expect_table_columns_to_match_ordered_list": ValidationCategory.STRUCTURE.value,
            "expect_table_column_count_to_be": ValidationCategory.STRUCTURE.value,
            "expect_table_row_count_to_be": ValidationCategory.STRUCTURE.value,
            "expect_column_values_to_not_be_null": ValidationCategory.STRUCTURE.value,
            
            "expect_column_values_to_be_in_set": ValidationCategory.VALUE.value,
            "expect_column_values_to_be_between": ValidationCategory.VALUE.value,
            "expect_column_values_to_match_regex": ValidationCategory.VALUE.value,
            "expect_column_values_to_match_strftime_format": ValidationCategory.VALUE.value,
            "expect_column_values_to_be_dateutil_parseable": ValidationCategory.VALUE.value,
            "expect_column_values_to_be_json_parseable": ValidationCategory.VALUE.value,
            "expect_column_values_to_be_of_type": ValidationCategory.VALUE.value,
            
            "expect_column_pair_values_to_be_equal": ValidationCategory.CONSISTENCY.value,
            "expect_column_pair_values_A_to_be_greater_than_B": ValidationCategory.CONSISTENCY.value,
            "expect_multicolumn_values_to_be_unique": ValidationCategory.CONSISTENCY.value
        }
        
        return mapping.get(expectation_type, ValidationCategory.UNKNOWN.value)

    def _process_validation_result_legacy(
        self,
        result,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """Process validation result in legacy format.
        
        Args:
            result: Great Expectations validation result
            resource_type: FHIR resource type
            resource_id: FHIR resource ID
            
        Returns:
            Dictionary with validation results
        """
        # Process validation results
        is_valid = result.success
        issues = self._process_validation_results(result)
        
        # Record validation metrics
        validation_result = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "is_valid": is_valid,
            "validation_type": ValidationType.CUSTOM.value,
            "issues": issues
        }
        
        if self.validation_metrics_recorder:
            self.validation_metrics_recorder.record_validation_result(
                resource_type=resource_type,
                is_valid=is_valid,
                validation_type=ValidationType.CUSTOM,
                pipeline_stage=None,
                issues=issues,
                metadata={"expectation_suite": None}
            )
        
        return validation_result


# Common FHIR expectations for resource types
def create_patient_expectations(validator: GreatExpectationsValidator, suite_name: str) -> bool:
    """Create common expectations for Patient resources.
    
    Args:
        validator: GreatExpectationsValidator instance
        suite_name: Name for the expectation suite
        
    Returns:
        True if the expectations were created, False otherwise
    """
    # Create basic structure expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "resourceType"},
        meta={"description": "Resource must have a resourceType"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "resourceType", "value_set": ["Patient"]},
        meta={"description": "resourceType must be Patient"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "id"},
        meta={"description": "Patient must have an id"}
    )
    
    # Add patient-specific expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "name[0].family"},
        meta={"description": "Patient should have a family name"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "name[0].given[0]"},
        meta={"description": "Patient should have a given name"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "gender", "value_set": ["male", "female", "other", "unknown"]},
        meta={"description": "Patient gender must be valid"}
    )
    
    return True


def create_observation_expectations(validator: GreatExpectationsValidator, suite_name: str) -> bool:
    """Create common expectations for Observation resources.
    
    Args:
        validator: GreatExpectationsValidator instance
        suite_name: Name for the expectation suite
        
    Returns:
        True if the expectations were created, False otherwise
    """
    # Create basic structure expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "resourceType"},
        meta={"description": "Resource must have a resourceType"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "resourceType", "value_set": ["Observation"]},
        meta={"description": "resourceType must be Observation"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "id"},
        meta={"description": "Observation must have an id"}
    )
    
    # Add observation-specific expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "status"},
        meta={"description": "Observation must have a status"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "status", "value_set": [
            "registered", "preliminary", "final", "amended", "corrected", 
            "cancelled", "entered-in-error", "unknown"
        ]},
        meta={"description": "Observation status must be valid"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "code"},
        meta={"description": "Observation must have a code"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "subject"},
        meta={"description": "Observation must have a subject"}
    )
    
    return True


def create_medication_request_expectations(validator: GreatExpectationsValidator, suite_name: str) -> bool:
    """Create common expectations for MedicationRequest resources.
    
    Args:
        validator: GreatExpectationsValidator instance
        suite_name: Name for the expectation suite
        
    Returns:
        True if the expectations were created, False otherwise
    """
    # Create basic structure expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "resourceType"},
        meta={"description": "Resource must have a resourceType"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "resourceType", "value_set": ["MedicationRequest"]},
        meta={"description": "resourceType must be MedicationRequest"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "id"},
        meta={"description": "MedicationRequest must have an id"}
    )
    
    # Add medication request-specific expectations
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "status"},
        meta={"description": "MedicationRequest must have a status"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "status", "value_set": [
            "active", "on-hold", "cancelled", "completed", "entered-in-error", 
            "stopped", "draft", "unknown"
        ]},
        meta={"description": "MedicationRequest status must be valid"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "intent"},
        meta={"description": "MedicationRequest must have an intent"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_values_to_be_in_set",
        kwargs={"column": "intent", "value_set": [
            "proposal", "plan", "order", "original-order", "reflex-order",
            "filler-order", "instance-order", "option"
        ]},
        meta={"description": "MedicationRequest intent must be valid"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "subject"},
        meta={"description": "MedicationRequest must have a subject"}
    )
    
    validator.add_expectation(
        suite_name=suite_name,
        expectation_type="expect_column_to_exist",
        kwargs={"column": "medication"},
        meta={"description": "MedicationRequest must have a medication"}
    )
    
    return True 