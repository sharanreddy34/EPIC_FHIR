"""
FHIR Quality Assessment Module

This module provides utilities to assess the quality of FHIR resources
based on the quality tier framework:
- Bronze: Raw data with minimal validation
- Silver: Enhanced data with cleansing and basic extensions
- Gold: Fully conformant, enriched data optimized for analytics and LLM use

The module evaluates resources for common quality issues:
1. Data Consistency
2. Profile Conformance
3. Cardinality Requirements
4. Extension Structure
5. Data Loss
6. Validation Logic
7. Narrative Completeness
8. Sensitive Data Handling
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FHIRQualityAssessor:
    """Assesses the quality of FHIR resources against quality tier requirements."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the quality assessor.
        
        Args:
            debug: Enable debug logging
        """
        if debug:
            logger.setLevel(logging.DEBUG)
            
        # Define known FHIR validation rules
        # These are simplified examples, a real implementation would be more comprehensive
        self.required_fields = {
            "Patient": ["resourceType", "id"],
            "Observation": ["resourceType", "id", "status", "code"],
            "Encounter": ["resourceType", "id", "status"]
        }
        
        # US Core required fields (simplified)
        self.us_core_required = {
            "Patient": ["identifier", "name"],
            "Observation": ["status", "category", "code", "subject"],
            "Encounter": ["status", "class", "subject"]
        }
        
        # Known valid coded values
        self.valid_values = {
            "Patient.gender": ["male", "female", "other", "unknown"],
            "Observation.status": ["registered", "preliminary", "final", "amended", "corrected", 
                                 "cancelled", "entered-in-error", "unknown"],
            "Encounter.status": ["planned", "arrived", "triaged", "in-progress", "onleave", 
                               "finished", "cancelled", "entered-in-error", "unknown"]
        }
        
    def assess_resource(self, resource: Dict) -> Dict:
        """
        Assess the quality of a FHIR resource.
        
        Args:
            resource: FHIR resource to assess
            
        Returns:
            Quality assessment results
        """
        if not resource or not isinstance(resource, dict):
            return {"error": "Invalid resource provided"}
            
        resource_type = resource.get("resourceType")
        if not resource_type:
            return {"error": "Resource missing resourceType"}
            
        # Determine current quality tier
        tier = self._determine_quality_tier(resource)
        
        # Run quality checks
        results = {
            "resource_type": resource_type,
            "resource_id": resource.get("id", "unknown"),
            "quality_tier": tier,
            "issues": [],
            "score": 0,  # Will be calculated based on checks
            "passed_checks": 0,
            "total_checks": 0
        }
        
        # Run all quality checks
        self._check_data_consistency(resource, results)
        self._check_required_fields(resource, results)
        self._check_profile_conformance(resource, results)
        self._check_extension_structure(resource, results)
        self._check_narrative(resource, results)
        self._check_sensitive_data(resource, results)
        
        # Calculate overall score (0-100)
        if results["total_checks"] > 0:
            results["score"] = int((results["passed_checks"] / results["total_checks"]) * 100)
            
        return results
    
    def assess_directory(self, directory: Path) -> Dict:
        """
        Assess all FHIR resources in a directory.
        
        Args:
            directory: Directory containing FHIR resources
            
        Returns:
            Aggregated quality assessment results
        """
        if not directory.exists() or not directory.is_dir():
            return {"error": f"Directory {directory} does not exist or is not a directory"}
            
        results = {
            "directory": str(directory),
            "assessed_at": datetime.datetime.now().isoformat(),
            "resources_assessed": 0,
            "resources_by_type": {},
            "resources_by_tier": {
                "BRONZE": 0,
                "SILVER": 0,
                "GOLD": 0,
                "UNKNOWN": 0
            },
            "average_score": 0,
            "issue_counts": {},
            "resource_results": []
        }
        
        # Find all JSON files recursively
        json_files = list(directory.glob("**/*.json"))
        
        total_score = 0
        for file_path in json_files:
            try:
                with open(file_path, 'r') as f:
                    resource = json.load(f)
                    
                # Skip if not a FHIR resource
                if not isinstance(resource, dict) or "resourceType" not in resource:
                    logger.debug(f"Skipping {file_path} - not a FHIR resource")
                    continue
                    
                # Assess this resource
                assessment = self.assess_resource(resource)
                
                # Skip if assessment failed
                if "error" in assessment:
                    logger.warning(f"Failed to assess {file_path}: {assessment['error']}")
                    continue
                    
                # Add file path to assessment
                assessment["file_path"] = str(file_path)
                
                # Add to aggregate results
                results["resources_assessed"] += 1
                results["resource_results"].append(assessment)
                
                # Update resource type counts
                resource_type = resource["resourceType"]
                if resource_type not in results["resources_by_type"]:
                    results["resources_by_type"][resource_type] = 0
                results["resources_by_type"][resource_type] += 1
                
                # Update tier counts
                tier = assessment["quality_tier"]
                results["resources_by_tier"][tier] += 1
                
                # Update issue counts
                for issue in assessment["issues"]:
                    issue_type = issue["type"]
                    if issue_type not in results["issue_counts"]:
                        results["issue_counts"][issue_type] = 0
                    results["issue_counts"][issue_type] += 1
                    
                # Add to total score
                total_score += assessment["score"]
                
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {str(e)}")
                continue
                
        # Calculate average score
        if results["resources_assessed"] > 0:
            results["average_score"] = int(total_score / results["resources_assessed"])
            
        return results
    
    def generate_report(self, results: Dict, output_file: Optional[Path] = None) -> str:
        """
        Generate a quality assessment report.
        
        Args:
            results: Quality assessment results
            output_file: Optional file to write the report to
            
        Returns:
            Report as markdown text
        """
        # Generate markdown report
        report = "# FHIR Resource Quality Assessment Report\n\n"
        
        # Add report time
        report += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Add summary section
        report += "## Summary\n\n"
        resources_assessed = results.get("resources_assessed", 0)
        report += f"Total resources assessed: {resources_assessed}\n\n"
        
        if resources_assessed > 0:
            report += f"Average quality score: {results.get('average_score', 0)}/100\n\n"
            
            # Resources by tier
            report += "### Resources by Quality Tier\n\n"
            report += "| Tier | Count | Percentage |\n"
            report += "|------|-------|------------|\n"
            
            tiers = results.get("resources_by_tier", {})
            for tier, count in sorted(tiers.items()):
                if resources_assessed > 0:
                    percentage = int((count / resources_assessed) * 100)
                else:
                    percentage = 0
                report += f"| {tier} | {count} | {percentage}% |\n"
                
            # Resources by type
            report += "\n### Resources by Type\n\n"
            report += "| Resource Type | Count |\n"
            report += "|--------------|-------|\n"
            
            types = results.get("resources_by_type", {})
            for resource_type, count in sorted(types.items()):
                report += f"| {resource_type} | {count} |\n"
                
            # Issue counts
            report += "\n### Issues by Type\n\n"
            report += "| Issue Type | Count |\n"
            report += "|------------|-------|\n"
            
            issues = results.get("issue_counts", {})
            for issue_type, count in sorted(issues.items()):
                report += f"| {issue_type} | {count} |\n"
                
            # Add detailed section for resources with issues
            report += "\n## Detailed Issues\n\n"
            
            # Group by resource type
            issues_by_type = {}
            for resource_result in results.get("resource_results", []):
                if resource_result.get("issues"):
                    resource_type = resource_result.get("resource_type")
                    if resource_type not in issues_by_type:
                        issues_by_type[resource_type] = []
                    issues_by_type[resource_type].append(resource_result)
            
            # Output issues by resource type
            for resource_type, resources in sorted(issues_by_type.items()):
                report += f"### {resource_type} Issues\n\n"
                
                for resource in resources:
                    resource_id = resource.get("resource_id", "unknown")
                    score = resource.get("score", 0)
                    file_path = resource.get("file_path", "")
                    
                    report += f"#### {resource_type}/{resource_id} (Score: {score}/100)\n\n"
                    if file_path:
                        report += f"File: {file_path}\n\n"
                        
                    report += "| Issue Type | Description | Severity |\n"
                    report += "|------------|-------------|----------|\n"
                    
                    for issue in resource.get("issues", []):
                        report += f"| {issue.get('type', '')} | {issue.get('description', '')} | {issue.get('severity', '')} |\n"
                        
                    report += "\n"
        
        # Write report to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Quality assessment report written to {output_file}")
            
        return report
    
    def _determine_quality_tier(self, resource: Dict) -> str:
        """Determine the quality tier of a resource based on its metadata."""
        # Check for explicit tier tag
        if "meta" in resource and "tag" in resource["meta"]:
            for tag in resource["meta"]["tag"]:
                if (tag.get("system") == "http://terminology.hl7.org/CodeSystem/v3-ObservationValue" and
                    tag.get("code") in ["BRONZE", "SILVER", "GOLD"]):
                    return tag["code"]
        
        # If no explicit tag, try to infer from content
        
        # Check if resource has a narrative - required for Gold
        has_narrative = "text" in resource and "div" in resource["text"]
        
        # Check if resource has US Core profile - indicator of Gold
        has_us_core = False
        if "meta" in resource and "profile" in resource["meta"]:
            has_us_core = any("us-core" in profile for profile in resource["meta"]["profile"])
            
        # Check if resource has extensions - indicator of at least Silver
        has_extensions = "extension" in resource and resource["extension"]
        
        # Check if resource has PHI security tags - indicator of Gold
        has_phi_tags = False
        if "meta" in resource and "security" in resource["meta"]:
            has_phi_tags = any(
                sec.get("code") == "PHI" for sec in resource["meta"]["security"]
            )
            
        # Make determination based on features
        if has_narrative and (has_us_core or has_phi_tags):
            return "GOLD"
        elif has_extensions or has_narrative:
            return "SILVER"
        else:
            return "BRONZE"
    
    def _check_data_consistency(self, resource: Dict, results: Dict) -> None:
        """Check for data consistency issues."""
        resource_type = resource.get("resourceType")
        
        # Track check count
        checks_to_run = 0
        checks_passed = 0
        
        # Patient-specific checks
        if resource_type == "Patient":
            # Gender consistency check
            if "gender" in resource and "_gender" in resource:
                checks_to_run += 1
                if "extension" in resource["_gender"]:
                    # Check for inconsistent data-absent-reason when gender is present
                    has_absent_reason = any(
                        ext.get("url") == "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
                        for ext in resource["_gender"]["extension"]
                    )
                    
                    if resource["gender"] is not None and has_absent_reason:
                        results["issues"].append({
                            "type": "Data Consistency",
                            "description": "Gender value present but has data-absent-reason extension",
                            "severity": "warning",
                            "path": "gender/_gender"
                        })
                    else:
                        checks_passed += 1
                else:
                    checks_passed += 1
            
            # Name components consistency
            if "name" in resource:
                for i, name in enumerate(resource["name"]):
                    # Check if family is present when given is present
                    if "given" in name:
                        checks_to_run += 1
                        if "family" not in name and "text" not in name:
                            results["issues"].append({
                                "type": "Data Consistency",
                                "description": f"Name has given name but no family name or text",
                                "severity": "warning",
                                "path": f"name[{i}]"
                            })
                        else:
                            checks_passed += 1
        
        # Observation-specific checks
        elif resource_type == "Observation":
            # Value consistency checks
            has_value = False
            value_fields = ["valueQuantity", "valueString", "valueBoolean", 
                           "valueInteger", "valueCodeableConcept"]
            
            for field in value_fields:
                if field in resource:
                    has_value = True
                    break
                    
            # Check if has value or dataAbsentReason
            checks_to_run += 1
            if not has_value:
                # Should have a dataAbsentReason
                has_reason = False
                if "dataAbsentReason" in resource:
                    has_reason = True
                    checks_passed += 1
                    
                if not has_reason:
                    results["issues"].append({
                        "type": "Data Consistency",
                        "description": "Observation has no value and no dataAbsentReason",
                        "severity": "warning",
                        "path": "Observation"
                    })
            else:
                checks_passed += 1
        
        # Update results
        results["total_checks"] += checks_to_run
        results["passed_checks"] += checks_passed
    
    def _check_required_fields(self, resource: Dict, results: Dict) -> None:
        """Check for missing required fields."""
        resource_type = resource.get("resourceType")
        
        # Skip if we don't have requirements for this type
        if resource_type not in self.required_fields:
            return
            
        required = self.required_fields[resource_type]
        
        # Track check count
        checks_to_run = len(required)
        checks_passed = 0
        
        for field in required:
            if "." in field:
                # Nested field
                parts = field.split(".")
                obj = resource
                found = True
                
                for part in parts:
                    if part not in obj:
                        found = False
                        break
                    obj = obj[part]
                    
                if found:
                    checks_passed += 1
                else:
                    results["issues"].append({
                        "type": "Missing Required Field",
                        "description": f"Missing required field {field}",
                        "severity": "error",
                        "path": field
                    })
            else:
                # Top-level field
                if field in resource:
                    checks_passed += 1
                else:
                    results["issues"].append({
                        "type": "Missing Required Field",
                        "description": f"Missing required field {field}",
                        "severity": "error",
                        "path": field
                    })
        
        # Update results
        results["total_checks"] += checks_to_run
        results["passed_checks"] += checks_passed
    
    def _check_profile_conformance(self, resource: Dict, results: Dict) -> None:
        """Check for profile conformance issues."""
        resource_type = resource.get("resourceType")
        
        # Skip if we don't have US Core requirements for this type
        if resource_type not in self.us_core_required:
            return
            
        # Check if resource claims US Core conformance
        claiming_us_core = False
        if "meta" in resource and "profile" in resource["meta"]:
            claiming_us_core = any(
                "us-core" in profile for profile in resource["meta"]["profile"]
            )
            
        # If not claiming US Core, skip detailed checks
        if not claiming_us_core:
            return
            
        # Check US Core required fields
        required = self.us_core_required[resource_type]
        
        # Track check count
        checks_to_run = len(required)
        checks_passed = 0
        
        for field in required:
            if "." in field:
                # Nested field
                parts = field.split(".")
                obj = resource
                found = True
                
                for part in parts:
                    if part not in obj:
                        found = False
                        break
                    obj = obj[part]
                    
                if found:
                    checks_passed += 1
                else:
                    results["issues"].append({
                        "type": "Profile Conformance",
                        "description": f"Resource claims US Core but missing {field}",
                        "severity": "error",
                        "path": field
                    })
            else:
                # Top-level field
                if field in resource:
                    checks_passed += 1
                else:
                    results["issues"].append({
                        "type": "Profile Conformance",
                        "description": f"Resource claims US Core but missing {field}",
                        "severity": "error",
                        "path": field
                    })
        
        # Update results
        results["total_checks"] += checks_to_run
        results["passed_checks"] += checks_passed
    
    def _check_extension_structure(self, resource: Dict, results: Dict) -> None:
        """Check for extension structure issues."""
        if "extension" not in resource:
            return
            
        # Track check count
        checks_to_run = 0
        checks_passed = 0
        
        for i, extension in enumerate(resource["extension"]):
            # Check if extension has a URL
            checks_to_run += 1
            if "url" not in extension:
                results["issues"].append({
                    "type": "Extension Structure",
                    "description": "Extension missing required URL",
                    "severity": "error",
                    "path": f"extension[{i}]"
                })
            else:
                checks_passed += 1
                
            # Check complex extensions
            if extension.get("url") == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
                checks_to_run += 1
                if "extension" not in extension:
                    results["issues"].append({
                        "type": "Extension Structure",
                        "description": "US Core race extension missing nested extensions",
                        "severity": "error",
                        "path": f"extension[{i}]"
                    })
                else:
                    # Check for required nested extensions
                    has_omb = any(
                        nested.get("url") == "ombCategory" for nested in extension["extension"]
                    )
                    has_text = any(
                        nested.get("url") == "text" for nested in extension["extension"]
                    )
                    
                    if not has_omb or not has_text:
                        results["issues"].append({
                            "type": "Extension Structure",
                            "description": "US Core race extension missing required components",
                            "severity": "warning",
                            "path": f"extension[{i}]"
                        })
                    else:
                        checks_passed += 1
                        
        # Update results
        results["total_checks"] += checks_to_run
        results["passed_checks"] += checks_passed
    
    def _check_narrative(self, resource: Dict, results: Dict) -> None:
        """Check for narrative issues."""
        # Track check count
        checks_to_run = 1
        checks_passed = 0
        
        # Check if resource has a narrative
        if "text" not in resource:
            results["issues"].append({
                "type": "Narrative",
                "description": "Resource is missing narrative text",
                "severity": "info",
                "path": "text"
            })
        elif "div" not in resource["text"]:
            results["issues"].append({
                "type": "Narrative",
                "description": "Resource narrative is missing div element",
                "severity": "warning",
                "path": "text.div"
            })
        elif "status" not in resource["text"]:
            results["issues"].append({
                "type": "Narrative",
                "description": "Resource narrative is missing status",
                "severity": "warning",
                "path": "text.status"
            })
        else:
            # Narrative exists - check content quality
            div_content = resource["text"]["div"]
            
            # Check for xhtml namespace
            if 'xmlns' not in div_content:
                results["issues"].append({
                    "type": "Narrative",
                    "description": "Narrative div is missing xmlns attribute",
                    "severity": "info",
                    "path": "text.div"
                })
            elif len(div_content) < 40:
                # Very short narratives are likely low quality
                results["issues"].append({
                    "type": "Narrative",
                    "description": "Narrative content appears too brief",
                    "severity": "info",
                    "path": "text.div"
                })
            else:
                checks_passed += 1
        
        # Update results
        results["total_checks"] += checks_to_run
        results["passed_checks"] += checks_passed
    
    def _check_sensitive_data(self, resource: Dict, results: Dict) -> None:
        """Check for sensitive data handling issues."""
        resource_type = resource.get("resourceType")
        
        # Skip checks for non-PHI resource types
        non_phi_types = ["OperationOutcome", "CapabilityStatement", "Bundle"]
        if resource_type in non_phi_types:
            return
            
        # Determine if resource likely contains PHI
        contains_phi = False
        
        # Patient resources almost always contain PHI
        if resource_type == "Patient":
            contains_phi = True
        # Observations may contain PHI
        elif resource_type == "Observation" and "subject" in resource:
            contains_phi = True
        # Encounters may contain PHI
        elif resource_type == "Encounter" and "subject" in resource:
            contains_phi = True
            
        # If resource contains PHI, check for security tags
        if contains_phi:
            # Track check count
            checks_to_run = 1
            checks_passed = 0
            
            has_phi_tag = False
            if "meta" in resource and "security" in resource["meta"]:
                has_phi_tag = any(
                    (sec.get("system") == "http://terminology.hl7.org/CodeSystem/v3-ActCode" and
                     sec.get("code") == "PHI") or
                    "PHI" in sec.get("code", "")
                    for sec in resource["meta"]["security"]
                )
                
            if not has_phi_tag:
                results["issues"].append({
                    "type": "Sensitive Data",
                    "description": "Resource likely contains PHI but is missing PHI security tag",
                    "severity": "warning",
                    "path": "meta.security"
                })
            else:
                checks_passed += 1
                
            # Update results
            results["total_checks"] += checks_to_run
            results["passed_checks"] += checks_passed

def assess_resource(resource: Dict, debug: bool = False) -> Dict:
    """
    Assess the quality of a single FHIR resource.
    
    Args:
        resource: FHIR resource to assess
        debug: Enable debug logging
        
    Returns:
        Quality assessment results
    """
    assessor = FHIRQualityAssessor(debug=debug)
    return assessor.assess_resource(resource)
    
def assess_directory(directory: Path, debug: bool = False) -> Dict:
    """
    Assess all FHIR resources in a directory.
    
    Args:
        directory: Directory containing FHIR resources
        debug: Enable debug logging
        
    Returns:
        Aggregated quality assessment results
    """
    assessor = FHIRQualityAssessor(debug=debug)
    return assessor.assess_directory(directory)
    
def generate_report(results: Dict, output_file: Optional[Path] = None) -> str:
    """
    Generate a quality assessment report.
    
    Args:
        results: Quality assessment results
        output_file: Optional file to write the report to
        
    Returns:
        Report as markdown text
    """
    assessor = FHIRQualityAssessor()
    return assessor.generate_report(results, output_file) 