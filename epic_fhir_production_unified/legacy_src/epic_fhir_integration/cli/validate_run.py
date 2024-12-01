#!/usr/bin/env python3
"""
FHIR Pipeline Run Validation CLI Tool

This tool validates a FHIR pipeline run by analyzing metrics, logs, and outputs
to ensure data quality, performance, and correctness.
"""

import os
import sys
import json
import argparse
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import pandas as pd
import yaml

from epic_fhir_integration.utils.paths import get_latest_test_directory

logger = logging.getLogger(__name__)

# Default validation thresholds
DEFAULT_VALIDATION_THRESHOLDS = {
    "row_count_threshold": 0.99,  # 99% of rows should be preserved
    "performance_thresholds": {
        "extract": 300,    # seconds
        "transform": 600,  # seconds
        "load": 300        # seconds
    },
    "data_quality_thresholds": {
        "completeness": 0.95,     # 95% of required fields should be populated
        "accuracy": 0.98,         # 98% of values should pass validation rules
        "consistency": 0.97       # 97% consistency across related fields
    },
    "resource_usage_thresholds": {
        "memory_percent_max": 90,  # Maximum memory usage percentage
        "cpu_percent_max": 95      # Maximum CPU usage percentage
    }
}

class ValidationConfig:
    """
    Configuration class for validation thresholds and rules.
    
    This class manages threshold values for different validation checks and
    provides methods to load custom configurations from files.
    """
    
    def __init__(
        self, 
        config_file: Optional[Union[str, Path]] = None,
        custom_thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation configuration.
        
        Args:
            config_file: Path to configuration file (optional)
            custom_thresholds: Dictionary of custom thresholds (optional)
        """
        # Start with default thresholds
        self.thresholds = DEFAULT_VALIDATION_THRESHOLDS.copy()
        
        # Load from config file if provided
        if config_file:
            self._load_from_file(config_file)
            
        # Apply custom thresholds if provided
        if custom_thresholds:
            self._apply_custom_thresholds(custom_thresholds)
    
    def _load_from_file(self, config_file: Union[str, Path]) -> None:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Config file {config_path} not found, using default config")
            return
            
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix == '.json':
                    config = json.load(f)
                elif config_path.suffix in ['.yml', '.yaml']:
                    config = yaml.safe_load(f)
                else:
                    logger.warning(f"Unsupported config file format: {config_path.suffix}, using default config")
                    return
                
            # Update thresholds with loaded values
            self._apply_custom_thresholds(config)
            
            logger.info(f"Loaded validation configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    def _apply_custom_thresholds(self, custom_thresholds: Dict[str, Any]) -> None:
        """
        Apply custom threshold values by deep update.
        
        Args:
            custom_thresholds: Dictionary of custom thresholds
        """
        self._deep_update(self.thresholds, custom_thresholds)
        
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively update a nested dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionary
                self._deep_update(target[key], value)
            else:
                # Update or add key-value pair
                target[key] = value
    
    def get_threshold(self, path: str, default: Any = None) -> Any:
        """
        Get a threshold value by dot-notation path.
        
        Args:
            path: Dot-notation path to threshold (e.g., 'performance_thresholds.extract')
            default: Default value if path not found
            
        Returns:
            Threshold value or default if not found
        """
        # Split path into components
        parts = path.split('.')
        
        # Start at top level
        current = self.thresholds
        
        # Traverse path
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
    
    def save_to_file(self, output_path: Union[str, Path]) -> None:
        """
        Save current configuration to file.
        
        Args:
            output_path: Path to save configuration
        """
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w') as f:
                if output_path.suffix == '.json':
                    json.dump(self.thresholds, f, indent=2)
                elif output_path.suffix in ['.yml', '.yaml']:
                    yaml.dump(self.thresholds, f)
                else:
                    # Default to JSON
                    json.dump(self.thresholds, f, indent=2)
                    
            logger.info(f"Saved validation configuration to {output_path}")
        except Exception as e:
            logger.error(f"Error saving config file: {e}")

class RunValidator:
    """
    Validator for FHIR pipeline runs.
    
    This class provides methods for validating a pipeline run by checking metrics,
    logs, and outputs against defined rules.
    """
    
    def __init__(
        self, 
        run_dir: Union[str, Path], 
        config_file: Optional[Union[str, Path]] = None,
        custom_thresholds: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """
        Initialize the run validator.
        
        Args:
            run_dir: Path to the run directory
            config_file: Path to validation config file (optional)
            custom_thresholds: Dictionary of custom thresholds (optional)
            verbose: Whether to output verbose logs
        """
        self.run_dir = Path(run_dir)
        self.verbose = verbose
        
        # Initialize validation configuration
        self.config = ValidationConfig(config_file, custom_thresholds)
        
        # Initialize validation results
        self.validation_results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "run_dir": str(self.run_dir),
            "validation_status": "PENDING",
            "checks": [],
            "overall_result": {
                "success": 0,
                "warning": 0,
                "failure": 0,
                "skipped": 0
            },
            "thresholds_used": self.config.thresholds
        }
        
        # Set up logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def _check_row_parity(self, source: str, target: str) -> Dict[str, Any]:
        """
        Check row count parity between pipeline stages.
        
        Args:
            source: Source stage (e.g., "bronze")
            target: Target stage (e.g., "silver")
            
        Returns:
            Validation result
        """
        metrics_df = self._load_metrics()
        if metrics_df.empty:
            return {
                "status": "SKIPPED",
                "message": f"No metrics found for {source} to {target} comparison"
            }
            
        try:
            # Get threshold from config
            threshold = self.config.get_threshold(
                f"row_count_threshold", 
                DEFAULT_VALIDATION_THRESHOLDS["row_count_threshold"]
            )
            
            # Filter metrics for source and target counts
            source_counts = metrics_df[
                (metrics_df['step'] == source) & 
                (metrics_df['name'].str.contains('count', case=False))
            ]
            target_counts = metrics_df[
                (metrics_df['step'] == target) & 
                (metrics_df['name'].str.contains('count', case=False))
            ]
            
            if source_counts.empty or target_counts.empty:
                return {
                    "status": "SKIPPED",
                    "message": f"Missing {source} or {target} count metrics"
                }
                
            # Calculate total counts
            source_total = source_counts['value'].sum()
            target_total = target_counts['value'].sum()
            
            if source_total == 0:
                return {
                    "status": "WARNING",
                    "message": f"No {source} records found"
                }
                
            # Calculate ratio
            ratio = target_total / source_total
            
            # Check against threshold
            if ratio >= threshold:
                return {
                    "status": "SUCCESS",
                    "message": f"{target.title()} preserved {ratio:.2%} of {source} records (threshold: {threshold:.2%})",
                    "details": {
                        "source_count": int(source_total),
                        "target_count": int(target_total),
                        "ratio": ratio,
                        "threshold": threshold
                    }
                }
            else:
                return {
                    "status": "FAILURE",
                    "message": f"{target.title()} only preserved {ratio:.2%} of {source} records (threshold: {threshold:.2%})",
                    "details": {
                        "source_count": int(source_total),
                        "target_count": int(target_total),
                        "ratio": ratio,
                        "threshold": threshold
                    }
                }
        except Exception as e:
            logger.error(f"Error checking row parity: {e}")
            return {
                "status": "FAILURE",
                "message": f"Error checking row parity: {str(e)}"
            }
            
    def _check_performance(self, step: str) -> Dict[str, Any]:
        """
        Check performance of a pipeline step.
        
        Args:
            step: Pipeline step (e.g., "extract")
            
        Returns:
            Validation result
        """
        metrics_df = self._load_metrics()
        if metrics_df.empty:
            return {
                "status": "SKIPPED",
                "message": f"No metrics found for {step} performance check"
            }
            
        try:
            # Get threshold from config
            threshold = self.config.get_threshold(
                f"performance_thresholds.{step}", 
                self.config.get_threshold("performance_thresholds.default", 600)
            )
            
            # Filter metrics for step duration
            duration_metrics = metrics_df[
                (metrics_df['step'] == step) & 
                (metrics_df['name'].str.contains('duration|time', case=False))
            ]
            
            if duration_metrics.empty:
                return {
                    "status": "SKIPPED",
                    "message": f"No duration metrics found for {step}"
                }
                
            # Get total duration
            total_duration = duration_metrics['value'].sum()
            
            # Check against threshold
            if total_duration <= threshold:
                return {
                    "status": "SUCCESS",
                    "message": f"{step.title()} completed in {total_duration:.2f} seconds (threshold: {threshold:.2f}s)",
                    "details": {
                        "duration": total_duration,
                        "threshold": threshold
                    }
                }
            else:
                return {
                    "status": "WARNING",
                    "message": f"{step.title()} took {total_duration:.2f} seconds, exceeding threshold of {threshold:.2f}s",
                    "details": {
                        "duration": total_duration,
                        "threshold": threshold
                    }
                }
        except Exception as e:
            logger.error(f"Error checking performance: {e}")
            return {
                "status": "FAILURE",
                "message": f"Error checking performance: {str(e)}"
            }
            
    def _check_data_quality(self, resource_type: str) -> Dict[str, Any]:
        """
        Check data quality for a resource type.
        
        Args:
            resource_type: FHIR resource type
            
        Returns:
            Validation result
        """
        metrics_df = self._load_metrics()
        if metrics_df.empty:
            return {
                "status": "SKIPPED",
                "message": f"No metrics found for {resource_type} data quality check"
            }
            
        try:
            # Get threshold from config
            threshold = self.config.get_threshold(
                f"data_quality_thresholds.completeness", 
                DEFAULT_VALIDATION_THRESHOLDS["data_quality_thresholds"]["completeness"]
            )
            
            # Filter metrics for resource quality
            quality_metrics = metrics_df[
                (metrics_df['resource_type'] == resource_type) & 
                (metrics_df['metric_type'] == 'QUALITY')
            ]
            
            if quality_metrics.empty:
                return {
                    "status": "SKIPPED",
                    "message": f"No quality metrics found for {resource_type}"
                }
                
            # Calculate quality score
            quality_score = quality_metrics['value'].mean()
            
            # Check against threshold
            if quality_score >= threshold:
                return {
                    "status": "SUCCESS",
                    "message": f"{resource_type} data quality score: {quality_score:.2%} (threshold: {threshold:.2%})",
                    "details": {
                        "quality_score": quality_score,
                        "threshold": threshold
                    }
                }
            else:
                return {
                    "status": "WARNING",
                    "message": f"{resource_type} data quality score: {quality_score:.2%}, below threshold of {threshold:.2%}",
                    "details": {
                        "quality_score": quality_score,
                        "threshold": threshold
                    }
                }
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
            return {
                "status": "FAILURE",
                "message": f"Error checking data quality: {str(e)}"
            }
            
    def _check_resource_usage(self) -> Dict[str, Any]:
        """
        Check resource usage metrics.
        
        Returns:
            Validation result
        """
        metrics_df = self._load_metrics()
        if metrics_df.empty:
            return {
                "status": "SKIPPED",
                "message": "No metrics found for resource usage check"
            }
            
        try:
            # Get thresholds from config
            memory_threshold = self.config.get_threshold(
                "resource_usage_thresholds.memory_percent_max", 
                DEFAULT_VALIDATION_THRESHOLDS["resource_usage_thresholds"]["memory_percent_max"]
            )
            cpu_threshold = self.config.get_threshold(
                "resource_usage_thresholds.cpu_percent_max", 
                DEFAULT_VALIDATION_THRESHOLDS["resource_usage_thresholds"]["cpu_percent_max"]
            )
            
            # Filter metrics for resource usage
            resource_metrics = metrics_df[
                (metrics_df['metric_type'] == 'RESOURCE')
            ]
            
            if resource_metrics.empty:
                return {
                    "status": "SKIPPED",
                    "message": "No resource usage metrics found"
                }
                
            # Get maximum memory usage
            memory_metrics = resource_metrics[resource_metrics['name'] == 'memory_percent']
            max_memory = memory_metrics['value'].max() if not memory_metrics.empty else 0
            
            # Get maximum CPU usage
            cpu_metrics = resource_metrics[resource_metrics['name'] == 'cpu_percent']
            max_cpu = cpu_metrics['value'].max() if not cpu_metrics.empty else 0
            
            # Check against thresholds
            if max_memory > memory_threshold or max_cpu > cpu_threshold:
                return {
                    "status": "WARNING",
                    "message": f"High resource usage detected: Memory {max_memory:.1f}%, CPU {max_cpu:.1f}%",
                    "details": {
                        "max_memory_percent": max_memory,
                        "max_cpu_percent": max_cpu,
                        "memory_threshold": memory_threshold,
                        "cpu_threshold": cpu_threshold
                    }
                }
            else:
                return {
                    "status": "SUCCESS",
                    "message": f"Resource usage within limits: Memory {max_memory:.1f}%, CPU {max_cpu:.1f}%",
                    "details": {
                        "max_memory_percent": max_memory,
                        "max_cpu_percent": max_cpu,
                        "memory_threshold": memory_threshold,
                        "cpu_threshold": cpu_threshold
                    }
                }
        except Exception as e:
            logger.error(f"Error checking resource usage: {e}")
            return {
                "status": "FAILURE",
                "message": f"Error checking resource usage: {str(e)}"
            }
            
    def _load_metrics(self) -> pd.DataFrame:
        """
        Load metrics from the run directory.
        
        Returns:
            DataFrame containing metrics
        """
        metrics_path = self.run_dir / "metrics" / "performance_metrics.parquet"
        transform_metrics_path = self.run_dir / "metrics" / "transform_metrics.parquet"
        
        dfs = []
        
        # Load performance metrics if available
        if metrics_path.exists():
            try:
                metrics_df = pd.read_parquet(metrics_path)
                logger.debug(f"Loaded {len(metrics_df)} performance metrics")
                dfs.append(metrics_df)
            except Exception as e:
                logger.error(f"Error loading performance metrics: {e}")
        
        # Load transform metrics if available
        if transform_metrics_path.exists():
            try:
                transform_df = pd.read_parquet(transform_metrics_path)
                logger.debug(f"Loaded {len(transform_df)} transform metrics")
                
                # Convert to common format if possible
                if 'resource_type' in transform_df.columns:
                    # Rename columns to match performance metrics
                    transform_df = transform_df.rename(columns={
                        'input_record_count': 'value',
                        'transform_status': 'status'
                    })
                    # Add missing columns
                    transform_df['step'] = 'transform'
                    transform_df['name'] = 'input_count'
                    transform_df['metric_type'] = 'TRANSFORM'
                    
                dfs.append(transform_df)
            except Exception as e:
                logger.error(f"Error loading transform metrics: {e}")
        
        # Combine metrics
        if not dfs:
            logger.warning("No metrics found")
            return pd.DataFrame()
            
        return pd.concat(dfs, ignore_index=True)

    def run_validation(self) -> Dict[str, Any]:
        """
        Run validation checks on the pipeline output.
        
        Returns:
            Validation results
        """
        logger.info(f"Running validation on {self.run_dir}")
        
        # List of validation checks to run
        validation_checks = [
            {
                "name": "bronze_to_silver_row_parity",
                "description": "Check that row counts are preserved from bronze to silver",
                "check_function": self._check_row_parity,
                "args": ["bronze", "silver"],
                "severity": "error"
            },
            {
                "name": "silver_to_gold_row_parity",
                "description": "Check that row counts are properly aggregated from silver to gold",
                "check_function": self._check_row_parity,
                "args": ["silver", "gold"],
                "severity": "warning"
            },
            {
                "name": "extract_performance",
                "description": "Check extraction performance",
                "check_function": self._check_performance,
                "args": ["extract"],
                "severity": "warning"
            },
            {
                "name": "transform_performance",
                "description": "Check transformation performance",
                "check_function": self._check_performance,
                "args": ["transform"],
                "severity": "warning"
            },
            {
                "name": "resource_usage",
                "description": "Check resource usage",
                "check_function": self._check_resource_usage,
                "args": [],
                "severity": "warning"
            }
        ]
        
        # Run each validation check
        for check in validation_checks:
            logger.info(f"Running validation check: {check['name']}")
            
            try:
                # Run check function with arguments
                result = check["check_function"](*check["args"])
                
                # Add check metadata
                result["name"] = check["name"]
                result["description"] = check["description"]
                result["severity"] = check["severity"]
                
                # Update result counts
                self.validation_results["overall_result"][result["status"].lower()] += 1
                
                # Add to checks list
                self.validation_results["checks"].append(result)
                
                logger.info(f"Check {check['name']}: {result['status']} - {result['message']}")
            except Exception as e:
                logger.error(f"Error running check {check['name']}: {e}")
                
                # Add error result
                error_result = {
                    "name": check["name"],
                    "description": check["description"],
                    "severity": check["severity"],
                    "status": "FAILURE",
                    "message": f"Error running check: {str(e)}"
                }
                
                # Update result counts
                self.validation_results["overall_result"]["failure"] += 1
                
                # Add to checks list
                self.validation_results["checks"].append(error_result)
        
        # Determine overall validation status
        if self.validation_results["overall_result"]["failure"] > 0:
            self.validation_results["validation_status"] = "FAILED"
        elif self.validation_results["overall_result"]["warning"] > 0:
            self.validation_results["validation_status"] = "WARNING"
        elif self.validation_results["overall_result"]["success"] > 0:
            self.validation_results["validation_status"] = "SUCCESS"
        else:
            self.validation_results["validation_status"] = "SKIPPED"
            
        logger.info(f"Validation completed with status: {self.validation_results['validation_status']}")
        
        return self.validation_results
        
    def write_results(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Write validation results to file.
        
        Args:
            output_path: Path to output file (optional)
            
        Returns:
            Path to output file
        """
        if output_path is None:
            # Default to run directory
            output_path = self.run_dir / "validation" / "results.json"
        else:
            output_path = Path(output_path)
            
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp if not already present
        if "timestamp" not in self.validation_results:
            self.validation_results["timestamp"] = datetime.datetime.now().isoformat()
            
        # Write results
        with open(output_path, "w") as f:
            json.dump(self.validation_results, f, indent=2)
            
        logger.info(f"Validation results written to {output_path}")
        
        # Also save the thresholds used to a separate file
        thresholds_path = output_path.parent / "thresholds.json"
        try:
            with open(thresholds_path, "w") as f:
                json.dump(self.config.thresholds, f, indent=2)
            logger.info(f"Validation thresholds written to {thresholds_path}")
        except Exception as e:
            logger.error(f"Error writing validation thresholds: {e}")
            
        return output_path

def main():
    """Main entry point for the validation CLI."""
    parser = argparse.ArgumentParser(
        description="Validate FHIR pipeline run"
    )
    parser.add_argument(
        "--run-dir",
        help="Path to run directory"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use latest run directory"
    )
    parser.add_argument(
        "--output-dir",
        help="Base output directory (used with --latest)"
    )
    parser.add_argument(
        "--config",
        help="Path to validation configuration file"
    )
    parser.add_argument(
        "--save-config",
        help="Save current configuration to file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Custom threshold arguments
    parser.add_argument(
        "--row-count-threshold",
        type=float,
        help="Row count parity threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--extract-time-threshold",
        type=float,
        help="Extraction time threshold in seconds"
    )
    parser.add_argument(
        "--transform-time-threshold",
        type=float,
        help="Transformation time threshold in seconds"
    )
    
    args = parser.parse_args()
    
    # Determine run directory
    run_dir = None
    if args.run_dir:
        run_dir = Path(args.run_dir)
    elif args.latest:
        if args.output_dir:
            base_dir = Path(args.output_dir)
        else:
            base_dir = Path("output")
            
        try:
            run_dir = get_latest_test_directory(base_dir)
            if run_dir is None:
                print(f"No test directories found in {base_dir}")
                return 1
        except Exception as e:
            print(f"Error finding latest test directory: {e}")
            return 1
    else:
        # Default to current working directory
        run_dir = Path.cwd()
        
    print(f"Using run directory: {run_dir}")
    
    # Prepare custom thresholds
    custom_thresholds = {}
    if args.row_count_threshold is not None:
        custom_thresholds["row_count_threshold"] = args.row_count_threshold
        
    if args.extract_time_threshold is not None or args.transform_time_threshold is not None:
        custom_thresholds["performance_thresholds"] = {}
        
        if args.extract_time_threshold is not None:
            custom_thresholds["performance_thresholds"]["extract"] = args.extract_time_threshold
            
        if args.transform_time_threshold is not None:
            custom_thresholds["performance_thresholds"]["transform"] = args.transform_time_threshold
    
    # Run validation
    validator = RunValidator(
        run_dir=run_dir,
        config_file=args.config,
        custom_thresholds=custom_thresholds,
        verbose=args.verbose
    )
    
    # Save configuration if requested
    if args.save_config:
        validator.config.save_to_file(args.save_config)
    
    # Run validation
    validation_results = validator.run_validation()
    
    # Write results
    validator.write_results()
    
    # Print results summary
    print("\nValidation Results Summary:")
    print(f"Status: {validation_results['validation_status']}")
    print(f"Checks: {len(validation_results['checks'])}")
    print(f"Successes: {validation_results['overall_result']['success']}")
    print(f"Warnings: {validation_results['overall_result']['warning']}")
    print(f"Failures: {validation_results['overall_result']['failure']}")
    print(f"Skipped: {validation_results['overall_result']['skipped']}")
    
    # Return exit code based on validation status
    if validation_results["validation_status"] == "FAILED":
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main()) 