#!/usr/bin/env python3
"""
Simplified FHIR Patient Extraction Test

This script uses the extract_test_patient.py file to extract data for a test patient
and display the results. It avoids the complexity of the full pipeline.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import traceback
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_debug_logging(enable_debug: bool):
    """
    Configure debug logging.
    
    Args:
        enable_debug: Whether to enable debug logging
    """
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        
        # Log to file in addition to console
        debug_log_file = Path("debug_test.log")
        file_handler = logging.FileHandler(debug_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled for test script")


def run_extraction(patient_id, resources=None, output_dir=None, debug=False, mock=False):
    """
    Run the extraction process for a patient.
    
    Args:
        patient_id: The patient ID to extract
        resources: Optional list of resources to extract
        output_dir: Optional output directory
        debug: Whether to enable debug logging
        mock: Whether to use mock mode
    """
    start_time = time.time()
    cmd = [sys.executable, "extract_test_patient.py", "--patient-id", patient_id]
    
    if resources:
        cmd.extend(["--resources", resources])
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
        
    if debug:
        cmd.append("--debug")
        
    if mock:
        cmd.append("--mock")
    
    logger.info(f"Running extraction with command: {' '.join(cmd)}")
    logger.debug(f"Working directory: {os.getcwd()}")
    
    try:
        # Run the extraction process
        logger.debug("Starting subprocess for extraction")
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Extraction completed successfully in {elapsed_time:.2f} seconds")
        
        # Log command output
        logger.debug("Extraction process output:")
        for line in result.stdout.splitlines():
            logger.debug(f"[STDOUT] {line}")
        
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Extraction failed with exit code {e.returncode} after {elapsed_time:.2f} seconds")
        
        # Log detailed command output
        logger.debug("Extraction process stdout:")
        for line in e.stdout.splitlines():
            logger.debug(f"[STDOUT] {line}")
            
        logger.debug("Extraction process stderr:")
        for line in e.stderr.splitlines():
            logger.debug(f"[STDERR] {line}")
        
        print("STDOUT:")
        print(e.stdout)
        print("\nSTDERR:")
        print(e.stderr)
        return False
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Unexpected error running extraction: {str(e)}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        print(f"Error: {str(e)}")
        return False


def check_extraction_output(patient_id, output_dir="./patient_data"):
    """
    Check the extraction output for a patient.
    
    Args:
        patient_id: The patient ID to check
        output_dir: The output directory
    """
    logger.info(f"Checking extraction output for patient {patient_id}")
    patient_dir = Path(output_dir) / patient_id
    
    if not patient_dir.exists():
        logger.error(f"Patient directory {patient_dir} does not exist")
        return
    
    # Check directory info
    logger.debug(f"Patient directory exists: {patient_dir}")
    if patient_dir.is_dir():
        try:
            dir_stats = os.stat(patient_dir)
            logger.debug(f"Directory stats: size={dir_stats.st_size}, modified={datetime.datetime.fromtimestamp(dir_stats.st_mtime)}")
        except Exception as e:
            logger.debug(f"Could not get directory stats: {e}")
    
    # Check for resource directories
    resources_found = []
    for resource_dir in patient_dir.glob("*"):
        if resource_dir.is_dir():
            resources_found.append(resource_dir.name)
    
    logger.info(f"Found resources: {', '.join(resources_found) if resources_found else 'None'}")
    
    # Check file counts for each resource
    total_entries = 0
    total_files = 0
    resource_details = []
    
    for resource in resources_found:
        resource_dir = patient_dir / resource
        files = list(resource_dir.glob("*.json"))
        total_files += len(files)
        
        entry_count = 0
        file_sizes = []
        resource_errors = 0
        
        for file in files:
            try:
                file_size = file.stat().st_size
                file_sizes.append(file_size)
                
                with open(file, 'r') as f:
                    data = json.load(f)
                    curr_entries = data.get("metadata", {}).get("entry_count", 0)
                    entry_count += curr_entries
                    
                    logger.debug(f"File {file.name} contains {curr_entries} entries, size: {file_size} bytes")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in file {file}: {str(e)}")
                resource_errors += 1
            except Exception as e:
                logger.error(f"Error reading file {file}: {str(e)}")
                logger.debug(f"File error details: {traceback.format_exc()}")
                resource_errors += 1
        
        avg_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        resource_details.append({
            "resource": resource,
            "files": len(files),
            "entries": entry_count,
            "errors": resource_errors,
            "total_size": sum(file_sizes),
            "avg_size": avg_size
        })
        
        logger.info(f"Resource {resource}: {len(files)} files, {entry_count} entries, {resource_errors} errors")
        if resource_errors > 0:
            logger.warning(f"Found {resource_errors} errors in {resource} files")
            
        logger.debug(f"Resource {resource} details: {len(files)} files, {entry_count} entries, " +
                    f"avg file size: {avg_size:.2f} bytes, total size: {sum(file_sizes)} bytes")
        
        total_entries += entry_count
    
    logger.info(f"Total: {total_files} files, {total_entries} entries across {len(resources_found)} resources")
    
    # Return details for potential further analysis
    return {
        "patient_id": patient_id,
        "resources_found": len(resources_found),
        "total_files": total_files,
        "total_entries": total_entries,
        "resource_details": resource_details
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test FHIR patient extraction")
    parser.add_argument("--patient-id", default="T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
                       help="Patient ID to extract")
    parser.add_argument("--resources", default="Patient,Encounter,Observation,Condition,MedicationRequest",
                       help="Comma-separated list of resources to extract")
    parser.add_argument("--output-dir", default="./patient_data",
                       help="Output directory")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check existing extraction output")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug logging")
    parser.add_argument("--mock", action="store_true",
                       help="Use mock mode instead of real API calls")
    args = parser.parse_args()
    
    # Set up debug logging if requested
    setup_debug_logging(args.debug)
    
    logger.info(f"Starting test for patient ID: {args.patient_id}")
    logger.debug(f"Command line arguments: {args}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.debug(f"Environment variables: EPIC_CLIENT_ID={bool(os.environ.get('EPIC_CLIENT_ID'))}, EPIC_CLIENT_SECRET={bool(os.environ.get('EPIC_CLIENT_SECRET'))}")
    
    if not args.check_only:
        # Set up environment for authentication
        os.environ["EPIC_CLIENT_ID"] = "3d6d8f7d-9bea-4fe2-b44d-81c7fec75ee5"
        # In a real environment, you would securely retrieve this
        # Check if we already have a secret set
        if not os.environ.get("EPIC_CLIENT_SECRET") and not args.mock:
            logger.warning("EPIC_CLIENT_SECRET environment variable not set - using mock mode")
            args.mock = True
        
        start_time = time.time()
        
        # Run extraction
        success = run_extraction(
            args.patient_id, 
            args.resources, 
            args.output_dir,
            debug=args.debug,
            mock=args.mock
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Extraction process took {elapsed_time:.2f} seconds")
        
        if not success:
            logger.error("Extraction failed")
            sys.exit(1)
    
    # Check extraction output
    result = check_extraction_output(args.patient_id, args.output_dir)
    
    # Display summary
    print("\nExtraction Test Summary:")
    print(f"Patient ID: {args.patient_id}")
    print(f"Output directory: {output_dir / args.patient_id}")
    
    if result:
        print(f"Resources found: {result['resources_found']}")
        print(f"Total files: {result['total_files']}")
        print(f"Total entries: {result['total_entries']}")
        
        if args.debug:
            print("\nResource Details:")
            for resource in result['resource_details']:
                print(f"  {resource['resource']}: {resource['entries']} entries in {resource['files']} files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled error: {str(e)}")
        print(f"\nFatal error: {str(e)}")
        print("See logs for more details or run with --debug for verbose output")
        sys.exit(1) 