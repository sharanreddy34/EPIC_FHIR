#!/usr/bin/env python3
"""
Environment Setup Script for Epic FHIR Integration Testing

This script prepares the environment for running Epic FHIR integration tests by:
1. Setting up the necessary environment variables
2. Generating an authentication token if needed
3. Creating required directories
4. Running the specified test script with proper parameters

Usage:
    python setup_test_env.py --patient-id PATIENT_ID [--output-dir DIR] [--debug]
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("setup_test_env")

def setup_environment_variables():
    """Set up environment variables required for Epic FHIR integration."""
    logger.info("Setting up environment variables...")
    
    # Define required environment variables and their default values
    required_vars = {
        "FHIR_OUTPUT_DIR": str(Path.cwd() / "output" / "production_test"),
        "EPIC_API_BASE_URL": "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        "EPIC_CLIENT_ID": "02317de4-f128-4607-989b-07892f678580"  # Non-production client ID
    }
    
    # Determine private key path
    repo_root = Path(__file__).resolve().parent.parent
    possible_key_paths = [
        repo_root / "secrets" / "epic_private_key.pem",
        repo_root / "auth" / "keys" / "epic_private_key.pem",
        repo_root.parent / "docs" / "key.md",
        Path.home() / "ATLAS Palantir" / "docs" / "key.md"
    ]
    
    private_key_path = None
    for path in possible_key_paths:
        if path.exists():
            private_key_path = path
            logger.info(f"Found private key at: {private_key_path}")
            break
    
    if private_key_path:
        required_vars["EPIC_PRIVATE_KEY_PATH"] = str(private_key_path)
    else:
        logger.warning("No private key file found. Authentication may fail.")
    
    # Set environment variables if not already set
    vars_set = 0
    for var_name, default_value in required_vars.items():
        if var_name not in os.environ:
            os.environ[var_name] = default_value
            logger.info(f"Set {var_name}={default_value}")
            vars_set += 1
        else:
            logger.info(f"Using existing {var_name}={os.environ[var_name]}")
    
    logger.info(f"Environment setup complete. Set {vars_set} variables.")
    return True

def ensure_auth_token():
    """Ensure an authentication token is available."""
    logger.info("Checking for Epic authentication token...")
    
    # Try to import the authentication module
    try:
        # First try to add the project root to Python path
        repo_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo_root))
        
        from epic_fhir_integration.auth.custom_auth import get_token, get_cached_token
        
        # Check if we have a valid cached token
        token = get_cached_token()
        if token:
            logger.info("Using existing cached token")
            return True
        
        # Get a new token
        logger.info("No valid token found. Generating new token...")
        token = get_token()
        if token:
            logger.info("Successfully generated new authentication token")
            return True
        else:
            logger.error("Failed to generate authentication token")
            return False
    except ImportError as e:
        logger.error(f"Failed to import authentication module: {e}")
        
        # Try using the standalone auth script as fallback
        logger.info("Trying fallback authentication method...")
        auth_script = repo_root / "auth" / "setup_epic_auth.py"
        
        if auth_script.exists():
            try:
                logger.info(f"Running auth script: {auth_script}")
                result = subprocess.run([sys.executable, str(auth_script)], check=True)
                
                if result.returncode == 0:
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.error("Authentication script failed")
                    return False
            except Exception as e:
                logger.error(f"Error running authentication script: {e}")
                return False
        else:
            logger.error(f"Authentication script not found at {auth_script}")
            return False

def run_test(patient_id, output_dir=None, debug=False, **kwargs):
    """Run the production test with specified parameters."""
    logger.info(f"Running test for patient ID: {patient_id}")
    
    # Determine the test script path
    repo_root = Path(__file__).resolve().parent.parent
    test_script = repo_root / "scripts" / "production_test_modified.py"
    
    if not test_script.exists():
        logger.error(f"Test script not found at {test_script}")
        return False
    
    # Build command arguments
    cmd = [sys.executable, str(test_script), "--patient-id", patient_id]
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
    
    if debug:
        cmd.append("--debug")
    
    # Add any additional arguments
    for key, value in kwargs.items():
        if isinstance(value, bool) and value:
            cmd.append(f"--{key.replace('_', '-')}")
        elif not isinstance(value, bool):
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
    
    # Run the test
    logger.info(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            logger.info("Test completed successfully")
            return True
        else:
            logger.error(f"Test failed with return code: {result.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error running test: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Set up environment and run Epic FHIR integration test")
    parser.add_argument("--patient-id", required=True, help="Patient ID to use for testing")
    parser.add_argument("--output-dir", help="Output directory for test results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--keep-tests", type=int, default=5, help="Number of test directories to keep")
    parser.add_argument("--min-disk-space", type=float, default=10.0, help="Minimum free disk space in GB")
    parser.add_argument("--monitor-disk", action="store_true", help="Enable disk space monitoring")
    parser.add_argument("--retry-count", type=int, default=3, help="Maximum number of retries for API calls")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Step 1: Setup environment variables
    if not setup_environment_variables():
        logger.error("Failed to set up environment variables")
        return 1
    
    # Step 2: Ensure we have an authentication token
    if not ensure_auth_token():
        logger.error("Failed to ensure authentication token")
        return 1
    
    # Step 3: Run the test
    kwargs = {
        "keep_tests": args.keep_tests,
        "min_disk_space": args.min_disk_space,
        "monitor_disk": args.monitor_disk,
        "retry_count": args.retry_count
    }
    
    if not run_test(args.patient_id, args.output_dir, args.debug, **kwargs):
        logger.error("Test execution failed")
        return 1
    
    logger.info("Environment setup and test execution completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 