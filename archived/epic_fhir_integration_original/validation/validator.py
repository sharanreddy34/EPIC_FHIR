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

logger = logging.getLogger(__name__)


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
        
    def get_infos(self) -> List[Dict]:
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
                ig_directory: Optional[str] = None, 
                fhir_version: str = "R4",
                validator_path: Optional[str] = None):
        """
        Initialize a FHIR validator.
        
        Args:
            ig_directory: Directory containing implementation guides and profiles
            fhir_version: FHIR version to validate against
            validator_path: Path to the HAPI FHIR Validator JAR file
        """
        self.fhir_version = fhir_version
        self.ig_directory = ig_directory
        self.validator_path = validator_path or self._get_validator_path()
        
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
    
    def validate(self, resource: Union[Dict, str]) -> ValidationResult:
        """
        Validate a FHIR resource.
        
        Args:
            resource: FHIR resource as a dictionary or JSON string
            
        Returns:
            ValidationResult: Validation result
        """
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
            
        # Create a temporary file for the resource
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_file.write(resource_json.encode("utf-8"))
            temp_file_path = temp_file.name
            
        try:
            # Build the validation command
            command = ["java", "-jar", self.validator_path, temp_file_path, "-output", "json"]
            
            # Add the FHIR version
            command.extend(["-version", self.fhir_version])
            
            # Add the implementation guide directory if specified
            if self.ig_directory and os.path.exists(self.ig_directory):
                command.extend(["-ig", self.ig_directory])
                
            # Run the validator
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse the validation output
            try:
                validation_results = json.loads(result.stdout)
                issues = validation_results.get("issues", [])
                return ValidationResult(resource_type, resource_id, issues)
            except json.JSONDecodeError:
                # If the output is not valid JSON, create a result with an error
                error_issue = {
                    "level": ValidationLevel.ERROR.value,
                    "message": f"Error parsing validator output: {result.stdout}"
                }
                return ValidationResult(resource_type, resource_id, [error_issue])
                
        except Exception as e:
            # Handle any exceptions
            error_issue = {
                "level": ValidationLevel.ERROR.value,
                "message": f"Error running validator: {str(e)}"
            }
            return ValidationResult(resource_type, resource_id, [error_issue])
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    def validate_batch(self, resources: List[Union[Dict, str]]) -> List[ValidationResult]:
        """
        Validate a batch of FHIR resources.
        
        Args:
            resources: List of FHIR resources as dictionaries or JSON strings
            
        Returns:
            List[ValidationResult]: List of validation results
        """
        results = []
        for resource in resources:
            results.append(self.validate(resource))
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