"""
FHIR Validator Module.

This module provides tools for validating FHIR resources against profiles
and implementation guides using the HL7 FHIR Validator.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Issue reported by the FHIR validator."""
    
    severity: str  # "error", "warning", "information"
    location: str  # Location in the resource
    message: str   # Issue message
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
        """Create a ValidationIssue from a dictionary.
        
        Args:
            data: Dictionary representation of the issue.
            
        Returns:
            ValidationIssue instance.
        """
        return cls(
            severity=data.get("severity", "error"),
            location=data.get("location", ""),
            message=data.get("message", ""),
        )


@dataclass
class ValidationResult:
    """Result of validating a FHIR resource."""
    
    resource_id: str               # ID of the validated resource
    resource_type: str             # Type of the validated resource
    is_valid: bool                 # Whether the resource is valid
    issues: List[ValidationIssue]  # List of validation issues
    
    @property
    def has_errors(self) -> bool:
        """Check if the validation result has errors.
        
        Returns:
            True if there are error-level issues, False otherwise.
        """
        return any(issue.severity == "error" for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if the validation result has warnings.
        
        Returns:
            True if there are warning-level issues, False otherwise.
        """
        return any(issue.severity == "warning" for issue in self.issues)
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues.
        
        Returns:
            List of error-level issues.
        """
        return [issue for issue in self.issues if issue.severity == "error"]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues.
        
        Returns:
            List of warning-level issues.
        """
        return [issue for issue in self.issues if issue.severity == "warning"]
    
    def get_information(self) -> List[ValidationIssue]:
        """Get all information-level issues.
        
        Returns:
            List of information-level issues.
        """
        return [issue for issue in self.issues if issue.severity == "information"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the validation result to a dictionary.
        
        Returns:
            Dictionary representation of the validation result.
        """
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "is_valid": self.is_valid,
            "issues": [
                {
                    "severity": issue.severity,
                    "location": issue.location,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


class FHIRValidator:
    """Validator for FHIR resources.
    
    This class provides methods for validating FHIR resources against
    profiles and implementation guides using the HL7 FHIR Validator.
    """
    
    def __init__(
        self,
        validator_path: Optional[str] = None,
        ig_directory: Optional[str] = None,
    ):
        """Initialize the FHIR validator.
        
        Args:
            validator_path: Path to the FHIR validator JAR file.
            ig_directory: Directory containing implementation guides.
        """
        self.validator_path = validator_path or self._find_validator_path()
        self.ig_directory = ig_directory
    
    def _find_validator_path(self) -> str:
        """Find the FHIR validator JAR file.
        
        Returns:
            Path to the FHIR validator JAR file.
            
        Raises:
            FileNotFoundError: If the validator JAR file cannot be found.
        """
        # Check common locations
        possible_locations = [
            "/opt/validator/validator_cli.jar",  # Container default
            "ops/validator/validator_cli.jar",   # Local repository
            Path.home() / "validator/validator_cli.jar",  # User home
            "/usr/local/bin/validator.jar",      # System-wide install
        ]
        
        for loc in possible_locations:
            if Path(loc).exists():
                return str(loc)
        
        # Check environment variable
        if os.environ.get("FHIR_VALIDATOR_JAR"):
            return os.environ["FHIR_VALIDATOR_JAR"]
            
        # Try to find validator.sh or validator.bat in PATH
        validator_script = shutil.which("validator.sh") or shutil.which("validator.bat")
        if validator_script:
            # The script likely points to the JAR file
            return validator_script
            
        raise FileNotFoundError(
            "FHIR validator JAR not found. Please specify the path."
        )
    
    def validate(
        self,
        resource: Dict[str, Any],
        profile: Optional[str] = None,
    ) -> ValidationResult:
        """Validate a FHIR resource against a profile.
        
        Args:
            resource: FHIR resource to validate.
            profile: Profile to validate against.
            
        Returns:
            Validation result.
        """
        # Extract resource information
        resource_id = resource.get("id", "unknown")
        resource_type = resource.get("resourceType", "unknown")
        
        # Create a temporary file for the resource
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
            json.dump(resource, temp_file)
            temp_file.flush()
            
            # Run the validator
            cmd = ["java", "-jar", self.validator_path, temp_file.name, "-output", "json"]
            
            # Add profile if specified
            if profile:
                cmd.extend(["-profile", profile])
                
            # Add implementation guides if specified
            if self.ig_directory:
                cmd.extend(["-ig", self.ig_directory])
                
            # Run the validator
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                
                # Parse the output
                if result.returncode == 0:
                    # Successful validation (may still have issues)
                    issues = self._parse_validator_output(result.stdout)
                    is_valid = not any(issue.severity == "error" for issue in issues)
                    
                    return ValidationResult(
                        resource_id=resource_id,
                        resource_type=resource_type,
                        is_valid=is_valid,
                        issues=issues,
                    )
                else:
                    # Validation error
                    logger.error(f"Validation failed: {result.stderr}")
                    return ValidationResult(
                        resource_id=resource_id,
                        resource_type=resource_type,
                        is_valid=False,
                        issues=[
                            ValidationIssue(
                                severity="error",
                                location="",
                                message=f"Validation process failed: {result.stderr}",
                            )
                        ],
                    )
                    
            except Exception as e:
                logger.error(f"Error running validator: {str(e)}")
                return ValidationResult(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    is_valid=False,
                    issues=[
                        ValidationIssue(
                            severity="error",
                            location="",
                            message=f"Validation process error: {str(e)}",
                        )
                    ],
                )
    
    def validate_batch(
        self,
        resources: List[Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> List[ValidationResult]:
        """Validate a batch of FHIR resources.
        
        Args:
            resources: List of FHIR resources to validate.
            profile: Profile to validate against.
            
        Returns:
            List of validation results.
        """
        return [self.validate(resource, profile) for resource in resources]
    
    def compile_fsh(
        self,
        fsh_directory: str,
        output_directory: Optional[str] = None,
    ) -> bool:
        """Compile FHIR Shorthand (FSH) to IG package.
        
        Args:
            fsh_directory: Directory containing FSH files.
            output_directory: Directory to write the compiled IG package.
                If not specified, a subdirectory of fsh_directory is used.
                
        Returns:
            True if compilation was successful, False otherwise.
        """
        try:
            # Check for SUSHI installation
            sushi_path = shutil.which("sushi")
            if not sushi_path:
                logger.error("SUSHI not found. Please install it with 'npm install -g fsh-sushi'")
                return False
                
            # Resolve output directory
            if output_directory is None:
                output_directory = os.path.join(fsh_directory, "output")
                
            # Create output directory if it doesn't exist
            os.makedirs(output_directory, exist_ok=True)
            
            # Run SUSHI
            cmd = [sushi_path, fsh_directory, "-o", output_directory]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                logger.info(f"FSH compilation successful: {result.stdout}")
                return True
            else:
                logger.error(f"FSH compilation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error compiling FSH: {str(e)}")
            return False
    
    def compile_and_validate(
        self,
        fsh_directory: str,
        resources: List[Dict[str, Any]],
        output_directory: Optional[str] = None,
    ) -> List[ValidationResult]:
        """Compile FSH and validate resources against the compiled profiles.
        
        Args:
            fsh_directory: Directory containing FSH files.
            resources: List of FHIR resources to validate.
            output_directory: Directory to write the compiled IG package.
                If not specified, a subdirectory of fsh_directory is used.
                
        Returns:
            List of validation results.
        """
        # Compile FSH
        if not self.compile_fsh(fsh_directory, output_directory):
            # Compilation failed, return invalid results
            return [
                ValidationResult(
                    resource_id=resource.get("id", "unknown"),
                    resource_type=resource.get("resourceType", "unknown"),
                    is_valid=False,
                    issues=[
                        ValidationIssue(
                            severity="error",
                            location="",
                            message="FSH compilation failed",
                        )
                    ],
                )
                for resource in resources
            ]
            
        # Resolve output directory
        if output_directory is None:
            output_directory = os.path.join(fsh_directory, "output")
            
        # Set IG directory for validation
        self.ig_directory = output_directory
        
        # Validate resources
        return self.validate_batch(resources)
    
    def _parse_validator_output(self, output: str) -> List[ValidationIssue]:
        """Parse the output of the FHIR validator.
        
        Args:
            output: Output of the FHIR validator.
            
        Returns:
            List of validation issues.
        """
        try:
            # Try to parse as JSON
            data = json.loads(output)
            
            # Extract issues
            issues = []
            for issue_data in data.get("issues", []):
                issue = ValidationIssue.from_dict(issue_data)
                issues.append(issue)
                
            return issues
            
        except json.JSONDecodeError:
            # Fall back to parsing text output
            issues = []
            
            # Simple parsing of text output
            for line in output.splitlines():
                if "error" in line.lower():
                    issues.append(ValidationIssue(
                        severity="error",
                        location="",
                        message=line.strip(),
                    ))
                elif "warning" in line.lower():
                    issues.append(ValidationIssue(
                        severity="warning",
                        location="",
                        message=line.strip(),
                    ))
                elif "information" in line.lower():
                    issues.append(ValidationIssue(
                        severity="information",
                        location="",
                        message=line.strip(),
                    ))
                    
            return issues 