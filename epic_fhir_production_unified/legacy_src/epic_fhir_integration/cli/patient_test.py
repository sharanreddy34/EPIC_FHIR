#!/usr/bin/env python3
"""
Command-line tool to test FHIR API with a single patient.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from epic_fhir_integration.io.custom_fhir_client import create_epic_fhir_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the single patient test CLI."""
    parser = argparse.ArgumentParser(description="Test Epic FHIR API with a single patient")
    parser.add_argument("--patient-id", required=True, help="Patient ID to retrieve")
    parser.add_argument("--fhir-url", help="FHIR API base URL")
    parser.add_argument("--output-dir", default="output/patient_test", help="Output directory for test results")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting Epic FHIR test for patient ID: {args.patient_id}")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create client
    try:
        client = create_epic_fhir_client(base_url=args.fhir_url)
        logger.info(f"Connected to FHIR server: {client.base_url}")
    except Exception as e:
        logger.error(f"Failed to create FHIR client: {e}")
        return 1
    
    # Test API connection
    try:
        # Get all data for the patient
        patient_data = client.get_patient_data(args.patient_id)
        
        # Print summary
        logger.info("Successfully retrieved patient data:")
        for resource_type, resources in patient_data.items():
            resource_count = len(resources)
            logger.info(f"  {resource_type}: {resource_count} resources")
        
        # Save results to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"patient_{args.patient_id}_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump(patient_data, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        
        # Generate report
        report_file = output_dir / f"report_{args.patient_id}_{timestamp}.md"
        with open(report_file, "w") as f:
            f.write(f"# FHIR Test Report for Patient {args.patient_id}\n\n")
            f.write(f"## Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## FHIR Server: {client.base_url}\n\n")
            f.write("## Resources Retrieved\n\n")
            
            for resource_type, resources in patient_data.items():
                resource_count = len(resources)
                f.write(f"- {resource_type}: {resource_count} resources\n")
            
            # Patient demographics (if available)
            if patient_data["Patient"] and len(patient_data["Patient"]) > 0:
                patient = patient_data["Patient"][0]
                f.write("\n## Patient Information\n\n")
                
                # Basic demographics
                if "name" in patient and len(patient["name"]) > 0:
                    name = patient["name"][0]
                    given = " ".join(name.get("given", ["Unknown"]))
                    family = name.get("family", "Unknown")
                    f.write(f"- Name: {given} {family}\n")
                
                if "gender" in patient:
                    f.write(f"- Gender: {patient['gender']}\n")
                
                if "birthDate" in patient:
                    f.write(f"- Birth Date: {patient['birthDate']}\n")
            
            f.write("\n## Test Result: SUCCESS\n")
        
        logger.info(f"Report generated: {report_file}")
        return 0
    
    except Exception as e:
        logger.error(f"Error testing FHIR API: {e}")
        
        # Generate error report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_file = output_dir / f"error_{args.patient_id}_{timestamp}.md"
        
        with open(error_file, "w") as f:
            f.write(f"# FHIR Test Error Report for Patient {args.patient_id}\n\n")
            f.write(f"## Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## FHIR Server: {args.fhir_url or 'Default from config'}\n\n")
            f.write("## Error Details\n\n")
            f.write(f"```\n{str(e)}\n```\n\n")
            f.write("## Test Result: FAILURE\n")
        
        logger.info(f"Error report generated: {error_file}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 