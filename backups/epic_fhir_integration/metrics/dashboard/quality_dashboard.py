"""
Quality Dashboard for FHIR data quality metrics.

This module provides a dashboard for visualizing data quality metrics.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class QualityDashboard:
    """
    Dashboard for visualizing data quality metrics.
    
    This class generates an interactive dashboard for exploring data quality metrics
    for FHIR resources.
    """
    
    def __init__(self):
        """Initialize the quality dashboard."""
        pass
    
    def generate_dashboard(self, 
                          metrics_file: Union[str, Path],
                          output_dir: Optional[Union[str, Path]] = None,
                          static_mode: bool = False) -> str:
        """
        Generate a dashboard from quality metrics.
        
        Args:
            metrics_file: Path to JSON file containing quality metrics
            output_dir: Directory to save dashboard files (default: current directory)
            static_mode: Whether to generate a static HTML file or an interactive dashboard
            
        Returns:
            Path to the generated dashboard HTML file
        """
        # Load quality metrics from file
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load quality metrics from {metrics_file}: {e}")
            # Return a simple error dashboard
            return self._generate_error_dashboard(metrics_file, output_dir, str(e))
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.getcwd()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate simple HTML dashboard as a placeholder for a more sophisticated implementation
        html_path = Path(output_dir) / "quality_dashboard.html"
        
        with open(html_path, 'w') as f:
            f.write(self._generate_html(metrics, static_mode))
        
        logger.info(f"Generated quality dashboard at {html_path}")
        return str(html_path)
    
    def _generate_html(self, metrics: Dict[str, Any], static_mode: bool) -> str:
        """
        Generate HTML for the dashboard.
        
        Args:
            metrics: Dictionary containing quality metrics
            static_mode: Whether to generate a static HTML file
            
        Returns:
            HTML content as a string
        """
        # Create a simple HTML dashboard
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FHIR Data Quality Dashboard</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>FHIR Data Quality Dashboard</h1>
        <div class="card">
            <h2>Overall Quality Metrics</h2>
            <div class="metric">
                <div class="metric-title">Overall Score</div>
                <div class="metric-value">{metrics.get('overall_score', 'N/A')}%</div>
            </div>
            <div class="metric">
                <div class="metric-title">Resource Count</div>
                <div class="metric-value">{metrics.get('resource_count', 'N/A')}</div>
            </div>
            <div class="metric">
                <div class="metric-title">Resource Types</div>
                <div class="metric-value">{len(metrics.get('resource_types', []))}</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Quality by Resource Type</h2>
            <table>
                <thead>
                    <tr>
                        <th>Resource Type</th>
                        <th>Count</th>
                        <th>Quality Score</th>
                        <th>Completeness</th>
                        <th>Conformance</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add rows for each resource type
        for resource_type, metrics_data in metrics.get('resource_types', {}).items():
            quality_score = metrics_data.get('quality_score', 0)
            score_class = "good" if quality_score >= 80 else "warning" if quality_score >= 60 else "bad"
            
            html += f"""
                    <tr>
                        <td>{resource_type}</td>
                        <td>{metrics_data.get('count', 0)}</td>
                        <td class="{score_class}">{quality_score}%</td>
                        <td>{metrics_data.get('completeness', 'N/A')}%</td>
                        <td>{metrics_data.get('conformance', 'N/A')}%</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>Quality Issues</h2>
            <table>
                <thead>
                    <tr>
                        <th>Resource Type</th>
                        <th>Issue Type</th>
                        <th>Count</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add rows for quality issues
        if 'issues' in metrics:
            for issue in metrics['issues']:
                html += f"""
                    <tr>
                        <td>{issue.get('resource_type', 'Unknown')}</td>
                        <td>{issue.get('issue_type', 'Unknown')}</td>
                        <td>{issue.get('count', 0)}</td>
                        <td>{issue.get('description', 'No description')}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_error_dashboard(self, metrics_file: Union[str, Path], 
                                 output_dir: Optional[Union[str, Path]],
                                 error_message: str) -> str:
        """
        Generate an error dashboard when metrics file can't be loaded.
        
        Args:
            metrics_file: Path to metrics file that caused the error
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
        html_path = Path(output_dir) / "quality_dashboard_error.html"
        
        with open(html_path, 'w') as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FHIR Data Quality Dashboard - Error</title>
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
        <h1>Error Loading Quality Metrics</h1>
        <p>An error occurred while loading quality metrics from:</p>
        <div class="code">{metrics_file}</div>
        <p>Error details:</p>
        <div class="code">{error_message}</div>
    </div>
</body>
</html>
""")
        
        return str(html_path) 