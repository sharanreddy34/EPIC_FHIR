#!/usr/bin/env python3
"""
FHIR Pipeline Local Execution Script

This script allows running the FHIR data pipeline locally without requiring
the full Foundry environment. It simulates the workflow defined in workflow_pipeline.yml
but with local filesystem storage instead of Foundry datasets.

Usage:
    python run_local_fhir_pipeline.py --patient-id <id> [--steps <steps>] [--output-dir <dir>] [--debug] [--strict]

Example:
    python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug --strict
"""

import os
import sys
import json
import yaml
import time
import shutil
import logging
import argparse
import datetime
import tempfile
import traceback
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
from pyspark.sql import SparkSession

# Import path utilities
from epic_fhir_integration.utils.paths import (
    get_run_root, 
    create_dataset_structure,
    create_run_metadata,
    update_run_metadata
)

# Import metrics collector
from epic_fhir_integration.metrics.collector import (
    record_metric,
    flush_metrics
)

# Add lib to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import strict mode utilities
from fhir_pipeline.utils.strict_mode import enable_strict_mode, get_strict_mode, strict_mode_check, no_mocks

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Function to fix import error in chaos_test.py
def extract_resources(patient_id: str, resource_types: Optional[List[str]] = None, 
                     environment: str = "non-production", debug: bool = False) -> Dict[str, pd.DataFrame]:
    """
    Extract FHIR resources for a specific patient.
    
    This is a wrapper for the run_extract_resources function that is used by the chaos_test.py tests.
    
    Args:
        patient_id: ID of the patient to extract resources for
        resource_types: List of resource types to extract (default: extracts all configured resources)
        environment: FHIR environment to use ("production" or "non-production")
        debug: Whether to enable debug logging
    
    Returns:
        Dictionary mapping resource types to pandas DataFrames with the extracted data
    """
    logger.info(f"Extracting resources for patient {patient_id}")
    
    # Configure output directory
    output_dir = Path("./temp_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create datasets structure for extraction
    base_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    datasets = create_dataset_structure(output_dir)
    
    # Run extraction
    success = run_extract_resources(base_dir, datasets, patient_id, 
                                  resource_type=None, mock_mode=False)
    
    if not success:
        logger.warning(f"Extraction failed")
        
        # In strict mode, fail loudly instead of falling back to mock data
        if get_strict_mode():
            strict_mode_check("extraction fallback to mock mode")
        else:
            logger.warning(f"Falling back to mock mode")
            run_extract_resources(base_dir, datasets, patient_id, 
                                resource_type=None, mock_mode=True)
    
    # Collect results into pandas dataframes
    results = {}
    bronze_dir = output_dir / "bronze" / "fhir_raw"
    
    for resource_dir in bronze_dir.glob("*"):
        if resource_dir.is_dir():
            resource_type = resource_dir.name
            
            # Skip if not in requested resource types
            if resource_types and resource_type not in resource_types:
                continue
            
            # Load all JSON files for this resource
            resource_data = []
            for json_file in resource_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        if "bundle" in data and "entry" in data["bundle"]:
                            for entry in data["bundle"]["entry"]:
                                if "resource" in entry:
                                    resource_data.append(entry["resource"])
                except Exception as e:
                    logger.error(f"Error reading {json_file}: {str(e)}")
            
            # Create dataframe if we have data
            if resource_data:
                results[resource_type] = pd.DataFrame(resource_data)
            else:
                # Empty dataframe with basic columns
                results[resource_type] = pd.DataFrame(columns=["id", "resourceType"])
    
    return results


def setup_debug_logging(enable_debug: bool, log_directory: Path = None):
    """
    Configure debug logging.
    
    Args:
        enable_debug: Whether to enable debug logging
        log_directory: Directory to store log files (optional)
    """
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        # Also set debug level for other modules
        logging.getLogger("pyspark").setLevel(logging.INFO)  # Too verbose to set to DEBUG
        
        # Log to file in addition to console
        if log_directory and log_directory.exists():
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_log_file = log_directory / f"debug_pipeline_{timestamp}.log"
        else:
        debug_log_file = Path("debug_pipeline.log")
            
        file_handler = logging.FileHandler(debug_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug(f"Debug logging enabled, writing to {debug_log_file}")

@no_mocks("create_mock_resources")
def create_mock_resources(output_dir: Path, patient_id: str, mock_mode: bool = False) -> bool:
    """
    Create mock FHIR resources for testing.
    
    In strict mode, this function will raise an error.
    
    Args:
        output_dir: Output directory
        patient_id: Patient ID to use in resources
        mock_mode: Whether mock mode is enabled
        
    Returns:
        Success status
    """
    # This function will raise an error in strict mode due to @no_mocks decorator
    logger.info("Creating mock FHIR resources")
    
    # Create mock data
    # ... existing mock data creation code ...
    
    return True

def get_or_refresh_token(token_file, debug=False):
    """Get existing token or refresh if needed."""
    try:
        # Try to load existing token
        with open(token_file, 'r') as f:
            token_data = json.load(f)
            
        # Check if token is expired or about to expire (less than 5 minutes left)
        now = time.time()
        expires_in = token_data.get('expires_in', 0)
        created_at = token_data.get('created_at', now - expires_in)
        time_left = created_at + expires_in - now
        
        if time_left > 300:  # More than 5 minutes left
            logger.debug(f"Using existing token with {time_left:.0f} seconds left")
            return token_data.get('access_token')
            
        logger.debug(f"Token expired or about to expire ({time_left:.0f} seconds left), refreshing")
    except (FileNotFoundError, json.JSONDecodeError):
        logger.debug("No valid token file found, getting new token")
    
    # Need to refresh the token - try the new auth module first
    try:
        from auth.setup_epic_auth import refresh_token
        
        logger.debug("Using auth module to refresh token")
        token_data = refresh_token()
        
        if token_data and 'access_token' in token_data:
            logger.debug("Token refreshed successfully")
            return token_data.get('access_token')
        else:
            logger.warning("Failed to refresh token with auth module")
    except ImportError:
        logger.debug("Auth module not available, using simple_token_refresh.py")
    
    # Use the simple refresh script if auth module failed or not available
    try:
        # Call the simple token refresh script
        cmd = [sys.executable, 'simple_token_refresh.py']
        if debug:
            cmd.append('--debug')
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Token refresh failed: {result.stderr}")
            return None
            
        # Re-read the token file
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        return token_data.get('access_token')
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return None

def main():
    """Main entry point for the local pipeline."""
    parser = argparse.ArgumentParser(description="Run FHIR pipeline locally")
    parser.add_argument("--patient-id", required=True, help="Patient ID for extraction")
    parser.add_argument("--output-dir", default="./local_output", help="Output directory")
    parser.add_argument("--steps", default="extract,transform,gold", help="Pipeline steps to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (no mock data)")
    parser.add_argument("--validate", action="store_true", help="Run validation after pipeline completes")
    
    args = parser.parse_args()
    
    # Create dataset structure with standard directories
    output_dir = Path(args.output_dir)
    directories = create_dataset_structure(output_dir)
    run_dir = directories["bronze"].parent  # Get the test run root directory
    
    # Configure logging to use logs directory
    setup_debug_logging(args.debug, directories["logs"])
    
    # Create run metadata
    create_run_metadata(
        run_dir,
        params={
            "patient_id": args.patient_id,
            "steps": args.steps,
            "debug_mode": args.debug,
            "strict_mode": args.strict,
        }
    )
    
    # Enable strict mode if requested
    if args.strict:
        enable_strict_mode()
        logger.info("STRICT MODE ENABLED - No mock data will be used")
    
    # ... existing code ...
    
    # Run validation if requested
    if args.validate:
        try:
            from epic_fhir_integration.cli.validate_run import RunValidator
            
            logger.info(f"Running validation on pipeline output in {run_dir}")
            validator = RunValidator(run_dir, verbose=args.debug)
            validation_results = validator.run_validation()
            result_file = validator.write_results()
            
            logger.info(f"Validation completed with status: {validation_results['validation_status']}")
            logger.info(f"Validation results written to: {result_file}")
            
            # Update run metadata with validation results
            update_run_metadata(
                run_dir,
                validation=validation_results
            )
        except Exception as e:
            logger.error(f"Error running validation: {e}")
    
    # Update run metadata to mark completion
    update_run_metadata(run_dir, end_run=True)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 