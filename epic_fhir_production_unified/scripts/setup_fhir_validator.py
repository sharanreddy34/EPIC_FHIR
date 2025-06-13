#!/usr/bin/env python3
"""
Setup script for the official HL7 FHIR Validator.

This script downloads the official HL7 FHIR Validator JAR file and sets up
configuration for validating FHIR resources against Implementation Guides (IGs).
"""

import argparse
import json
import logging
import os
import platform
import requests
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FHIR Validator URLs
VALIDATOR_URL = "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar"
US_CORE_IG_URL = "https://www.hl7.org/fhir/us/core/full-ig.zip"

def download_file(url: str, target_path: Path) -> bool:
    """
    Download a file from a URL.
    
    Args:
        url: URL to download from
        target_path: Path to save the file to
        
    Returns:
        True if download was successful, False otherwise
    """
    try:
        logger.info(f"Downloading {url} to {target_path}")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(target_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
            
        logger.info(f"Downloaded {target_path.name} successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

def check_java_installation() -> bool:
    """
    Check if Java is installed and available in PATH.
    
    Returns:
        True if Java is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["java", "-version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info(f"Java is installed: {result.stderr.strip()}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Java is not installed or not in PATH")
        return False

def setup_validator(validator_dir: Path, igs: list = None) -> Path:
    """
    Set up the FHIR Validator with specified Implementation Guides.
    
    Args:
        validator_dir: Directory to install validator to
        igs: List of Implementation Guide identifiers to install
        
    Returns:
        Path to the validator JAR file
    """
    # Create validator directory
    validator_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for Java
    if not check_java_installation():
        logger.error("Please install Java and ensure it's in your PATH before proceeding.")
        sys.exit(1)
    
    # Download validator JAR if it doesn't exist
    validator_jar = validator_dir / "validator_cli.jar"
    if not validator_jar.exists():
        if not download_file(VALIDATOR_URL, validator_jar):
            logger.error("Failed to download FHIR Validator.")
            sys.exit(1)
    else:
        logger.info(f"FHIR Validator already exists at {validator_jar}")
    
    # Create IGs directory
    igs_dir = validator_dir / "igs"
    igs_dir.mkdir(exist_ok=True)
    
    # Download US Core IG if requested or default
    if igs is None or 'hl7.fhir.us.core' in igs:
        us_core_zip = igs_dir / "us_core.zip"
        us_core_dir = igs_dir / "us_core"
        
        if not us_core_dir.exists():
            if not download_file(US_CORE_IG_URL, us_core_zip):
                logger.warning("Failed to download US Core IG.")
            else:
                # Extract the US Core IG
                logger.info(f"Extracting US Core IG to {us_core_dir}")
                us_core_dir.mkdir(exist_ok=True)
                
                with ZipFile(us_core_zip, 'r') as zip_ref:
                    zip_ref.extractall(us_core_dir)
                    
                logger.info("US Core IG extracted successfully")
        else:
            logger.info(f"US Core IG already exists at {us_core_dir}")
    
    # Create a configuration file for the validator
    config = {
        "tx": {
            "endpoint": "http://tx.fhir.org/r4",
            "local": [
                str(igs_dir / "us_core" / "ValueSet")
            ]
        },
        "ig": {
            "registry": "https://fhir.github.io/ig-registry/registry.json",
            "local": [
                str(igs_dir / "us_core" / "profiles")
            ]
        }
    }
    
    config_file = validator_dir / "validator_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Validator configuration written to {config_file}")
    
    # Create a helper script to run the validator
    script_ext = ".bat" if platform.system() == "Windows" else ".sh"
    script_path = validator_dir / f"run_validator{script_ext}"
    
    if platform.system() == "Windows":
        script_content = f"""@echo off
java -jar "{validator_jar}" %%* -tx n/a
"""
    else:
        script_content = f"""#!/bin/bash
java -jar "{validator_jar}" "$@" -tx n/a
"""
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make the script executable on non-Windows platforms
    if platform.system() != "Windows":
        os.chmod(script_path, 0o755)
    
    logger.info(f"Validator helper script created at {script_path}")
    
    return validator_jar

def main():
    parser = argparse.ArgumentParser(description="Set up the HL7 FHIR Validator")
    parser.add_argument(
        "--dir", 
        help="Directory to install validator to", 
        default="tools/fhir-validator"
    )
    parser.add_argument(
        "--igs", 
        nargs="+", 
        help="Implementation Guides to install (default: hl7.fhir.us.core)",
        default=["hl7.fhir.us.core"]
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Test the validator after installation"
    )
    
    args = parser.parse_args()
    
    # Convert directory to an absolute path
    validator_dir = Path(args.dir).resolve()
    
    # Set up the validator
    validator_jar = setup_validator(validator_dir, args.igs)
    
    if args.test:
        logger.info("Testing the FHIR Validator...")
        
        test_file = validator_dir / "test_patient.json"
        with open(test_file, 'w') as f:
            f.write('''
{
  "resourceType": "Patient",
  "id": "test",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
  },
  "name": [
    {
      "family": "Smith",
      "given": ["John"]
    }
  ],
  "gender": "male",
  "birthDate": "1970-01-01"
}
''')
        
        try:
            cmd = ["java", "-jar", str(validator_jar), str(test_file), "-version", "4.0.1"]
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            logger.info("Validator output:")
            logger.info(result.stdout)
            
            if "Success" in result.stdout:
                logger.info("Validator test passed!")
            else:
                logger.warning("Validator test may not have passed. Check the output above.")
                
        except subprocess.SubprocessError as e:
            logger.error(f"Error testing validator: {e}")
    
    logger.info(f"FHIR Validator setup completed successfully in {validator_dir}")
    logger.info(f"Run the validator using: {validator_dir / f'run_validator{'.bat' if platform.system() == 'Windows' else '.sh'}'}")

if __name__ == "__main__":
    main() 