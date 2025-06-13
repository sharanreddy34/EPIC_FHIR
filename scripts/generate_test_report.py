#!/usr/bin/env python3
"""
Generate a comprehensive test report from real-world testing results.
"""

import os
import sys
import json
import logging
import argparse
import glob
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_report")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate a comprehensive test report")
    parser.add_argument(
        "--input-dir",
        default="test_output",
        help="Directory containing test result files"
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory containing test log files"
    )
    parser.add_argument(
        "--output",
        default="test_report.md",
        help="Output file for the test report"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML report in addition to Markdown"
    )
    return parser.parse_args()

def find_latest_test_run(input_dir, log_dir):
    """Find the latest test run based on directory timestamps."""
    test_dirs = list(Path(input_dir).glob("e2e_test_*"))
    if not test_dirs:
        logger.error(f"No test output directories found in {input_dir}")
        return None
    
    # Sort by timestamp in directory name
    test_dirs.sort(key=lambda p: p.name, reverse=True)
    latest_dir = test_dirs[0]
    
    # Find matching log file
    timestamp = latest_dir.name.replace("e2e_test_", "")
    log_files = list(Path(log_dir).glob(f"real_world_test_{timestamp}*.log"))
    log_file = log_files[0] if log_files else None
    
    return {
        "output_dir": latest_dir,
        "log_file": log_file,
        "timestamp": timestamp
    }

def extract_environment_info(log_file):
    """Extract environment information from the log file."""
    if not log_file or not log_file.exists():
        return {}
    
    env_info = {
        "date": None,
        "test_mode": None,
        "force_fetch": None,
        "verbose": None
    }
    
    with open(log_file, "r") as f:
        in_header = False
        for line in f:
            line = line.strip()
            if "==== Epic FHIR Integration Real-World Testing ====" in line:
                in_header = True
                continue
            if in_header and "===========================" in line:
                break
            if in_header:
                if line.startswith("Date:"):
                    env_info["date"] = line.replace("Date:", "").strip()
                elif line.startswith("Test mode:"):
                    env_info["test_mode"] = line.replace("Test mode:", "").strip()
                elif line.startswith("Force fetch:"):
                    env_info["force_fetch"] = line.replace("Force fetch:", "").strip()
                elif line.startswith("Verbose:"):
                    env_info["verbose"] = line.replace("Verbose:", "").strip()
    
    # Additional environment info
    env_info["python_version"] = sys.version.split()[0]
    try:
        import subprocess
        java_version = subprocess.run(
            ["java", "-version"], 
            capture_output=True, 
            text=True, 
            check=False
        ).stderr
        env_info["java_version"] = java_version.split("\n")[0] if java_version else "Not found"
    except Exception as e:
        env_info["java_version"] = f"Error checking: {str(e)}"
    
    return env_info

def extract_test_results(output_dir):
    """Extract and analyze test results from output files."""
    results = {
        "auth": {
            "success": False,
            "data": None
        },
        "pathling": {
            "success": False,
            "data": None
        },
        "validation": {
            "success": False,
            "data": None
        },
        "datasets": {
            "success": False,
            "data": None
        }
    }
    
    # Check auth results
    auth_file = output_dir / "auth_extract_analyze_results.json"
    if auth_file.exists():
        try:
            with open(auth_file, "r") as f:
                auth_data = json.load(f)
            results["auth"]["success"] = True
            results["auth"]["data"] = auth_data
        except Exception as e:
            logger.error(f"Error reading auth results: {str(e)}")
    
    # Check Pathling results
    pathling_count = output_dir / "pathling_patient_count.json"
    if pathling_count.exists():
        try:
            with open(pathling_count, "r") as f:
                pathling_data = json.load(f)
            results["pathling"]["success"] = True
            results["pathling"]["data"] = pathling_data
        except Exception as e:
            logger.error(f"Error reading Pathling results: {str(e)}")
    
    # Check validation results
    validation_file = output_dir / "validation_report.json"
    if validation_file.exists():
        try:
            with open(validation_file, "r") as f:
                validation_data = json.load(f)
            results["validation"]["success"] = True
            results["validation"]["data"] = validation_data
        except Exception as e:
            logger.error(f"Error reading validation results: {str(e)}")
    
    # Check dataset results
    dataset_file = output_dir / "validated_patient_dataset.csv"
    if dataset_file.exists():
        try:
            # Just check if file exists and has content
            file_size = dataset_file.stat().st_size
            results["datasets"]["success"] = file_size > 0
            results["datasets"]["data"] = {
                "file_size": file_size,
                "path": str(dataset_file)
            }
        except Exception as e:
            logger.error(f"Error checking dataset results: {str(e)}")
    
    return results

def generate_markdown_report(env_info, test_results, output_file):
    """Generate a Markdown report from the test results."""
    with open(output_file, "w") as f:
        # Report header
        f.write("# Epic FHIR Integration Real-World Test Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Environment information
        f.write("## Test Environment\n\n")
        f.write(f"- Test Date: {env_info.get('date', 'Not available')}\n")
        f.write(f"- Test Mode: {env_info.get('test_mode', 'Not available')}\n")
        f.write(f"- Python Version: {env_info.get('python_version', 'Not available')}\n")
        f.write(f"- Java Version: {env_info.get('java_version', 'Not available')}\n\n")
        
        # Summary table
        f.write("## Test Summary\n\n")
        f.write("| Component | Status | Details |\n")
        f.write("|-----------|--------|--------|\n")
        
        # Authentication
        auth_status = "✅ Success" if test_results["auth"]["success"] else "❌ Failed"
        auth_details = "Patient and vital signs extracted" if test_results["auth"]["success"] else "Test failed"
        f.write(f"| Authentication & Extraction | {auth_status} | {auth_details} |\n")
        
        # Pathling
        pathling_status = "✅ Success" if test_results["pathling"]["success"] else "❌ Failed"
        if test_results["pathling"]["success"]:
            pathling_details = f"Count: {test_results['pathling']['data'].get('count', 0)}"
        else:
            pathling_details = "Test failed or not run"
        f.write(f"| Pathling Analytics | {pathling_status} | {pathling_details} |\n")
        
        # Validation
        validation_status = "✅ Success" if test_results["validation"]["success"] else "❌ Failed"
        if test_results["validation"]["success"]:
            valid_data = test_results["validation"]["data"]
            patient_valid = valid_data.get("patient", {}).get("valid", False)
            obs_count = valid_data.get("observations", {}).get("valid", 0)
            validation_details = f"Patient valid: {patient_valid}, Valid observations: {obs_count}"
        else:
            validation_details = "Test failed or not run"
        f.write(f"| FHIR Validation | {validation_status} | {validation_details} |\n")
        
        # Datasets
        datasets_status = "✅ Success" if test_results["datasets"]["success"] else "❌ Failed"
        datasets_details = "Datasets created successfully" if test_results["datasets"]["success"] else "Test failed or not run"
        f.write(f"| Dataset Generation | {datasets_status} | {datasets_details} |\n\n")
        
        # Detailed results
        if test_results["auth"]["success"] and test_results["auth"]["data"]:
            f.write("## Patient Information\n\n")
            patient = test_results["auth"]["data"].get("patient", {})
            f.write(f"- Patient ID: {patient.get('id', 'Not available')}\n")
            f.write(f"- Gender: {patient.get('gender', 'Not available')}\n")
            f.write(f"- Birth Date: {patient.get('birthDate', 'Not available')}\n\n")
            
            vital_signs = test_results["auth"]["data"].get("vitalSigns", [])
            if vital_signs:
                f.write("### Vital Signs\n\n")
                f.write("| Code | Description | Value | Unit | Date |\n")
                f.write("|------|-------------|-------|------|------|\n")
                for vs in vital_signs[:5]:  # Limit to 5 for brevity
                    f.write(f"| {vs.get('code', '')} | {vs.get('display', '')} | {vs.get('value', '')} | {vs.get('unit', '')} | {vs.get('date', '')} |\n")
                if len(vital_signs) > 5:
                    f.write(f"| ... | ... | ... | ... | ... |\n")
                f.write(f"\n*Total vital signs: {len(vital_signs)}*\n\n")
        
        if test_results["validation"]["success"] and test_results["validation"]["data"]:
            f.write("## Validation Results\n\n")
            valid_data = test_results["validation"]["data"]
            
            f.write("### Patient Validation\n\n")
            patient_valid = valid_data.get("patient", {})
            f.write(f"- Valid: {patient_valid.get('valid', False)}\n")
            f.write(f"- Issues: {patient_valid.get('issues_count', 0)}\n\n")
            
            f.write("### Observation Validation\n\n")
            obs_data = valid_data.get("observations", {})
            f.write(f"- Total: {obs_data.get('total', 0)}\n")
            f.write(f"- Valid: {obs_data.get('valid', 0)}\n")
            f.write(f"- Valid Percentage: {obs_data.get('percentage_valid', 0):.1f}%\n\n")
            
            f.write("### Condition Validation\n\n")
            cond_data = valid_data.get("conditions", {})
            f.write(f"- Total: {cond_data.get('total', 0)}\n")
            f.write(f"- Valid: {cond_data.get('valid', 0)}\n")
            f.write(f"- Valid Percentage: {cond_data.get('percentage_valid', 0):.1f}%\n\n")
        
        # Conclusion
        f.write("## Conclusion\n\n")
        all_success = all(component["success"] for component in test_results.values())
        if all_success:
            f.write("✅ All tests completed successfully. The Epic FHIR Integration is working properly with real-world data.\n\n")
        else:
            f.write("⚠️ Some tests failed. Please review the detailed test logs for more information.\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Ensure all tests are passing consistently\n")
        f.write("2. Test with additional patient datasets\n")
        f.write("3. Integrate with production systems\n")
        f.write("4. Develop additional analytics capabilities\n\n")
    
    logger.info(f"Markdown report generated: {output_file}")
    return output_file

def convert_markdown_to_html(markdown_file):
    """Convert Markdown report to HTML."""
    try:
        import markdown
        with open(markdown_file, "r") as f:
            md_content = f.read()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Epic FHIR Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
                h1 {{ color: #333366; }}
                h2 {{ color: #336699; margin-top: 20px; }}
                h3 {{ color: #339999; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            {markdown.markdown(md_content, extensions=['tables'])}
        </body>
        </html>
        """
        
        html_file = markdown_file.replace(".md", ".html")
        with open(html_file, "w") as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {html_file}")
        return html_file
    except ImportError:
        logger.warning("Python 'markdown' package not installed. Skipping HTML conversion.")
        return None

def main():
    """Main function."""
    args = parse_args()
    
    # Find latest test run
    test_run = find_latest_test_run(args.input_dir, args.log_dir)
    if not test_run:
        logger.error("No test run found")
        return 1
    
    logger.info(f"Processing test run from {test_run['timestamp']}")
    
    # Extract environment info
    env_info = extract_environment_info(test_run["log_file"])
    logger.info(f"Environment info extracted: {env_info}")
    
    # Extract test results
    test_results = extract_test_results(test_run["output_dir"])
    logger.info(f"Test results extracted")
    
    # Generate report
    report_file = generate_markdown_report(env_info, test_results, args.output)
    
    # Convert to HTML if requested
    if args.html:
        html_file = convert_markdown_to_html(report_file)
        if html_file:
            logger.info(f"HTML report generated: {html_file}")
    
    logger.info("Report generation complete")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 