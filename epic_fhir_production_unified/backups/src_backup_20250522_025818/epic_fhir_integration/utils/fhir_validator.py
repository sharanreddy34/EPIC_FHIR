"""
FHIR resource validation using the official HL7 FHIR Validator.

This module provides utilities for validating FHIR resources against
official HL7 FHIR profiles and implementation guides using the official validator.
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from fhir.resources.resource import Resource

logger = logging.getLogger(__name__)

class FHIRValidator:
    """Interface to the HL7 FHIR Validator for validating resources against profiles."""
    
    def __init__(self, validator_path: Optional[Path] = None, version: str = "4.0.1", terminology_server: Optional[str] = None):
        """
        Initialize a new FHIR validator.
        
        Args:
            validator_path: Path to the validator JAR file. If None, will look for it in common directories.
            version: FHIR version to validate against (default: 4.0.1)
            terminology_server: URL of terminology server to use for validating codes
        """
        self.version = version
        self.terminology_server = terminology_server
        
        # If validator_path is not provided, look in common locations
        if validator_path is None:
            common_paths = [
                Path.cwd() / "tools" / "fhir-validator" / "validator_cli.jar",
                Path.home() / "fhir-validator" / "validator_cli.jar",
                Path("/usr/local/bin/fhir-validator/validator_cli.jar"),
                Path("C:/fhir-validator/validator_cli.jar"),
            ]
            
            for path in common_paths:
                if path.exists():
                    validator_path = path
                    break
        
        # If validator_path is still None or doesn't exist, raise error
        if validator_path is None or not validator_path.exists():
            possible_paths = [str(p) for p in common_paths]
            raise FileNotFoundError(
                f"FHIR Validator JAR not found. Please install it using the setup_fhir_validator.py script "
                f"or specify its location. Tried: {possible_paths}"
            )
        
        self.validator_path = validator_path
        logger.info(f"Using FHIR Validator at {validator_path}")
    
    def validate_json(self, json_data: Union[str, Dict[str, Any]], profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a FHIR resource as JSON against a profile.
        
        Args:
            json_data: FHIR resource data as a JSON string or dictionary
            profile: Optional profile to validate against. If None, will use profiles in resource.meta.profile
            
        Returns:
            Dictionary with validation results
        """
        # Convert dict to JSON string if necessary
        if isinstance(json_data, dict):
            json_data = json.dumps(json_data, indent=2)
        
        # Create a temporary file for the JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_data)
            temp_file = f.name
        
        try:
            # Prepare the command
            cmd = ["java", "-jar", str(self.validator_path), temp_file, "-version", self.version]
            
            # Add profile if specified
            if profile:
                cmd.extend(["-profile", profile])
            
            # Add terminology server if specified
            if self.terminology_server:
                cmd.extend(["-tx", self.terminology_server])
            else:
                cmd.extend(["-tx", "n/a"])  # Skip terminology validation if no server
            
            # Run the validator
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            # Parse the output
            return self._parse_validator_output(result.stdout, result.stderr)
            
        finally:
            # Clean up the temporary file
            os.unlink(temp_file)
    
    def validate_resource(self, resource: Resource, profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a FHIR resource object against a profile.
        
        Args:
            resource: FHIR resource object
            profile: Optional profile to validate against. If None, will use profiles in resource.meta.profile
            
        Returns:
            Dictionary with validation results
        """
        # Convert resource to JSON
        json_data = resource.json()
        
        # Validate using the JSON validator
        return self.validate_json(json_data, profile)
    
    def _parse_validator_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Parse the output from the FHIR validator.
        
        Args:
            stdout: Standard output from the validator
            stderr: Standard error from the validator
            
        Returns:
            Dictionary with validation results
        """
        # Initialize results
        results = {
            "valid": False,
            "issues": [],
            "errors": [],
            "warnings": [],
            "information": [],
            "raw_output": stdout,
            "raw_error": stderr
        }
        
        # Check for overall success
        if "Success: 0 errors" in stdout:
            results["valid"] = True
        
        # Extract issues
        issue_pattern = re.compile(r'(Error|Warning|Information)\s+@\s+(.*?)\s+(.*)')
        for line in stdout.split('\n'):
            match = issue_pattern.search(line)
            if match:
                severity, location, message = match.groups()
                issue = {
                    "severity": severity.lower(),
                    "location": location,
                    "message": message.strip()
                }
                
                results["issues"].append(issue)
                
                # Add to specific category
                if severity.lower() == "error":
                    results["errors"].append(issue)
                elif severity.lower() == "warning":
                    results["warnings"].append(issue)
                elif severity.lower() == "information":
                    results["information"].append(issue)
        
        return results

class ValidationReportGenerator:
    """Generate structured validation reports for FHIR resources."""
    
    def __init__(self, validator: FHIRValidator):
        """
        Initialize a validation report generator.
        
        Args:
            validator: FHIR validator to use
        """
        self.validator = validator
    
    def generate_report_for_resource(self, resource: Resource, profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a validation report for a FHIR resource.
        
        Args:
            resource: FHIR resource to validate
            profile: Optional profile to validate against
            
        Returns:
            Validation report dictionary
        """
        validation_result = self.validator.validate_resource(resource, profile)
        
        # Create a report with summary information
        report = {
            "resource_type": resource.resource_type,
            "resource_id": resource.id,
            "profile": profile or "default",
            "valid": validation_result["valid"],
            "error_count": len(validation_result["errors"]),
            "warning_count": len(validation_result["warnings"]),
            "info_count": len(validation_result["information"]),
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "information": validation_result["information"],
        }
        
        return report
    
    def generate_report_for_bundle(self, resources: List[Resource], profile_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate a validation report for multiple FHIR resources.
        
        Args:
            resources: List of FHIR resources to validate
            profile_map: Optional mapping of resource types to profiles
            
        Returns:
            Validation report dictionary
        """
        if profile_map is None:
            profile_map = {}
        
        # Initialize the report
        report = {
            "total_resources": len(resources),
            "valid_resources": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "resource_reports": [],
            "resource_types": {},
            "summary": {}
        }
        
        # Process each resource
        for resource in resources:
            # Get the profile to validate against
            profile = profile_map.get(resource.resource_type)
            
            # Generate report for this resource
            resource_report = self.generate_report_for_resource(resource, profile)
            report["resource_reports"].append(resource_report)
            
            # Update summary counts
            if resource_report["valid"]:
                report["valid_resources"] += 1
            
            report["error_count"] += resource_report["error_count"]
            report["warning_count"] += resource_report["warning_count"]
            report["info_count"] += resource_report["info_count"]
            
            # Update resource type stats
            if resource.resource_type not in report["resource_types"]:
                report["resource_types"][resource.resource_type] = {
                    "count": 0,
                    "valid": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "info_count": 0
                }
            
            rt_stats = report["resource_types"][resource.resource_type]
            rt_stats["count"] += 1
            if resource_report["valid"]:
                rt_stats["valid"] += 1
            rt_stats["error_count"] += resource_report["error_count"]
            rt_stats["warning_count"] += resource_report["warning_count"]
            rt_stats["info_count"] += resource_report["info_count"]
        
        # Calculate overall validity percentage
        report["valid_percent"] = (report["valid_resources"] / report["total_resources"] * 100) if report["total_resources"] > 0 else 100
        
        # Generate summary text
        summary = []
        summary.append(f"Validated {report['total_resources']} resources")
        summary.append(f"Valid: {report['valid_resources']} ({report['valid_percent']:.1f}%)")
        summary.append(f"Errors: {report['error_count']}")
        summary.append(f"Warnings: {report['warning_count']}")
        summary.append(f"Information: {report['info_count']}")
        
        if report["resource_types"]:
            summary.append("\nResource Types:")
            for rt, stats in report["resource_types"].items():
                valid_pct = (stats["valid"] / stats["count"] * 100) if stats["count"] > 0 else 100
                summary.append(f"  {rt}: {stats['valid']}/{stats['count']} valid ({valid_pct:.1f}%), {stats['error_count']} errors")
        
        report["summary"]["text"] = "\n".join(summary)
        
        return report 