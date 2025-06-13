#!/usr/bin/env python3
"""
Validation Test Script for FHIR Resources

This script validates FHIR resources against profiles for each tier.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("validation_test")

from epic_fhir_integration.validation.validator import FHIRValidator

class ValidationTest:
    def __init__(self, input_dir, output_dir, mock_mode=False):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mock_mode = mock_mode or os.environ.get("USE_MOCK_MODE") == "true"
        
        logger.info(f"Validation test initialized with mock mode: {'enabled' if self.mock_mode else 'disabled'}")
        
        # Create validators
        self.base_validator = FHIRValidator(mock_mode=self.mock_mode)  # Basic FHIR R4 validation
        
        # Results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": {},
            "mock_mode": self.mock_mode
        }
    
    def load_resources(self, tier):
        """Load resources for a specific tier."""
        tier_dir = self.input_dir / tier
        if not tier_dir.exists():
            logger.warning(f"Directory not found for tier: {tier}")
            return {}
        
        resources = {}
        for file_path in tier_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    resource = json.load(f)
                    resource_type = resource.get("resourceType")
                    if resource_type:
                        if resource_type not in resources:
                            resources[resource_type] = []
                        resources[resource_type].append(resource)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        return resources
    
    def validate_resources(self, tier, resources):
        """Validate resources for a specific tier."""
        logger.info(f"Validating {tier} tier resources")
        
        # Validation results
        results = {}
        
        # Validate each resource type
        for resource_type, resources_list in resources.items():
            results[resource_type] = []
            
            for resource in resources_list:
                # Basic FHIR validation
                basic_result = self.base_validator.validate(resource)
                
                # Store results
                resource_id = resource.get("id", "unknown")
                result = {
                    "resource_id": resource_id,
                    "basic_validation": {
                        "is_valid": basic_result.is_valid,
                        "error_count": len(basic_result.get_errors()),
                        "warning_count": len(basic_result.get_warnings())
                    }
                }
                
                # For Gold tier, validate against US Core profiles if specified
                if tier == "gold" and resource.get("meta", {}).get("profile"):
                    profiles = resource["meta"]["profile"]
                    result["profile_validation"] = {}
                    
                    for profile in profiles:
                        # We only log this because we don't have the actual US Core profiles
                        logger.info(f"Resource {resource_id} claims conformance to profile: {profile}")
                        result["profile_validation"][profile] = {
                            "profile_claimed": True
                        }
                
                results[resource_type].append(result)
        
        return results
    
    def run_tests(self):
        """Run validation tests for all tiers."""
        # Test each tier
        for tier in ["bronze", "silver", "gold"]:
            resources = self.load_resources(tier)
            if resources:
                self.results["validation_results"][tier] = self.validate_resources(tier, resources)
        
        # Generate report
        report_file = self.output_dir / "validation_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate Markdown report
        md_report = self.output_dir / "validation_report.md"
        with open(md_report, "w") as f:
            f.write("# FHIR Validation Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.mock_mode:
                f.write("**Note:** This report was generated in mock mode. Results are simulated.\n\n")
            
            f.write("## Validation Summary\n\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["validation_results"]:
                    tier_results = self.results["validation_results"][tier]
                    f.write(f"### {tier.title()} Tier\n\n")
                    
                    # Count resources and validation results
                    total_resources = 0
                    valid_resources = 0
                    
                    for resource_type, results in tier_results.items():
                        type_total = len(results)
                        type_valid = sum(1 for r in results if r["basic_validation"]["is_valid"])
                        
                        total_resources += type_total
                        valid_resources += type_valid
                        
                        f.write(f"- {resource_type}: {type_valid}/{type_total} valid\n")
                    
                    # Overall summary
                    percent_valid = (valid_resources / total_resources * 100) if total_resources > 0 else 0
                    f.write(f"\n**Overall:** {valid_resources}/{total_resources} valid ({percent_valid:.1f}%)\n\n")
                    
                    # Profile conformance for Gold tier
                    if tier == "gold":
                        f.write("\n**Profile Conformance:**\n\n")
                        for resource_type, results in tier_results.items():
                            for result in results:
                                if "profile_validation" in result:
                                    resource_id = result["resource_id"]
                                    for profile, profile_result in result["profile_validation"].items():
                                        f.write(f"- {resource_type}/{resource_id}: Claims conformance to {profile}\n")
        
        logger.info(f"Reports generated: {report_file} and {md_report}")
        return self.results

def main():
    parser = argparse.ArgumentParser(description="Validate FHIR resources against profiles")
    parser.add_argument("--input-dir", required=True, help="Input directory containing tier folders")
    parser.add_argument("--output-dir", required=True, help="Output directory for test results")
    parser.add_argument("--mock", action="store_true", help="Enable mock mode for testing without real dependencies")
    
    args = parser.parse_args()
    
    tester = ValidationTest(args.input_dir, args.output_dir, mock_mode=args.mock)
    tester.run_tests()

if __name__ == "__main__":
    main()
