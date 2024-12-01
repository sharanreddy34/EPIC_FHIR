#!/usr/bin/env python3
"""
Complete FHIR Pipeline Runner

This script runs the entire FHIR pipeline from API extraction to gold layer creation.
It handles authentication, API calls, and data transformations with robust error handling.

Usage:
    python run_complete_pipeline.py --patient-id ID [--output-dir DIR] [--debug] [--strict]

Example:
    python run_complete_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug
"""

import os
import sys
import time
import json
import argparse
import logging
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

# Add script directory to path
script_dir = Path(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, str(script_dir))

# Configure logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("pipeline_runner")

def setup_logging(debug_mode, output_dir):
    """
    Set up logging configuration.
    
    Args:
        debug_mode: Whether to enable debug logging
        output_dir: Output directory path
    """
    # Create logs directory
    logs_dir = Path(output_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"pipeline_{timestamp}.log"
    
    # Set up file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Set logging level
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logger.setLevel(log_level)
    file_handler.setLevel(log_level)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    logger.info(f"Logging to {log_file}")
    if debug_mode:
        logger.debug("Debug logging enabled")

def validate_directories(output_dir):
    """
    Validate and create output directory structure.
    
    Args:
        output_dir: Base output directory
    """
    # Standard directory structure
    directories = [
        output_dir / "bronze" / "fhir_raw",
        output_dir / "silver" / "fhir_normalized",
        output_dir / "gold",
        output_dir / "metrics",
        output_dir / "logs",
        output_dir / "config",
        output_dir / "secrets"
    ]
    
    # Create directories
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Validated directory: {directory}")
    
    logger.info(f"Output directory structure validated: {output_dir}")
    return directories

def refresh_auth_token():
    """
    Refresh the EPIC FHIR API token.
    
    Returns:
        Token data if successful, None otherwise
    """
    logger.info("Refreshing authentication token")
    
    try:
        # Import token refresher
        from auth.setup_epic_auth import get_access_token
        
        # Get fresh token
        token_data = get_access_token(debug=logger.level == logging.DEBUG)
        
        if token_data and "access_token" in token_data:
            logger.info(f"Token refreshed successfully, expires in {token_data.get('expires_in')} seconds")
            
            # Copy token to secrets directory
            try:
                from pathlib import Path
                token_file = Path("epic_token.json")
                if token_file.exists():
                    # Ensure target directory exists
                    secrets_dir = Path("output/secrets")
                    secrets_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy token file
                    import shutil
                    shutil.copy(token_file, secrets_dir / "epic_token.json")
                    logger.debug(f"Copied token to {secrets_dir / 'epic_token.json'}")
            except Exception as e:
                logger.warning(f"Failed to copy token to secrets directory: {str(e)}")
            
            return token_data
        else:
            logger.error("Failed to refresh token - no valid token data returned")
            return None
            
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def extract_resources(patient_id, output_dir, strict_mode=False, debug_mode=False):
    """
    Extract FHIR resources from the API.
    
    Args:
        patient_id: Patient ID to extract data for
        output_dir: Output directory
        strict_mode: Whether to enable strict mode
        debug_mode: Whether to enable debug mode
        
    Returns:
        Success status and extracted resource counts
    """
    logger.info(f"Extracting resources for patient {patient_id}")
    start_time = time.time()
    
    # First refresh token to ensure we have a valid one
    token_data = refresh_auth_token()
    
    if not token_data:
        logger.error("Failed to refresh token - cannot proceed with extraction")
        return False, {}
    
    # Destination directory for extracted data
    bronze_dir = output_dir / "bronze" / "fhir_raw"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    
    # Resource types to extract
    resource_types = [
        "Patient", 
        "Encounter", 
        "Observation", 
        "Condition", 
        "MedicationRequest", 
        "Procedure", 
        "Immunization", 
        "AllergyIntolerance"
    ]
    
    # Command arguments
    args = [
        "python", "extract_test_patient.py",
        f"--patient-id={patient_id}",
        f"--resources={','.join(resource_types)}",
        f"--output-dir={bronze_dir}"
    ]
    
    if debug_mode:
        args.append("--debug")
    
    # Run extraction
    logger.info(f"Running extraction command: {' '.join(args)}")
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Extraction failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False, {}
        else:
            logger.info("Extraction command completed successfully")
        
        # Parse output for resource counts
        resource_counts = {}
        
        # Extract resource counts from output
        import re
        count_pattern = re.compile(r"- (\w+): (\d+) resources")
        for line in result.stdout.splitlines():
            match = count_pattern.search(line)
            if match:
                resource_type, count = match.groups()
                resource_counts[resource_type] = int(count)
                
        # Check if we extracted anything
        if not resource_counts:
            logger.error("No resources extracted - aborting")
            return False, {}
        
        elapsed = time.time() - start_time
        logger.info(f"Resource extraction completed in {elapsed:.2f} seconds")
        logger.info(f"Extracted resources: {resource_counts}")
        
        return True, resource_counts
        
    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        logger.debug(traceback.format_exc())
        return False, {}

def transform_bronze_to_silver(output_dir, strict_mode=False, debug_mode=False):
    """
    Transform bronze data to silver layer.
    
    Args:
        output_dir: Output directory
        strict_mode: Whether to enable strict mode
        debug_mode: Whether to enable debug mode
        
    Returns:
        Success status
    """
    logger.info("Transforming bronze data to silver layer")
    start_time = time.time()
    
    # Bronze and silver directories
    bronze_dir = output_dir / "bronze"
    silver_dir = output_dir / "silver"
    
    # Check if bronze directory exists and has data
    if not bronze_dir.exists() or not any(bronze_dir.glob("**/*.json")):
        logger.error(f"Bronze directory {bronze_dir} does not exist or has no data - cannot proceed")
        return False
    
    # Command arguments
    args = [
        "python", "scripts/transform_bronze_to_silver.py",
        f"--bronze-dir={bronze_dir}",
        f"--silver-dir={silver_dir}"
    ]
    
    if debug_mode:
        args.append("--debug")
    
    # Run transformation
    logger.info(f"Running bronze-to-silver transformation: {' '.join(args)}")
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Bronze-to-silver transformation failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
        else:
            logger.info("Bronze-to-silver transformation completed successfully")
        
        # Verify silver data was generated
        silver_normalized_dir = silver_dir / "fhir_normalized"
        if not silver_normalized_dir.exists() or not any(silver_normalized_dir.glob("*.parquet")):
            logger.error("No data found in silver layer after transformation")
            return False
        
        elapsed = time.time() - start_time
        logger.info(f"Bronze-to-silver transformation completed in {elapsed:.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during bronze-to-silver transformation: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def transform_silver_to_gold(output_dir, strict_mode=False, debug_mode=False):
    """
    Transform silver data to gold layer.
    
    Args:
        output_dir: Output directory
        strict_mode: Whether to enable strict mode
        debug_mode: Whether to enable debug mode
        
    Returns:
        Success status
    """
    logger.info("Transforming silver data to gold layer")
    start_time = time.time()
    
    # Silver and gold directories
    silver_dir = output_dir / "silver"
    gold_dir = output_dir / "gold"
    
    # Check if silver directory exists and has data
    silver_normalized_dir = silver_dir / "fhir_normalized"
    if not silver_normalized_dir.exists() or not any(silver_normalized_dir.glob("*.parquet")):
        logger.error(f"Silver directory {silver_normalized_dir} does not exist or has no data - cannot proceed")
        return False
    
    # Command arguments
    args = [
        "python", "scripts/transform_silver_to_gold.py",
        f"--silver-dir={silver_dir}",
        f"--gold-dir={gold_dir}",
        "--summaries=patient,observation,encounter,medication"
    ]
    
    if debug_mode:
        args.append("--debug")
    
    # Run transformation
    logger.info(f"Running silver-to-gold transformation: {' '.join(args)}")
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Silver-to-gold transformation failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
        else:
            logger.info("Silver-to-gold transformation completed successfully")
        
        # Verify gold data was generated
        if not any(gold_dir.glob("*.parquet")):
            logger.error("No data found in gold layer after transformation")
            return False
            
        elapsed = time.time() - start_time
        logger.info(f"Silver-to-gold transformation completed in {elapsed:.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during silver-to-gold transformation: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def print_summary(output_dir, resource_counts):
    """
    Print a summary of the pipeline run.
    
    Args:
        output_dir: Output directory
        resource_counts: Resource counts from extraction
    """
    print("\n" + "="*80)
    print(f"FHIR PIPELINE RUN SUMMARY")
    print("="*80)
    
    # Directory structure
    print(f"Output directory: {output_dir}")
    
    # Bronze layer
    bronze_dir = output_dir / "bronze" / "fhir_raw"
    bronze_resource_types = [d.name for d in bronze_dir.glob("*") if d.is_dir()]
    print(f"\nBronze Layer: {len(bronze_resource_types)} resource types")
    
    for resource_type in sorted(bronze_resource_types):
        resource_dir = bronze_dir / resource_type
        file_count = len(list(resource_dir.glob("*.json")))
        resource_count = resource_counts.get(resource_type, "unknown")
        print(f"  - {resource_type}: {file_count} files, {resource_count} resources")
    
    # Silver layer
    silver_dir = output_dir / "silver" / "fhir_normalized"
    if silver_dir.exists():
        silver_files = list(silver_dir.glob("*.parquet"))
        print(f"\nSilver Layer: {len(silver_files)} parquet files")
        
        for parquet_file in sorted(silver_files):
            # Try to get basic info without actually reading the file
            file_size = parquet_file.stat().st_size / 1024  # KB
            print(f"  - {parquet_file.stem}: {file_size:.1f} KB")
    else:
        print("\nSilver Layer: not created")
    
    # Gold layer
    gold_dir = output_dir / "gold"
    if gold_dir.exists():
        gold_files = list(gold_dir.glob("*.parquet"))
        print(f"\nGold Layer: {len(gold_files)} parquet files")
        
        for parquet_file in sorted(gold_files):
            file_size = parquet_file.stat().st_size / 1024  # KB
            print(f"  - {parquet_file.stem}: {file_size:.1f} KB")
    else:
        print("\nGold Layer: not created")
    
    print("\nPipeline run completed!")
    print("="*80)

def verify_output_against_readme(output_dir):
    """
    Verify the output structure against the README-E2E-TEST.md requirements.
    
    Args:
        output_dir: Output directory to verify
    
    Returns:
        List of verification results
    """
    logger.info("Verifying output against README-E2E-TEST.md requirements")
    
    verification_results = []
    
    # Expected directory structure
    expected_dirs = [
        ("bronze/fhir_raw", "Raw FHIR resources"),
        ("silver/fhir_normalized", "Normalized FHIR resources"),
        ("gold", "Gold layer datasets")
    ]
    
    for dir_path, description in expected_dirs:
        full_path = output_dir / dir_path
        if full_path.exists() and full_path.is_dir():
            # Check if directory has any content
            if any(full_path.iterdir()):
                verification_results.append(("PASS", f"{dir_path} exists and has content - {description}"))
            else:
                verification_results.append(("WARN", f"{dir_path} exists but is empty - {description}"))
        else:
            verification_results.append(("FAIL", f"{dir_path} does not exist - {description}"))
    
    # Check for specific resource types in bronze layer
    bronze_fhir_dir = output_dir / "bronze" / "fhir_raw"
    if bronze_fhir_dir.exists():
        expected_resources = ["Patient", "Encounter", "Observation"]
        for resource_type in expected_resources:
            resource_dir = bronze_fhir_dir / resource_type
            if resource_dir.exists() and resource_dir.is_dir():
                # Check if directory has JSON files
                json_files = list(resource_dir.glob("*.json"))
                if json_files:
                    verification_results.append(("PASS", f"Bronze layer contains {resource_type} with {len(json_files)} files"))
                else:
                    verification_results.append(("WARN", f"Bronze layer contains {resource_type} but no JSON files"))
            else:
                verification_results.append(("WARN", f"Bronze layer is missing {resource_type}"))
    
    # Check for specific files in silver layer
    silver_dir = output_dir / "silver" / "fhir_normalized"
    if silver_dir.exists():
        expected_files = ["patient.parquet", "observation.parquet", "encounter.parquet"]
        for file_name in expected_files:
            file_path = silver_dir / file_name
            if file_path.exists() and file_path.is_file():
                file_size = file_path.stat().st_size / 1024  # KB
                verification_results.append(("PASS", f"Silver layer contains {file_name} ({file_size:.1f} KB)"))
            else:
                verification_results.append(("WARN", f"Silver layer is missing {file_name}"))
    
    # Check for specific files in gold layer
    gold_dir = output_dir / "gold"
    if gold_dir.exists():
        expected_files = ["patient_summary.parquet", "observation_summary.parquet", "encounter_summary.parquet"]
        for file_name in expected_files:
            file_path = gold_dir / file_name
            if file_path.exists() and file_path.is_file():
                file_size = file_path.stat().st_size / 1024  # KB
                verification_results.append(("PASS", f"Gold layer contains {file_name} ({file_size:.1f} KB)"))
            else:
                verification_results.append(("WARN", f"Gold layer is missing {file_name}"))
    
    return verification_results

def print_verification_results(verification_results):
    """
    Print verification results.
    
    Args:
        verification_results: List of verification results
    """
    print("\n" + "="*80)
    print("OUTPUT VERIFICATION RESULTS")
    print("="*80)
    
    # Count results by status
    status_counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for status, _ in verification_results:
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Print summary
    print(f"Total checks: {len(verification_results)}")
    print(f"PASS: {status_counts['PASS']}")
    print(f"WARN: {status_counts['WARN']}")
    print(f"FAIL: {status_counts['FAIL']}")
    print("-"*80)
    
    # Print detailed results
    for status, message in verification_results:
        if status == "PASS":
            print(f"✅ {message}")
        elif status == "WARN":
            print(f"⚠️ {message}")
        elif status == "FAIL":
            print(f"❌ {message}")
    
    print("="*80)

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run complete FHIR pipeline")
    parser.add_argument("--patient-id", required=True, help="Patient ID to process")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (fail on any error)")
    parser.add_argument("--steps", default="extract,transform,gold,verify", 
                        help="Pipeline steps to run (comma-separated)")
    
    args = parser.parse_args()
    
    # Convert output directory to Path
    output_dir = Path(args.output_dir)
    
    # Setup logging
    setup_logging(args.debug, output_dir)
    
    logger.info(f"Starting complete FHIR pipeline for patient {args.patient_id}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Debug mode: {args.debug}")
    logger.info(f"Strict mode: {args.strict}")
    logger.info(f"Steps to run: {args.steps}")
    
    # Determine steps to run
    steps = [step.strip().lower() for step in args.steps.split(",")]
    
    try:
        # Validate and create output directory structure
        directories = validate_directories(output_dir)
        
        # Extract resources (bronze layer)
        if "extract" in steps:
            logger.info("Running extraction step")
            success, resource_counts = extract_resources(
                args.patient_id, 
                output_dir, 
                args.strict, 
                args.debug
            )
            
            if not success:
                logger.error("Extraction step failed - aborting pipeline")
                return 1
        else:
            # If not running extract, check for existing data
            bronze_dir = output_dir / "bronze" / "fhir_raw"
            resource_counts = {}
            if bronze_dir.exists():
                for resource_dir in bronze_dir.glob("*"):
                    if resource_dir.is_dir():
                        json_files = list(resource_dir.glob("*.json"))
                        resource_counts[resource_dir.name] = len(json_files)
        
        # Transform bronze to silver
        if "transform" in steps:
            logger.info("Running bronze-to-silver transformation step")
            success = transform_bronze_to_silver(
                output_dir, 
                args.strict, 
                args.debug
            )
            
            if not success:
                logger.error("Bronze-to-silver transformation failed - aborting pipeline")
                return 1
        
        # Transform silver to gold
        if "gold" in steps:
            logger.info("Running silver-to-gold transformation step")
            success = transform_silver_to_gold(
                output_dir, 
                args.strict, 
                args.debug
            )
            
            if not success:
                logger.error("Silver-to-gold transformation failed - aborting pipeline")
                return 1
        
        # Print summary
        print_summary(output_dir, resource_counts)
        
        # Verify against README requirements
        if "verify" in steps:
            logger.info("Running verification step")
            verification_results = verify_output_against_readme(output_dir)
            print_verification_results(verification_results)
        
        logger.info("Pipeline completed successfully")
        return 0
            
    except Exception as e:
        logger.error(f"Unhandled exception in pipeline: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 