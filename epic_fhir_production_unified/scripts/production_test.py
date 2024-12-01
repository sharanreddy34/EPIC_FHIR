#!/usr/bin/env python3
"""
Production-ready test script for Epic-FHIR integration.

This script tests the entire pipeline with a single patient:
1. Authentication with Epic
2. Patient data extraction
3. Bronze-to-Silver transformation
4. Silver-to-Gold transformation
5. Verification, validation and reporting

Usage:
    python production_test.py --patient-id ID [--output-dir DIR] [--debug]
"""

import os
import sys
import time
import json
import argparse
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Import path utilities
from epic_fhir_integration.utils.paths import (
    get_run_root, 
    create_dataset_structure,
    create_run_metadata,
    update_run_metadata,
    cleanup_old_test_directories
)

# Import metrics collector
from epic_fhir_integration.metrics.collector import (
    record_metric,
    flush_metrics,
    record_metrics_batch
)

# Import validator
from epic_fhir_integration.cli.validate_run import RunValidator

# Import retry utilities
from epic_fhir_integration.utils.retry import (
    retry_on_exceptions,
    retry_api_call,
    is_transient_error
)

# Import disk space monitoring
from epic_fhir_integration.utils.disk_monitor import (
    check_disk_space,
    start_disk_monitoring,
    stop_disk_monitoring
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("epic_fhir_test")

def setup_logging(debug_mode, directories):
    """Set up logging to file."""
    # Get logs directory
    logs_dir = directories["logs"]
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"test_{timestamp}.log"
    
    # Set up file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Set logging level
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logger.setLevel(log_level)
    file_handler.setLevel(log_level)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    logger.info(f"Logging to {log_file}")
    return log_file

def get_authentication_token(verbose=False):
    """Get an authentication token from Epic."""
    logger.info("Getting authentication token...")
    start_time = time.time()
    
    try:
        from epic_fhir_integration.auth.custom_auth import get_token
        
        # Get token
        token = get_token()
        
        # Record metric
        elapsed = time.time() - start_time
        record_metric("auth", "authentication_time", elapsed, metric_type="RUNTIME")
        
        if token:
            logger.info("Successfully obtained authentication token")
            record_metric("auth", "authentication_success", 1)
            
            if verbose:
                logger.debug(f"Token: {token[:30]}...")
            return token
        else:
            logger.error("Failed to get authentication token")
            record_metric("auth", "authentication_success", 0)
            return None
    except Exception as e:
        logger.error(f"Error getting authentication token: {e}")
        logger.debug(traceback.format_exc())
        
        # Record error metric
        elapsed = time.time() - start_time
        record_metric("auth", "authentication_time", elapsed, metric_type="RUNTIME")
        record_metric("auth", "authentication_success", 0)
        record_metric("auth", "authentication_error", str(e), metric_type="ERROR")
        
        return None

def extract_patient_data(patient_id, directories, debug_mode=False, max_retries=3):
    """Extract patient data using our custom FHIR client."""
    logger.info(f"Extracting data for patient ID: {patient_id}")
    start_time = time.time()
    
    try:
        from epic_fhir_integration.io.custom_fhir_client import create_epic_fhir_client
        
        # Create client
        client = create_epic_fhir_client()
        logger.info(f"Connected to FHIR server: {client.base_url}")
        
        # Record client connection metric
        record_metric("extract", "client_connection", 1)
        
        # Extract patient data with retries for transient errors
        @retry_on_exceptions(
            max_retries=max_retries,
            should_retry_func=is_transient_error,
            on_retry=lambda attempt, e, delay: logger.warning(
                f"API call attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
        )
        def get_patient_data_with_retry():
            return client.get_patient_data(patient_id)
        
        # Make the API call with retries
        patient_data = get_patient_data_with_retry()
        
        # Check disk space before saving data
        has_space, disk_space = check_disk_space(
            directories["bronze"], 
            min_free_gb=1.0  # Require at least 1GB free
        )
        
        if not has_space:
            raise IOError(
                f"Insufficient disk space to save data: {disk_space['free_gb']:.2f} GB free. "
                f"At least 1.0 GB required."
            )
        
        # Record resource count metrics in batch for efficiency
        metrics_batch = []
        for resource_type, resources in patient_data.items():
            count = len(resources)
            logger.info(f"Extracted {count} {resource_type} resources")
            
            # Add count metric
            metrics_batch.append({
                "step": "bronze",
                "name": f"{resource_type}_count",
                "value": count,
                "resource_type": resource_type
            })
            
            # Add size metric if feasible
            try:
                import sys
                size = sys.getsizeof(json.dumps(resources))
                metrics_batch.append({
                    "step": "bronze",
                    "name": f"{resource_type}_bytes",
                    "value": size,
                    "resource_type": resource_type
                })
            except Exception as e:
                logger.warning(f"Could not calculate size for {resource_type}: {e}")
        
        # Record metrics in batch
        if metrics_batch:
            record_metrics_batch(metrics_batch)
        
        # Save to bronze layer
        bronze_dir = directories["bronze"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = bronze_dir / f"patient_{patient_id}_{timestamp}.json"
        
        with open(output_file, "w") as f:
            json.dump(patient_data, f, indent=2)
        
        logger.info(f"Saved raw data to: {output_file}")
        
        # Record extraction success and time metrics
        elapsed = time.time() - start_time
        logger.info(f"Extraction completed in {elapsed:.2f} seconds")
        record_metric("extract", "extraction_time", elapsed, metric_type="RUNTIME")
        record_metric("extract", "extraction_success", 1)
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return True, patient_data, output_file
    except Exception as e:
        logger.error(f"Error extracting patient data: {e}")
        logger.debug(traceback.format_exc())
        
        # Record extraction failure metrics
        elapsed = time.time() - start_time
        record_metric("extract", "extraction_time", elapsed, metric_type="RUNTIME")
        record_metric("extract", "extraction_success", 0)
        record_metric("extract", "extraction_error", str(e), metric_type="ERROR")
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return False, None, None

def transform_to_silver(bronze_file, directories, debug_mode=False):
    """Transform bronze data to silver format."""
    logger.info(f"Transforming bronze data to silver: {bronze_file}")
    start_time = time.time()
    silver_dir = directories["silver"]
    
    try:
        # For production, we would use pyspark here
        # For this test, we'll create a simplified CSV representation
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Record pre-transformation metric
        record_metric("transform", "bronze_to_silver_start", timestamp)
        
        # Load the bronze data
        with open(bronze_file, "r") as f:
            patient_data = json.load(f)
        
        # Record input counts for each resource type
        for resource_type, resources in patient_data.items():
            record_metric(
                "transform", 
                f"{resource_type}_input_count", 
                len(resources),
                resource_type=resource_type
            )
        
        # Create silver files for each resource type
        silver_file_counts = {}
        
        for resource_type, resources in patient_data.items():
            if not resources:
                continue
                
            # Create a simple flattened representation
            silver_file = silver_dir / f"{resource_type.lower()}_{timestamp}.csv"
            row_count = 0
            
            with open(silver_file, "w") as f:
                # Write header
                if resource_type == "Patient" and resources:
                    # Patient-specific headers
                    headers = ["id", "name", "gender", "birthDate"]
                    f.write(",".join(headers) + "\n")
                    
                    # Write data
                    for resource in resources:
                        id_val = resource.get("id", "")
                        gender = resource.get("gender", "")
                        birth_date = resource.get("birthDate", "")
                        
                        # Handle name
                        name = ""
                        if "name" in resource and resource["name"]:
                            name_obj = resource["name"][0]
                            given = " ".join(name_obj.get("given", []))
                            family = name_obj.get("family", "")
                            name = f"{given} {family}".strip()
                        
                        f.write(f"{id_val},{name},{gender},{birth_date}\n")
                        row_count += 1
                
                elif resource_type == "Observation" and resources:
                    # Observation-specific headers
                    headers = ["id", "patient", "code", "value", "date"]
                    f.write(",".join(headers) + "\n")
                    
                    # Write data
                    for resource in resources:
                        id_val = resource.get("id", "")
                        
                        # Get patient reference
                        patient = ""
                        if "subject" in resource and "reference" in resource["subject"]:
                            patient = resource["subject"]["reference"].replace("Patient/", "")
                        
                        # Get code
                        code = ""
                        if "code" in resource and "coding" in resource["code"] and resource["code"]["coding"]:
                            code = resource["code"]["coding"][0].get("code", "")
                        
                        # Get value
                        value = ""
                        if "valueQuantity" in resource:
                            value = resource["valueQuantity"].get("value", "")
                        
                        # Get date
                        date = resource.get("effectiveDateTime", "")
                        
                        f.write(f"{id_val},{patient},{code},{value},{date}\n")
                        row_count += 1
                
                else:
                    # Generic approach for other resources
                    headers = ["id", "resourceType"]
                    f.write(",".join(headers) + "\n")
                    
                    for resource in resources:
                        id_val = resource.get("id", "")
                        f.write(f"{id_val},{resource_type}\n")
                        row_count += 1
            
            logger.info(f"Created silver file: {silver_file} with {row_count} rows")
            silver_file_counts[resource_type] = row_count
            
            # Record output count for this resource type
            record_metric(
                "silver", 
                f"{resource_type}_output_count", 
                row_count,
                resource_type=resource_type
            )
        
        # Compare input and output counts for each resource type
        for resource_type, input_count in [(rt, len(res)) for rt, res in patient_data.items() if len(res) > 0]:
            output_count = silver_file_counts.get(resource_type, 0)
            
            # Check for row count discrepancies
            if output_count != input_count:
                logger.warning(
                    f"Row count discrepancy for {resource_type}: "
                    f"Input={input_count}, Output={output_count}"
                )
                record_metric(
                    "validation", 
                    f"{resource_type}_row_count_match", 
                    0,
                    resource_type=resource_type,
                    details={
                        "input_count": input_count,
                        "output_count": output_count,
                        "ratio": output_count / input_count if input_count > 0 else 0
                    }
                )
            else:
                logger.info(f"Row counts match for {resource_type}: {input_count}")
                record_metric(
                    "validation", 
                    f"{resource_type}_row_count_match", 
                    1,
                    resource_type=resource_type,
                    details={
                        "input_count": input_count,
                        "output_count": output_count,
                        "ratio": 1.0
                    }
                )
        
        # Record transformation success and time metrics
        elapsed = time.time() - start_time
        logger.info(f"Bronze-to-silver transformation completed in {elapsed:.2f} seconds")
        record_metric("transform", "bronze_to_silver_time", elapsed, metric_type="RUNTIME")
        record_metric("transform", "bronze_to_silver_success", 1)
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return True
    except Exception as e:
        logger.error(f"Error transforming to silver: {e}")
        logger.debug(traceback.format_exc())
        
        # Record transformation failure metrics
        elapsed = time.time() - start_time
        record_metric("transform", "bronze_to_silver_time", elapsed, metric_type="RUNTIME")
        record_metric("transform", "bronze_to_silver_success", 0)
        record_metric("transform", "bronze_to_silver_error", str(e), metric_type="ERROR")
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return False

def transform_to_gold(directories, debug_mode=False):
    """Transform silver data to gold format."""
    logger.info(f"Transforming silver data to gold")
    start_time = time.time()
    silver_dir = directories["silver"]
    gold_dir = directories["gold"]
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Record pre-transformation metric
        record_metric("transform", "silver_to_gold_start", timestamp)
        
        # In a real implementation, this would use Spark transformations
        # For this test, we'll create simple summary files
        
        # Create patient summary
        patient_files = list(silver_dir.glob("patient_*.csv"))
        patient_row_count = 0
        
        if patient_files:
            gold_file = gold_dir / f"patient_summary_{timestamp}.csv"
            
            # Record input counts
            for patient_file in patient_files:
                with open(patient_file, 'r') as f:
                    # Count rows (subtract 1 for header)
                    row_count = sum(1 for _ in f) - 1
                    patient_row_count += row_count
                    
            record_metric(
                "transform", 
                "patient_input_count", 
                patient_row_count,
                resource_type="Patient"
            )
            
            # Simply copy for now as a demo
            import shutil
            shutil.copy(patient_files[0], gold_file)
            
            # Count rows in output file
            with open(gold_file, 'r') as f:
                # Count rows (subtract 1 for header)
                output_row_count = sum(1 for _ in f) - 1
                
            record_metric(
                "gold", 
                "patient_output_count", 
                output_row_count,
                resource_type="Patient"
            )
            
            logger.info(f"Created gold file: {gold_file} with {output_row_count} rows")
            
            # Check for row count discrepancies
            if output_row_count != patient_row_count:
                logger.warning(
                    f"Row count discrepancy for Patient gold transformation: "
                    f"Input={patient_row_count}, Output={output_row_count}"
                )
                record_metric(
                    "validation", 
                    "patient_gold_row_count_match", 
                    0,
                    resource_type="Patient",
                    details={
                        "input_count": patient_row_count,
                        "output_count": output_row_count,
                        "ratio": output_row_count / patient_row_count if patient_row_count > 0 else 0
                    }
                )
            else:
                logger.info(f"Row counts match for Patient gold transformation: {patient_row_count}")
                record_metric(
                    "validation", 
                    "patient_gold_row_count_match", 
                    1,
                    resource_type="Patient",
                    details={
                        "input_count": patient_row_count,
                        "output_count": output_row_count,
                        "ratio": 1.0
                    }
                )
        
        # Create observation summary
        observation_files = list(silver_dir.glob("observation_*.csv"))
        observation_row_count = 0
        
        if observation_files:
            gold_file = gold_dir / f"observation_summary_{timestamp}.csv"
            
            # Record input counts
            for observation_file in observation_files:
                with open(observation_file, 'r') as f:
                    # Count rows (subtract 1 for header)
                    row_count = sum(1 for _ in f) - 1
                    observation_row_count += row_count
                    
            record_metric(
                "transform", 
                "observation_input_count", 
                observation_row_count,
                resource_type="Observation"
            )
            
            # Simply copy the first file for now
            import shutil
            shutil.copy(observation_files[0], gold_file)
            
            # Count rows in output file
            with open(gold_file, 'r') as f:
                # Count rows (subtract 1 for header)
                output_row_count = sum(1 for _ in f) - 1
                
            record_metric(
                "gold", 
                "observation_output_count", 
                output_row_count,
                resource_type="Observation"
            )
            
            logger.info(f"Created gold file: {gold_file} with {output_row_count} rows")
        
            # Check for row count discrepancies
            if output_row_count != observation_row_count:
                logger.warning(
                    f"Row count discrepancy for Observation gold transformation: "
                    f"Input={observation_row_count}, Output={output_row_count}"
                )
                record_metric(
                    "validation", 
                    "observation_gold_row_count_match", 
                    0,
                    resource_type="Observation",
                    details={
                        "input_count": observation_row_count,
                        "output_count": output_row_count,
                        "ratio": output_row_count / observation_row_count if observation_row_count > 0 else 0
                    }
                )
            else:
                logger.info(f"Row counts match for Observation gold transformation: {observation_row_count}")
                record_metric(
                    "validation", 
                    "observation_gold_row_count_match", 
                    1,
                    resource_type="Observation",
                    details={
                        "input_count": observation_row_count,
                        "output_count": output_row_count,
                        "ratio": 1.0
                    }
                )
        
        # Record transformation success and time metrics
        elapsed = time.time() - start_time
        logger.info(f"Silver-to-gold transformation completed in {elapsed:.2f} seconds")
        record_metric("transform", "silver_to_gold_time", elapsed, metric_type="RUNTIME")
        record_metric("transform", "silver_to_gold_success", 1)
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return True
    except Exception as e:
        logger.error(f"Error transforming to gold: {e}")
        logger.debug(traceback.format_exc())
        
        # Record transformation failure metrics
        elapsed = time.time() - start_time
        record_metric("transform", "silver_to_gold_time", elapsed, metric_type="RUNTIME")
        record_metric("transform", "silver_to_gold_success", 0)
        record_metric("transform", "silver_to_gold_error", str(e), metric_type="ERROR")
        
        # Flush metrics to disk
        flush_metrics(directories["metrics"])
        
        return False

def validate_pipeline_run(run_dir, debug_mode=False):
    """Run validation checks on the pipeline output."""
    logger.info(f"Validating pipeline run in {run_dir}")
    start_time = time.time()
    
    try:
        # Create validator
        validator = RunValidator(run_dir, verbose=debug_mode)
        
        # Run validation
        validation_results = validator.run_validation()
        
        # Write results
        result_file = validator.write_results()
        
        # Record validation metrics
        status = validation_results["validation_status"]
        record_metric("validation", "status", status)
        record_metric("validation", "success_count", validation_results["overall_result"]["success"])
        record_metric("validation", "warning_count", validation_results["overall_result"]["warning"])
        record_metric("validation", "failure_count", validation_results["overall_result"]["failure"])
        record_metric("validation", "skipped_count", validation_results["overall_result"]["skipped"])
        
        # Record validation time
        elapsed = time.time() - start_time
        record_metric("validation", "validation_time", elapsed, metric_type="RUNTIME")
        
        # Flush metrics to disk
        flush_metrics(Path(run_dir) / "metrics")
        
        logger.info(f"Validation completed with status: {status}")
        logger.info(f"Validation results written to: {result_file}")
        
        # Update run metadata
        update_run_metadata(
            run_dir, 
            validation={
                "status": status,
                "success": validation_results["overall_result"]["success"],
                "warning": validation_results["overall_result"]["warning"],
                "failure": validation_results["overall_result"]["failure"],
                "skipped": validation_results["overall_result"]["skipped"],
                "result_file": str(result_file)
            }
        )
        
        # Return True if validation passed (no failures)
        return validation_results["overall_result"]["failure"] == 0, validation_results
    except Exception as e:
        logger.error(f"Error validating pipeline run: {e}")
        logger.debug(traceback.format_exc())
        
        # Record validation failure
        elapsed = time.time() - start_time
        record_metric("validation", "validation_time", elapsed, metric_type="RUNTIME")
        record_metric("validation", "status", "ERROR")
        record_metric("validation", "error", str(e), metric_type="ERROR")
        
        # Flush metrics to disk
        flush_metrics(Path(run_dir) / "metrics")
        
        return False, None

def generate_report(patient_id, patient_data, directories, steps_status, validation_results=None):
    """Generate a comprehensive test report."""
    logger.info("Generating test report")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = directories["reports"]
        
        report_file = reports_dir / f"test_report_{patient_id}_{timestamp}.md"
        
        with open(report_file, "w") as f:
            f.write(f"# Epic FHIR Integration Test Report\n\n")
            f.write(f"## Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Patient ID: {patient_id}\n\n")
            
            # Test steps results
            f.write("## Test Steps Results\n\n")
            
            for step, status in steps_status.items():
                status_icon = "✅" if status else "❌"
                f.write(f"- {status_icon} {step}\n")
            
            f.write("\n")
            
            # Resource summary
            if patient_data:
                f.write("## Resources Retrieved\n\n")
                
                for resource_type, resources in patient_data.items():
                    f.write(f"- {resource_type}: {len(resources)} resources\n")
                
                f.write("\n")
                
                # Patient information
                if "Patient" in patient_data and patient_data["Patient"]:
                    patient = patient_data["Patient"][0]
                    f.write("## Patient Information\n\n")
                    
                    # Name
                    if "name" in patient and patient["name"]:
                        name = patient["name"][0]
                        given = " ".join(name.get("given", ["Unknown"]))
                        family = name.get("family", "Unknown")
                        f.write(f"- Name: {given} {family}\n")
                    
                    # Gender
                    if "gender" in patient:
                        f.write(f"- Gender: {patient['gender']}\n")
                    
                    # Birth date
                    if "birthDate" in patient:
                        f.write(f"- Birth Date: {patient['birthDate']}\n")
                    
                    f.write("\n")
            
            # Validation results
            if validation_results:
                f.write("## Validation Results\n\n")
                f.write(f"- Status: {validation_results['validation_status']}\n")
                f.write(f"- Success: {validation_results['overall_result']['success']}\n")
                f.write(f"- Warnings: {validation_results['overall_result']['warning']}\n")
                f.write(f"- Failures: {validation_results['overall_result']['failure']}\n")
                f.write(f"- Skipped: {validation_results['overall_result']['skipped']}\n\n")
                
                # Include validation checks
                f.write("### Validation Checks\n\n")
                for check in validation_results['checks']:
                    status_icon = "✅" if check['status'] == "SUCCESS" else "⚠️" if check['status'] == "WARNING" else "❌" if check['status'] == "FAILURE" else "⏭️"
                    f.write(f"- {status_icon} {check['name']}: {check['message']}\n")
                
                f.write("\n")
            
            # Performance metrics
            f.write("## Performance Metrics\n\n")
            
            try:
                # Load metrics
                metrics_file = directories["metrics"] / "performance_metrics.parquet"
                if metrics_file.exists():
                    metrics_df = pd.read_parquet(metrics_file)
                    
                    # Filter runtime metrics
                    runtime_metrics = metrics_df[metrics_df['metric_type'] == 'RUNTIME']
                    
                    if not runtime_metrics.empty:
                        for _, metric in runtime_metrics.iterrows():
                            if 'time' in metric['name'] or 'duration' in metric['name']:
                                f.write(f"- {metric['step'].title()} {metric['name']}: {metric['value']:.2f} seconds\n")
                
                f.write("\n")
            except Exception as e:
                logger.warning(f"Could not include metrics in report: {e}")
            
            # Overall result
            overall_success = all(steps_status.values())
            validation_passed = steps_status.get('Validation', True)  # If validation step exists, use its status
            result = "SUCCESS" if overall_success and validation_passed else "FAILURE"
            f.write(f"## Overall Test Result: {result}\n")
        
        logger.info(f"Test report generated: {report_file}")
        return report_file
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        logger.debug(traceback.format_exc())
        return None

def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run production test for Epic FHIR integration")
    parser.add_argument("--patient-id", required=True, help="Patient ID to use for testing")
    parser.add_argument("--output-dir", default="output/production_test", help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--keep-tests", type=int, default=5, help="Number of test directories to keep")
    parser.add_argument("--min-disk-space", type=float, default=10.0, help="Minimum free disk space in GB")
    parser.add_argument("--monitor-disk", action="store_true", help="Enable disk space monitoring")
    parser.add_argument("--retry-count", type=int, default=3, help="Maximum number of retries for API calls")
    args = parser.parse_args()
    
    # Convert output directory to Path
    output_dir = Path(args.output_dir)
    
    # Check disk space before starting
    has_space, disk_space = check_disk_space(output_dir, min_free_gb=args.min_disk_space)
    if not has_space:
        logger.error(
            f"Insufficient disk space: {disk_space['free_gb']:.2f} GB free, "
            f"minimum required: {args.min_disk_space:.2f} GB"
        )
        return 1
    
    logger.info(f"Disk space check passed: {disk_space['free_gb']:.2f} GB free")
    
    # Start disk space monitoring if requested
    if args.monitor_disk:
        logger.info("Starting disk space monitoring")
        monitor = start_disk_monitoring(
            path=output_dir,
            min_free_gb=args.min_disk_space,
            warning_threshold_gb=args.min_disk_space * 1.5,
            check_interval=300,  # 5 minutes
            auto_cleanup=True
        )
    
    # Track step status
    steps_status = {
        "Authentication": False,
        "Data Extraction": False,
        "Bronze to Silver Transformation": False,
        "Silver to Gold Transformation": False,
        "Validation": False
    }
    
    # Create test directory structure using utility function
    directories = create_dataset_structure(output_dir)
    run_dir = directories["bronze"].parent  # Get the test run root directory
    
    # Create run metadata with patient ID
    create_run_metadata(
        run_dir,
        params={
            "patient_id": args.patient_id,
            "debug_mode": args.debug,
            "retry_count": args.retry_count,
            "disk_space": {
                "initial_free_gb": disk_space["free_gb"],
                "min_required_gb": args.min_disk_space
            }
        }
    )
    
    # Setup logging to the test-specific logs directory
    log_file = setup_logging(args.debug, directories)
    logger.info(f"Starting production test for patient ID: {args.patient_id}")
    logger.info(f"Test directory: {run_dir}")
    
    # Initialize validation results
    validation_results = None
    
    try:
        # Step 1: Authentication
        token = get_authentication_token(verbose=args.debug)
        steps_status["Authentication"] = token is not None
        
        if not token:
            logger.error("Authentication failed - cannot proceed with test")
            update_run_metadata(run_dir, end_run=True, status="FAILED", error="Authentication failed")
            generate_report(args.patient_id, None, directories, steps_status)
            return 1
        
        # Step 2: Extract patient data
        success, patient_data, bronze_file = extract_patient_data(
            args.patient_id, 
            directories, 
            args.debug,
            max_retries=args.retry_count
        )
        steps_status["Data Extraction"] = success
        
        if not success:
            logger.error("Data extraction failed - cannot proceed with test")
            update_run_metadata(run_dir, end_run=True, status="FAILED", error="Data extraction failed")
            generate_report(args.patient_id, None, directories, steps_status)
            return 1
        
        # Step 3: Transform to silver
        success = transform_to_silver(
            bronze_file, 
            directories, 
            args.debug
        )
        steps_status["Bronze to Silver Transformation"] = success
        
        if not success:
            logger.error("Bronze to silver transformation failed - cannot proceed with gold transformation")
            update_run_metadata(run_dir, end_run=True, status="FAILED", error="Bronze to silver transformation failed")
            generate_report(args.patient_id, patient_data, directories, steps_status)
            return 1
        
        # Step 4: Transform to gold
        success = transform_to_gold(
            directories, 
            args.debug
        )
        steps_status["Silver to Gold Transformation"] = success
        
        # Step 5: Validate the pipeline run
        validation_success, validation_results = validate_pipeline_run(run_dir, args.debug)
        steps_status["Validation"] = validation_success
        
        # Update run metadata with status
        overall_success = all(steps_status.values())
        status = "SUCCESS" if overall_success else "PARTIAL_SUCCESS" if steps_status["Data Extraction"] else "FAILED"
        
        update_run_metadata(
            run_dir, 
            end_run=True, 
            status=status,
            steps_status=steps_status
        )
        
        # Generate final report including validation results
        report_file = generate_report(
            args.patient_id, 
            patient_data, 
            directories, 
            steps_status,
            validation_results
        )
        
        # Clean up old test directories
        if args.keep_tests > 0:
            removed = cleanup_old_test_directories(output_dir, keep_latest=args.keep_tests)
            if removed:
                logger.info(f"Cleaned up {len(removed)} old test directories")
        
        # Print summary
        print("\n" + "="*80)
        print("EPIC FHIR INTEGRATION TEST SUMMARY")
        print("="*80)
        print(f"Patient ID: {args.patient_id}")
        print(f"Test directory: {run_dir}")
        
        # Print step status
        for step, status in steps_status.items():
            status_str = "✓ PASS" if status else "✗ FAIL"
            print(f"{step:40s} {status_str}")
        
        # Print overall result
        overall_success = all(steps_status.values())
        result = "SUCCESS" if overall_success else "FAILURE"
        print("-"*80)
        print(f"Overall Result: {result}")
        
        if validation_results:
            print(f"Validation Status: {validation_results['validation_status']}")
            print(f"Validation Results: {validation_results['overall_result']['success']} success, "
                  f"{validation_results['overall_result']['warning']} warnings, "
                  f"{validation_results['overall_result']['failure']} failures")
        
        if report_file:
            print(f"Detailed report: {report_file}")
        
        print(f"Log file: {log_file}")
        print("="*80)
        
        # Stop disk monitoring if enabled
        if args.monitor_disk:
            logger.info("Stopping disk space monitoring")
            stop_disk_monitoring()
        
        return 0 if overall_success else 1
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.debug(traceback.format_exc())
        
        # Update run metadata with error
        update_run_metadata(
            run_dir, 
            end_run=True, 
            status="ERROR",
            error=str(e)
        )
        
        # Try to generate report even after error
        generate_report(args.patient_id, None, directories, steps_status, validation_results)
        
        # Stop disk monitoring if enabled
        if args.monitor_disk:
            logger.info("Stopping disk space monitoring")
            stop_disk_monitoring()
            
        return 1

if __name__ == "__main__":
    sys.exit(main()) 