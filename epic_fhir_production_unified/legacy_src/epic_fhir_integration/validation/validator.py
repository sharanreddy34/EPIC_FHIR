"""
FHIR validator using HAPI FHIR Validator.

This module provides a validator for FHIR resources using the HAPI FHIR Validator.
It supports validation against FHIR Shorthand (FSH) profiles.
"""

import os
import json
import logging
import subprocess
import tempfile
import enum
from typing import Any, Dict, List, Optional, Union
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Use Docker validator by default, can be overridden with environment variable
VALIDATOR_DOCKER = os.getenv("VALIDATOR_DOCKER", "fhir-validator:latest")
USE_DOCKER = os.getenv("USE_VALIDATOR_DOCKER", "true").lower() in ("true", "1", "yes")


class ValidationLevel(enum.Enum):
    """Validation severity levels."""
    
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFORMATION = "INFORMATION"


class ValidationResult:
    """Result of validating a FHIR resource."""
    
    def __init__(self, resource_type: str, resource_id: str, issues: List[Dict] = None):
        """
        Initialize a validation result.
        
        Args:
            resource_type: Type of the validated resource
            resource_id: ID of the validated resource
            issues: List of validation issues
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.issues = issues or []
        self.is_valid = not any(issue.get("level") == ValidationLevel.ERROR.value for issue in self.issues)
        
    def has_errors(self) -> bool:
        """
        Check if the validation result has errors.
        
        Returns:
            bool: True if there are any errors, False otherwise
        """
        return any(issue.get("level") == ValidationLevel.ERROR.value for issue in self.issues)
        
    def has_warnings(self) -> bool:
        """
        Check if the validation result has warnings.
        
        Returns:
            bool: True if there are any warnings, False otherwise
        """
        return any(issue.get("level") == ValidationLevel.WARNING.value for issue in self.issues)
        
    def get_errors(self) -> List[Dict]:
        """
        Get all error issues.
        
        Returns:
            List[Dict]: List of error issues
        """
        return [issue for issue in self.issues if issue.get("level") == ValidationLevel.ERROR.value]
        
    def get_warnings(self) -> List[Dict]:
        """
        Get all warning issues.
        
        Returns:
            List[Dict]: List of warning issues
        """
        return [issue for issue in self.issues if issue.get("level") == ValidationLevel.WARNING.value]
        
    def get_info(self) -> List[Dict]:
        """
        Get all informational issues.
        
        Returns:
            List[Dict]: List of informational issues
        """
        return [issue for issue in self.issues if issue.get("level") == ValidationLevel.INFORMATION.value]
        
    def to_dict(self) -> Dict:
        """
        Convert the validation result to a dictionary.
        
        Returns:
            Dict: Dictionary representation of the validation result
        """
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "is_valid": self.is_valid,
            "issues": self.issues,
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationResult":
        """
        Create a validation result from a dictionary.
        
        Args:
            data: Dictionary representation of a validation result
            
        Returns:
            ValidationResult: Validation result
        """
        return cls(
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            issues=data.get("issues", [])
        )


class FHIRValidator:
    """Validator for FHIR resources using HAPI FHIR Validator."""
    
    def __init__(self, 
                ig_directory: Optional[Union[str, Path]] = None, 
                fhir_version: str = "R4",
                validator_path: Optional[str] = None,
                mock_mode: bool = False,
                java_debug_port: Optional[int] = None):
        """
        Initialize a FHIR validator.
        
        Args:
            ig_directory: Directory containing implementation guides and profiles
            fhir_version: FHIR version to validate against
            validator_path: Path to the HAPI FHIR Validator JAR file
            mock_mode: Whether to use mock implementations for testing
            java_debug_port: Optional port for Java remote debugging
        """
        self.fhir_version = fhir_version
        self.ig_directory = Path(ig_directory) if ig_directory else None
        self.validator_path = validator_path or self._get_validator_path()
        self.mock_mode = mock_mode
        self.java_debug_port = java_debug_port
        
    def _get_validator_path(self) -> str:
        """
        Get the path to the HAPI FHIR Validator JAR file.
        
        Returns:
            str: Path to the validator JAR file
        """
        # Try to find the validator in common locations
        validator_names = [
            "validator_cli.jar",
            "org.hl7.fhir.validator.jar",
            "hapi-fhir-validator-cli.jar"
        ]
        
        potential_paths = [
            os.path.join(os.path.expanduser("~"), "fhir", name) for name in validator_names
        ]
        potential_paths.extend([
            os.path.join("/usr/local/bin", name) for name in validator_names
        ])
        potential_paths.extend([
            os.path.join(".", name) for name in validator_names
        ])
        
        for path in potential_paths:
            if os.path.exists(path):
                return path
                
        # Try to download the validator
        return self._download_validator()
        
    def _download_validator(self) -> str:
        """
        Download the HAPI FHIR Validator.
        
        Returns:
            str: Path to the downloaded validator
        """
        try:
            import urllib.request
            
            # Create a directory for the validator
            validator_dir = os.path.join(os.path.expanduser("~"), "fhir")
            os.makedirs(validator_dir, exist_ok=True)
            
            # Download the validator
            validator_url = "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar"
            validator_path = os.path.join(validator_dir, "validator_cli.jar")
            
            logger.info(f"Downloading HAPI FHIR Validator from {validator_url}")
            urllib.request.urlretrieve(validator_url, validator_path)
            
            return validator_path
            
        except Exception as e:
            logger.error(f"Error downloading HAPI FHIR Validator: {e}")
            raise ValueError(
                "HAPI FHIR Validator not found. Please download it manually from "
                "https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar "
                "and specify its path using the validator_path parameter."
            )
    
    def validate(self, resource: Union[Dict, str], profile: Optional[str] = None) -> ValidationResult:
        """
        Validate a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or JSON string
            profile: Optional profile to validate against
            
        Returns:
            ValidationResult: Validation result
        """
        if self.mock_mode:
            # Simulate a successful validation in mock mode
            resource_type = "Unknown"
            resource_id = "mock_id"
            if isinstance(resource, dict):
                resource_type = resource.get("resourceType", "Unknown")
                resource_id = resource.get("id", "mock_id")
            elif isinstance(resource, str):
                try:
                    res_dict = json.loads(resource)
                    resource_type = res_dict.get("resourceType", "Unknown")
                    resource_id = res_dict.get("id", "mock_id")
                except json.JSONDecodeError:
                    pass # Keep defaults
            
            logger.info(f"Mock validation for {resource_type}/{resource_id}")
            return ValidationResult(resource_type, resource_id, [])

        # Convert the resource to a JSON string if it's a dictionary
        if isinstance(resource, dict):
            resource_json = json.dumps(resource)
        else:
            resource_json = resource
            
        # Extract resource type and ID for the result
        try:
            resource_dict = json.loads(resource_json)
            resource_type = resource_dict.get("resourceType", "Unknown")
            resource_id = resource_dict.get("id", "Unknown")
        except Exception:
            resource_type = "Unknown"
            resource_id = "Unknown"
        
        # Create a temporary directory for the validation
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input file
            input_path = os.path.join(tmpdir, "input.json")
            with open(input_path, "w") as f:
                f.write(resource_json)
            
            # Create output file path
            output_path = os.path.join(tmpdir, "output.json")
            
            try:
                if USE_DOCKER:
                    # Use Docker for validation to ensure Java 11
                    command = [
                        "docker", "run", "--rm",
                        "-v", f"{tmpdir}:/data",
                        VALIDATOR_DOCKER,
                        "-output", "/data/output.json"
                    ]
                    
                    # Add the FHIR version
                    command.extend(["-version", self.fhir_version])
                    
                    # Add the implementation guide directory if specified
                    if self.ig_directory and os.path.exists(self.ig_directory):
                        # Need to mount the IG directory
                        ig_mount = f"{self.ig_directory}:/ig"
                        command[3:3] = ["-v", ig_mount]
                        command.extend(["-ig", "/ig"])
                        
                    # Add profile if specified
                    if profile:
                        command.extend(["-profile", profile])
                    
                    # Add the input file at the end
                    command.append("/data/input.json")
                    
                    logger.debug(f"Executing Docker FHIR validation command: {' '.join(command)}")
                else:
                    # Build the standard Java validation command
                    command = ["java"]
                    if self.java_debug_port:
                        debug_options = f"-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:{self.java_debug_port}"
                        command.append(debug_options)
                        logger.info(f"FHIR Validator will be started with Java debug options: {debug_options}")
                    command.extend(["-jar", str(self.validator_path), input_path,
                               "-output", output_path]) # Output to specific file
                    
                    # Add the FHIR version
                    command.extend(["-version", self.fhir_version])
                    
                    # Add the implementation guide directory if specified
                    if self.ig_directory and os.path.exists(self.ig_directory):
                        command.extend(["-ig", str(self.ig_directory)])
                        
                    # Add profile if specified
                    if profile:
                        command.extend(["-profile", profile])
                    
                    logger.debug(f"Executing FHIR validation command: {' '.join(command)}")
                
                # Run the validator
                result = subprocess.run(
                    command,
                    capture_output=True, # Capture stdout/stderr for logging
                    text=True,
                    check=False # We will check returncode manually
                )
                
                logger.debug(f"Validator stdout:\n{result.stdout}")
                if result.stderr:
                    logger.debug(f"Validator stderr:\n{result.stderr}")

                if result.returncode != 0:
                    # Validator exited with an error
                    error_message = f"FHIR Validator process failed with exit code {result.returncode}. Stderr: {result.stderr.strip()}. Stdout: {result.stdout.strip()}"
                    logger.error(error_message)
                    error_issue = {
                        "level": ValidationLevel.ERROR.value,
                        "message": error_message
                    }
                    return ValidationResult(resource_type, resource_id, [error_issue])

                # Parse the validation output from the temporary output file
                try:
                    with open(output_path, 'r') as f:
                        output_content = f.read()
                    if not output_content.strip():
                        # Output file is empty, this often means validator had an internal error
                        # but still exited with 0, or no issues were found (empty OperationOutcome)
                        logger.warning(f"FHIR Validator output file is empty. Stdout: {result.stdout.strip()}. Stderr: {result.stderr.strip()}")
                        # Check if stdout contains "All OK" or similar success indicators if output is empty
                        if "All OK" in result.stdout or (result.stdout.strip() == "" and result.stderr.strip() == ""):
                             return ValidationResult(resource_type, resource_id, []) # Assume valid if empty output and no errors
                        
                        error_issue = {
                            "level": ValidationLevel.ERROR.value,
                            "message": f"FHIR Validator output file was empty. Validator stdout: {result.stdout.strip()}. Stderr: {result.stderr.strip()}"
                        }
                        return ValidationResult(resource_type, resource_id, [error_issue])

                    validation_results = json.loads(output_content)
                    issues = validation_results.get("messages", []) # HL7 validator uses "messages"
                    # Adapt "messages" to "issues" structure if needed, or ensure ValidationResult handles it
                    # For now, assuming ValidationResult can take the raw messages
                    return ValidationResult(resource_type, resource_id, issues)
                except json.JSONDecodeError as jde:
                    error_message = f"Error parsing validator JSON output from {output_path}: {str(jde)}. Content: {output_content[:500]}"
                    logger.error(error_message)
                    error_issue = {
                        "level": ValidationLevel.ERROR.value,
                        "message": error_message
                    }
                    return ValidationResult(resource_type, resource_id, [error_issue])
                except Exception as e_parse:
                    error_message = f"Unexpected error parsing validator output file {output_path}: {str(e_parse)}"
                    logger.error(error_message)
                    error_issue = {
                        "level": ValidationLevel.ERROR.value,
                        "message": error_message
                    }
                    return ValidationResult(resource_type, resource_id, [error_issue])
                    
            except Exception as e_run:
                # Handle any exceptions during subprocess run or setup
                error_message = f"Error running validator process: {str(e_run)}"
                logger.error(error_message, exc_info=True)
                error_issue = {
                    "level": ValidationLevel.ERROR.value,
                    "message": error_message
                }
                return ValidationResult(resource_type, resource_id, [error_issue])
                
    def validate_batch(self, resources: List[Union[Dict, str]], profile: Optional[str] = None) -> List[ValidationResult]:
        """
        Validate a batch of FHIR resources.
        
        Args:
            resources: List of FHIR resources as dictionaries or JSON strings
            profile: Optional profile to validate against
            
        Returns:
            List[ValidationResult]: List of validation results
        """
        results = []
        for resource in resources:
            results.append(self.validate(resource, profile=profile))
        return results
    
    def compile_fsh(self, fsh_directory: str, output_directory: Optional[str] = None) -> str:
        """
        Compile FHIR Shorthand (FSH) files to FHIR resources.
        
        Args:
            fsh_directory: Directory containing FSH files
            output_directory: Optional directory to output compiled resources
                If not provided, a temporary directory will be created
                
        Returns:
            str: Path to the directory containing compiled resources
        """
        if not output_directory:
            output_directory = tempfile.mkdtemp()
            
        # Use mock compilation when in mock mode
        if self.mock_mode:
            logger.info(f"Mock compilation of FSH files in {fsh_directory} to {output_directory}")
            # Create a basic output structure to simulate SUSHI
            os.makedirs(os.path.join(output_directory, "package"), exist_ok=True)
            os.makedirs(os.path.join(output_directory, "fsh-generated", "resources"), exist_ok=True)
            
            # Create a dummy package.json
            package_json = os.path.join(output_directory, "package", "package.json")
            with open(package_json, "w") as f:
                f.write('{"name": "mock-ig", "version": "1.0.0", "fhirVersions": ["4.0.1"]}')
                
            return output_directory
            
        try:
            # Check if Sushi CLI is installed
            result = subprocess.run(
                ["sushi", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise ValueError(
                    "FHIR Shorthand compiler (Sushi) not found. "
                    "Please install it with 'npm install -g fsh-sushi'"
                )
                
            # Run Sushi to compile FSH files
            result = subprocess.run(
                ["sushi", fsh_directory, "-o", output_directory],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise ValueError(f"Error compiling FSH files: {result.stderr}")
                
            return output_directory
            
        except Exception as e:
            logger.error(f"Error compiling FSH files: {e}")
            raise
            
    def compile_and_validate(self, 
                           fsh_directory: str, 
                           resources: List[Union[Dict, str]]) -> List[ValidationResult]:
        """
        Compile FHIR Shorthand (FSH) files and validate resources against them.
        
        Args:
            fsh_directory: Directory containing FSH files
            resources: List of FHIR resources to validate
            
        Returns:
            List[ValidationResult]: List of validation results
        """
        # Compile FSH files
        output_directory = self.compile_fsh(fsh_directory)
        
        try:
            # Set the IG directory to the compiled resources
            self.ig_directory = output_directory
            
            # Validate resources
            return self.validate_batch(resources)
            
        finally:
            # Clean up the temporary directory if it was created automatically
            if os.path.exists(output_directory) and output_directory != fsh_directory:
                shutil.rmtree(output_directory)
                
    def _get_resource_tier(self, resource: Dict) -> str:
        """
        Determine the tier level of a resource based on its content.
        
        Args:
            resource: FHIR resource dictionary
            
        Returns:
            str: 'bronze', 'silver', 'gold', or 'unknown'
        """
        # Look for tier extension
        extensions = resource.get("meta", {}).get("extension", [])
        for ext in extensions:
            if ext.get("url") == "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier":
                return ext.get("valueString", "unknown")
        
        # Look for profiles that might indicate gold tier
        profiles = resource.get("meta", {}).get("profile", [])
        if profiles and any("us-core" in profile for profile in profiles):
            return "gold"
            
        # Check for silver tier indicators (more complete data)
        if resource.get("identifier") and resource.get("meta"):
            return "silver"
            
        # Default to bronze
        return "bronze"
        
    def _create_mock_validation_result(self, resource_type: str, resource_id: str, tier: str) -> ValidationResult:
        """
        Create a mock validation result based on resource tier.
        
        Args:
            resource_type: Type of the validated resource
            resource_id: ID of the validated resource
            tier: Resource tier ('bronze', 'silver', 'gold')
            
        Returns:
            ValidationResult: Mock validation result
        """
        issues = []
        
        # For testing purposes, we can simulate issues based on tier
        if tier == "bronze":
            # Bronze tier has more issues
            issues.append({
                "level": ValidationLevel.ERROR.value,
                "code": "VALIDATION_ERROR",
                "message": "Resource is missing essential elements required by the profile"
            })
            issues.append({
                "level": ValidationLevel.WARNING.value,
                "code": "VALIDATION_WARNING",
                "message": "Resource uses non-standard extensions"
            })
        elif tier == "silver":
            # Silver tier has fewer issues
            issues.append({
                "level": ValidationLevel.WARNING.value,
                "code": "VALIDATION_WARNING",
                "message": "Resource uses extensions that could be standardized"
            })
            issues.append({
                "level": ValidationLevel.INFORMATION.value,
                "code": "VALIDATION_INFO",
                "message": "Consider adding additional context to the resource"
            })
        elif tier == "gold":
            # Gold tier has no errors, maybe informational issues
            issues.append({
                "level": ValidationLevel.INFORMATION.value,
                "code": "VALIDATION_INFO",
                "message": "Resource is fully compliant with the profile"
            })
        else:
            # Unknown tier - assume errors
            issues.append({
                "level": ValidationLevel.ERROR.value,
                "code": "VALIDATION_ERROR",
                "message": "Resource tier cannot be determined"
            })
        
        # Log the mock validation result
        logger.info(f"Mock validation for {resource_type}/{resource_id} ({tier} tier): {'valid' if tier == 'gold' else 'invalid'}")
        
        return ValidationResult(resource_type, resource_id, issues) 