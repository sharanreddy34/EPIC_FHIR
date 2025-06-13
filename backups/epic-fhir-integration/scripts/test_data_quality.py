#!/usr/bin/env python3
"""
Data Quality Test Script for FHIR Resources

This script tests the quality of FHIR resources across Bronze, Silver, and Gold tiers.
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
logger = logging.getLogger("data_quality_test")

from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter
from epic_fhir_integration.validation.validator import FHIRValidator

class DataQualityTest:
    def __init__(self, input_dir, output_dir, mock_mode=False):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mock_mode = mock_mode or os.environ.get("USE_MOCK_MODE") == "true"
        
        logger.info(f"Data quality test initialized with mock mode: {'enabled' if self.mock_mode else 'disabled'}")
        
        self.fhirpath_adapter = FHIRPathAdapter()
        self.validator = FHIRValidator(mock_mode=self.mock_mode)
        
        # Results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tiers": {},
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
    
    def test_tier(self, tier):
        """Test resources for a specific tier."""
        logger.info(f"Testing {tier} tier")
        
        resources = self.load_resources(tier)
        if not resources:
            logger.warning(f"No resources found for tier: {tier}")
            self.results["tiers"][tier] = {
                "resource_count": 0,
                "overall_quality": 0,
                "validation_results": {}
            }
            return
        
        # Count resources
        resource_counts = {k: len(v) for k, v in resources.items()}
        total_count = sum(resource_counts.values())
        
        # Validate resources
        validation_results = {}
        for resource_type, resources_list in resources.items():
            validation_results[resource_type] = []
            for resource in resources_list:
                result = self.validator.validate(resource)
                validation_results[resource_type].append({
                    "resource_id": resource.get("id", "unknown"),
                    "is_valid": result.is_valid,
                    "error_count": len(result.get_errors()),
                    "warning_count": len(result.get_warnings())
                })
        
        # Calculate quality score
        # Simple score: percentage of valid resources
        valid_count = 0
        for results in validation_results.values():
            valid_count += sum(1 for r in results if r["is_valid"])
        
        quality_score = (valid_count / total_count) * 100 if total_count > 0 else 0
        
        # Store results
        self.results["tiers"][tier] = {
            "resource_count": total_count,
            "resource_counts": resource_counts,
            "overall_quality": quality_score,
            "validation_results": validation_results
        }
        
        logger.info(f"{tier} tier: {valid_count}/{total_count} valid resources ({quality_score:.1f}% quality)")
    
    def run_tests(self):
        """Run tests for all tiers."""
        # Test each tier
        self.test_tier("bronze")
        self.test_tier("silver")
        self.test_tier("gold")
        
        # Generate report
        report_file = self.output_dir / "data_quality_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate Markdown report
        md_report = self.output_dir / "data_quality_report.md"
        with open(md_report, "w") as f:
            f.write("# FHIR Data Quality Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.mock_mode:
                f.write("**Note:** This report was generated in mock mode. Results are simulated.\n\n")
            
            f.write("## Quality Summary\n\n")
            f.write("| Tier | Resource Count | Quality Score |\n")
            f.write("|------|---------------|---------------|\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["tiers"]:
                    tier_data = self.results["tiers"][tier]
                    count = tier_data["resource_count"]
                    score = tier_data["overall_quality"]
                    f.write(f"| {tier.title()} | {count} | {score:.1f}% |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for tier in ["bronze", "silver", "gold"]:
                if tier in self.results["tiers"]:
                    tier_data = self.results["tiers"][tier]
                    f.write(f"### {tier.title()} Tier\n\n")
                    
                    f.write("**Resource Counts:**\n\n")
                    if "resource_counts" in tier_data:
                        for resource_type, count in tier_data["resource_counts"].items():
                            f.write(f"- {resource_type}: {count}\n")
                    
                    f.write("\n**Validation Results:**\n\n")
                    for resource_type, results in tier_data["validation_results"].items():
                        valid_count = sum(1 for r in results if r["is_valid"])
                        total_count = len(results)
                        f.write(f"- {resource_type}: {valid_count}/{total_count} valid\n")
        
        logger.info(f"Reports generated: {report_file} and {md_report}")
        return self.results

def main():
    parser = argparse.ArgumentParser(description="Test FHIR data quality across tiers")
    parser.add_argument("--input-dir", required=True, help="Input directory containing tier folders")
    parser.add_argument("--output-dir", required=True, help="Output directory for test results")
    parser.add_argument("--mock", action="store_true", help="Enable mock mode for testing without real dependencies")
    
    args = parser.parse_args()
    
    tester = DataQualityTest(args.input_dir, args.output_dir, mock_mode=args.mock)
    tester.run_tests()

if __name__ == "__main__":
    main()
