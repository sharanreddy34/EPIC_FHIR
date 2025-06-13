"""
Validation Dashboard for FHIR validation results.

This module provides a dashboard for visualizing validation results.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class ValidationDashboard:
    """
    Dashboard for visualizing FHIR validation results.
    
    This class generates an interactive dashboard for exploring validation results
    for FHIR resources.
    """
    
    def __init__(self):
        """Initialize the validation dashboard."""
        pass
    
    def generate_dashboard(self, 
                          validation_file: Union[str, Path],
                          output_dir: Optional[Union[str, Path]] = None,
                          static_mode: bool = False) -> str:
        """
        Generate a dashboard from validation results.
        
        Args:
            validation_file: Path to JSON file containing validation results
            output_dir: Directory to save dashboard files (default: current directory)
            static_mode: Whether to generate a static HTML file or an interactive dashboard
            
        Returns:
            Path to the generated dashboard HTML file
        """
        # Load validation results from file
        try:
            with open(validation_file, 'r') as f:
                validation_results = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load validation results from {validation_file}: {e}")
            # Return a simple error dashboard
            return self._generate_error_dashboard(validation_file, output_dir, str(e))
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.getcwd()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate simple HTML dashboard as a placeholder for a more sophisticated implementation
        html_path = Path(output_dir) / "validation_dashboard.html"
        
        with open(html_path, 'w') as f:
            f.write(self._generate_html(validation_results, static_mode))
        
        logger.info(f"Generated validation dashboard at {html_path}")
        return str(html_path)
    
    def _generate_html(self, validation_results: Dict[str, Any], static_mode: bool) -> str:
        """
        Generate HTML for the dashboard.
        
        Args:
            validation_results: Dictionary containing validation results
            static_mode: Whether to generate a static HTML file
            
        Returns:
            HTML content as a string
        """
        # Calculate overall stats
        batch_results = validation_results.get('batch', {})
        total_resources = batch_results.get('total', 0)
        valid_resources = batch_results.get('valid_count', 0)
        invalid_resources = batch_results.get('invalid_count', 0)
        percent_valid = batch_results.get('percent_valid', 0)
        
        # Create a simple HTML dashboard
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FHIR Validation Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .card {{
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }}
        .metric {{
            display: inline-block;
            text-align: center;
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin: 10px;
            min-width: 150px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-title {{
            font-size: 14px;
            color: #6c757d;
        }}
        .good {{
            color: #28a745;
        }}
        .warning {{
            color: #ffc107;
        }}
        .bad {{
            color: #dc3545;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f1f1f1;
        }}
        .progress {{
            height: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            background-color: #28a745;
            text-align: center;
            color: white;
            line-height: 20px;
            font-size: 14px;
        }}
        .error-list {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px;
            max-height: 200px;
            overflow-y: auto;
        }}
        .error-item {{
            margin-bottom: 5px;
            padding: 5px;
            border-left: 3px solid #dc3545;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FHIR Validation Dashboard</h1>
        
        <div class="card">
            <h2>Overall Validation Results</h2>
            <div class="metric">
                <div class="metric-title">Total Resources</div>
                <div class="metric-value">{total_resources}</div>
            </div>
            <div class="metric">
                <div class="metric-title">Valid Resources</div>
                <div class="metric-value good">{valid_resources}</div>
            </div>
            <div class="metric">
                <div class="metric-title">Invalid Resources</div>
                <div class="metric-value bad">{invalid_resources}</div>
            </div>
            <div class="metric">
                <div class="metric-title">Valid Percentage</div>
                <div class="metric-value">{percent_valid:.1f}%</div>
            </div>
            
            <h3>Validation Progress</h3>
            <div class="progress">
                <div class="progress-bar" style="width: {percent_valid}%">{percent_valid:.1f}%</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Validation Results by Resource Type</h2>
            <table>
                <thead>
                    <tr>
                        <th>Resource Type</th>
                        <th>Valid</th>
                        <th>Error Count</th>
                        <th>Warning Count</th>
                        <th>Info Count</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add rows for each resource type
        for resource_type, results in validation_results.items():
            if resource_type == "batch":
                continue
            
            is_valid = results.get("is_valid", False)
            valid_class = "good" if is_valid else "bad"
            error_count = results.get("error_count", 0)
            warning_count = results.get("warning_count", 0)
            info_count = results.get("info_count", 0)
            
            html += f"""
                    <tr>
                        <td>{resource_type}</td>
                        <td class="{valid_class}">{is_valid}</td>
                        <td>{error_count}</td>
                        <td>{warning_count}</td>
                        <td>{info_count}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>Validation Errors</h2>
"""
        
        # Add validation errors for each resource type
        for resource_type, results in validation_results.items():
            if resource_type == "batch" or not results.get("errors"):
                continue
            
            html += f"""
            <h3>{resource_type} Errors</h3>
            <div class="error-list">
"""
            
            for error in results["errors"]:
                html += f"""
                <div class="error-item">{error}</div>
"""
            
            html += """
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_error_dashboard(self, validation_file: Union[str, Path], 
                                 output_dir: Optional[Union[str, Path]],
                                 error_message: str) -> str:
        """
        Generate an error dashboard when validation file can't be loaded.
        
        Args:
            validation_file: Path to validation file that caused the error
            output_dir: Directory to save dashboard file
            error_message: Error message to display
            
        Returns:
            Path to the generated error dashboard HTML file
        """
        # Determine output directory
        if output_dir is None:
            output_dir = os.getcwd()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate error HTML
        html_path = Path(output_dir) / "validation_dashboard_error.html"
        
        with open(html_path, 'w') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FHIR Validation Dashboard - Error</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .error-card {{
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 20px auto;
            max-width: 800px;
            border-left: 5px solid #dc3545;
        }}
        h1 {{
            color: #dc3545;
        }}
        .code {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            font-family: monospace;
            white-space: pre-wrap;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="error-card">
        <h1>Error Loading Validation Results</h1>
        <p>An error occurred while loading validation results from:</p>
        <div class="code">{validation_file}</div>
        <p>Error details:</p>
        <div class="code">{error_message}</div>
    </div>
</body>
</html>
""")
        
        return str(html_path) 