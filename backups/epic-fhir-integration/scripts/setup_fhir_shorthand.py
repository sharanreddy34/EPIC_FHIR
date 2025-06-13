#!/usr/bin/env python3
"""
Setup script for FHIR Shorthand (FSH) and SUSHI.

This script sets up FHIR Shorthand (FSH) and SUSHI for creating
custom FHIR profiles, extensions, and implementation guides.
"""

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Example FSH files for common resources
EXAMPLE_FSH_FILES = {
    "Patient": """
Profile: EpicPatient
Parent: Patient
Id: epic-patient
Title: "Epic Patient Profile"
Description: "Profile of the Patient resource for Epic data"
* identifier 1..*
* identifier ^slicing.discriminator.type = #pattern
* identifier ^slicing.discriminator.path = "type.coding.code"
* identifier ^slicing.rules = #open
* identifier ^slicing.description = "Slice based on identifier type"
* identifier contains
    MRN 1..1 and
    SSN 0..1
* identifier[MRN].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[MRN].type.coding.code = #MR
* identifier[MRN].system = "urn:oid:1.2.840.114350.1.13.0.1.7.5.737384.0"
* identifier[SSN].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[SSN].type.coding.code = #SS
* extension contains
    http://hl7.org/fhir/us/core/StructureDefinition/us-core-race named race 0..1 and
    http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity named ethnicity 0..1
""",
    "Observation": """
Profile: EpicObservation
Parent: Observation
Id: epic-observation
Title: "Epic Observation Profile"
Description: "Profile of the Observation resource for Epic data"
* status MS
* code MS
* subject 1..1
* subject only Reference(EpicPatient)
* subject MS
* effectiveDateTime MS
* valueQuantity MS
* valueString MS
* valueCodeableConcept MS
* component MS
""",
    "Encounter": """
Profile: EpicEncounter
Parent: Encounter
Id: epic-encounter
Title: "Epic Encounter Profile"
Description: "Profile of the Encounter resource for Epic data"
* status MS
* class MS
* type MS
* subject 1..1
* subject only Reference(EpicPatient)
* subject MS
* period MS
* reasonCode MS
* diagnosis MS
* diagnosis.condition MS
* diagnosis.rank MS
* location MS
* serviceProvider MS
"""
}

def check_node_npm():
    """
    Check if Node.js and npm are installed.
    
    Returns:
        Tuple of (node_installed, npm_installed)
    """
    node_installed = False
    npm_installed = False
    
    try:
        result = subprocess.run(
            ["node", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        node_version = result.stdout.strip()
        logger.info(f"Node.js is installed: {node_version}")
        node_installed = True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Node.js is not installed or not in PATH")
    
    try:
        result = subprocess.run(
            ["npm", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        npm_version = result.stdout.strip()
        logger.info(f"npm is installed: {npm_version}")
        npm_installed = True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("npm is not installed or not in PATH")
    
    return node_installed, npm_installed

def install_sushi():
    """
    Install SUSHI globally using npm.
    
    Returns:
        True if installation was successful, False otherwise
    """
    try:
        logger.info("Installing SUSHI globally...")
        
        result = subprocess.run(
            ["npm", "install", "-g", "fsh-sushi"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("SUSHI installed successfully")
        
        # Verify installation
        result = subprocess.run(
            ["sushi", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        
        sushi_version = result.stdout.strip()
        logger.info(f"SUSHI version: {sushi_version}")
        
        return True
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error installing SUSHI: {e}")
        logger.error(f"Stdout: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        logger.error(f"Stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        return False

def create_fsh_project(project_dir: Path):
    """
    Create a new FHIR Shorthand project.
    
    Args:
        project_dir: Directory to create the project in
        
    Returns:
        True if creation was successful, False otherwise
    """
    try:
        logger.info(f"Creating FSH project in {project_dir}")
        
        # Create the project directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create package.json
        package_json = {
            "name": "epic-fhir-profiles",
            "version": "0.1.0",
            "description": "FHIR profiles for Epic integration",
            "scripts": {
                "build": "sushi ."
            },
            "dependencies": {
                "fsh-sushi": "^2.0.0"
            }
        }
        
        with open(project_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        # Create sushi-config.yaml
        sushi_config = """
id: epic-fhir-profiles
canonical: http://example.org/fhir/epic-profiles
name: EpicFHIRProfiles
status: draft
version: 0.1.0
fhirVersion: 4.0.1
dependencies:
  hl7.fhir.us.core: 3.1.1
copyrightYear: 2023+
releaseLabel: draft
publisher: Your Organization
"""
        
        with open(project_dir / "sushi-config.yaml", "w") as f:
            f.write(sushi_config)
        
        # Create directories
        (project_dir / "input" / "fsh").mkdir(parents=True, exist_ok=True)
        (project_dir / "input" / "images").mkdir(parents=True, exist_ok=True)
        (project_dir / "input" / "pagecontent").mkdir(parents=True, exist_ok=True)
        
        # Create example FSH files
        for resource_type, fsh_content in EXAMPLE_FSH_FILES.items():
            with open(project_dir / "input" / "fsh" / f"{resource_type.lower()}.fsh", "w") as f:
                f.write(fsh_content)
        
        # Create aliases.fsh
        aliases = """
// External Code Systems
Alias: $v2-0203 = http://terminology.hl7.org/CodeSystem/v2-0203
Alias: $loinc = http://loinc.org
Alias: $sct = http://snomed.info/sct
Alias: $ucum = http://unitsofmeasure.org

// External Extensions
Alias: $us-core-race = http://hl7.org/fhir/us/core/StructureDefinition/us-core-race
Alias: $us-core-ethnicity = http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity
"""
        
        with open(project_dir / "input" / "fsh" / "aliases.fsh", "w") as f:
            f.write(aliases)
        
        # Create README in the project
        readme = """# Epic FHIR Profiles

This directory contains FHIR Shorthand (FSH) definitions for custom FHIR profiles used in the Epic FHIR integration.

## Building

To build the profiles:

```bash
npm run build
```

This will create the FHIR structure definitions in the `output` directory.

## Profiles

- EpicPatient: Custom profile of Patient resource
- EpicObservation: Custom profile of Observation resource
- EpicEncounter: Custom profile of Encounter resource

## Usage

After building, the output can be used with the FHIR Validator to validate resources against these profiles.
"""
        
        with open(project_dir / "README.md", "w") as f:
            f.write(readme)
        
        logger.info(f"FSH project created successfully in {project_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating FSH project: {e}")
        return False

def build_fsh_project(project_dir: Path):
    """
    Build a FHIR Shorthand project using SUSHI.
    
    Args:
        project_dir: Directory containing the FSH project
        
    Returns:
        True if build was successful, False otherwise
    """
    try:
        logger.info(f"Building FSH project in {project_dir}")
        
        # Run SUSHI to build the project
        result = subprocess.run(
            ["sushi", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("FSH project built successfully")
        logger.info(f"Output: {result.stdout}")
        
        return True
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error building FSH project: {e}")
        logger.error(f"Stdout: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        logger.error(f"Stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        return False

def configure_fhir_validator(fsh_output_dir: Path, validator_dir: Path):
    """
    Configure the FHIR Validator to use the custom profiles.
    
    Args:
        fsh_output_dir: Directory containing the built FSH project
        validator_dir: Directory containing the FHIR Validator
        
    Returns:
        True if configuration was successful, False otherwise
    """
    try:
        logger.info(f"Configuring FHIR Validator in {validator_dir} to use profiles from {fsh_output_dir}")
        
        # Read the validator configuration
        config_file = validator_dir / "validator_config.json"
        if not config_file.exists():
            logger.error(f"Validator configuration file not found: {config_file}")
            return False
        
        with open(config_file, "r") as f:
            config = json.load(f)
        
        # Update the configuration to include the custom profiles
        package_dir = fsh_output_dir / "package"
        if not package_dir.exists():
            logger.error(f"Package directory not found: {package_dir}")
            return False
        
        # Add the package directory to the IG paths
        if "ig" not in config:
            config["ig"] = {}
        if "local" not in config["ig"]:
            config["ig"]["local"] = []
        
        package_path = str(package_dir)
        if package_path not in config["ig"]["local"]:
            config["ig"]["local"].append(package_path)
        
        # Write the updated configuration
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"FHIR Validator configured to use custom profiles from {package_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error configuring FHIR Validator: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up FHIR Shorthand (FSH) and SUSHI")
    parser.add_argument(
        "--dir", 
        help="Directory to create FSH project in", 
        default="fhir_profiles"
    )
    parser.add_argument(
        "--validator-dir", 
        help="Directory containing the FHIR Validator", 
        default="tools/fhir-validator"
    )
    parser.add_argument(
        "--build", 
        action="store_true", 
        help="Build the FSH project after setup"
    )
    parser.add_argument(
        "--install-sushi", 
        action="store_true", 
        help="Install SUSHI globally"
    )
    
    args = parser.parse_args()
    
    # Convert directories to absolute paths
    project_dir = Path(args.dir).resolve()
    validator_dir = Path(args.validator_dir).resolve()
    
    # Check if Node.js and npm are installed
    node_installed, npm_installed = check_node_npm()
    if not node_installed or not npm_installed:
        logger.error("Node.js and npm are required to use SUSHI")
        logger.error("Please install them before continuing")
        sys.exit(1)
    
    # Install SUSHI if requested
    if args.install_sushi:
        if not install_sushi():
            logger.error("Failed to install SUSHI")
            sys.exit(1)
    
    # Create FSH project
    if not create_fsh_project(project_dir):
        logger.error("Failed to create FSH project")
        sys.exit(1)
    
    # Build the project if requested
    if args.build:
        if not build_fsh_project(project_dir):
            logger.error("Failed to build FSH project")
            sys.exit(1)
        
        # Configure the FHIR Validator to use the custom profiles
        output_dir = project_dir / "output"
        if output_dir.exists() and validator_dir.exists():
            if not configure_fhir_validator(output_dir, validator_dir):
                logger.warning("Failed to configure FHIR Validator to use custom profiles")
        else:
            logger.warning(f"Output directory {output_dir} or validator directory {validator_dir} not found")
    
    logger.info("FSH setup completed successfully")
    logger.info(f"FSH project directory: {project_dir}")
    if args.build:
        logger.info(f"Built profiles are in: {project_dir / 'output'}")
    else:
        logger.info("To build the profiles, run: cd {project_dir} && npm run build")

if __name__ == "__main__":
    main() 