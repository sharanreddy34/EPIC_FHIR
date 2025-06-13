"""
Validation Dashboard Utilities.

This module provides utilities for generating dashboards specifically
focused on FHIR validation results, with detailed metrics and visualizations.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from epic_fhir_integration.metrics.validation_metrics import ValidationMetrics
from epic_fhir_integration.validation.validator import FHIRValidator

logger = logging.getLogger(__name__)


class ValidationDashboardGenerator:
    """
    Dashboard utilities for FHIR validation results.

    This class provides tools to generate dashboards specifically for
    FHIR validation results, including profile conformance, validation
    issues, and resource-specific metrics.
    """

    def __init__(
        self,
        output_dir: Union[str, Path],
        title: str = "FHIR Validation Dashboard",
        port: int = 8051,
        debug: bool = False,
    ):
        """
        Initialize the validation dashboard.

        Args:
            output_dir: Directory to save dashboard files
            title: Dashboard title
            port: Port to run the dashboard server on
            debug: Whether to run in debug mode
        """
        self.output_dir = Path(output_dir)
        self.title = title
        self.port = port
        self.debug = debug
        self.validation_data = []
        self.profile_data = {}
        self.app = None

    def load_validation_results(self, results_path: Union[str, Path]) -> None:
        """
        Load validation results from a file.

        Args:
            results_path: Path to the validation results JSON file
        """
        results_path = Path(results_path)
        if not results_path.exists():
            raise FileNotFoundError(f"Validation results not found: {results_path}")

        try:
            with open(results_path, "r") as f:
                data = json.load(f)
            
            # Store validation data
            self.validation_data = data.get("results", [])
            
            # Extract profile information
            if "profiles" in data:
                self.profile_data = data["profiles"]
                
            logger.info(f"Loaded validation results from {results_path}")
            logger.info(f"Loaded {len(self.validation_data)} validation results")
        except Exception as e:
            logger.error(f"Error loading validation results: {e}")
            raise

    def load_batch_validation_results(self, metrics: ValidationMetrics) -> None:
        """
        Load validation results from ValidationMetrics.

        Args:
            metrics: ValidationMetrics instance with validation results
        """
        try:
            # Extract validation results
            self.validation_data = metrics.get_all_validation_results()
            
            # Extract profile information if available
            if hasattr(metrics, "get_profile_statistics"):
                self.profile_data = metrics.get_profile_statistics()
                
            logger.info(f"Loaded {len(self.validation_data)} validation results from metrics")
        except Exception as e:
            logger.error(f"Error loading validation results from metrics: {e}")
            raise

    def _create_validation_summary_card(self) -> dbc.Card:
        """Create a card with overall validation summary."""
        if not self.validation_data:
            return dbc.Card([
                dbc.CardHeader("Validation Summary"),
                dbc.CardBody("No validation data loaded")
            ])
        
        # Calculate summary statistics
        total = len(self.validation_data)
        valid = sum(1 for r in self.validation_data if r.get("valid", False))
        invalid = total - valid
        
        # Calculate error statistics
        errors = sum(1 for r in self.validation_data 
                    for i in r.get("issues", []) if i.get("severity", "") == "error")
        warnings = sum(1 for r in self.validation_data 
                      for i in r.get("issues", []) if i.get("severity", "") == "warning")
        info = sum(1 for r in self.validation_data 
                  for i in r.get("issues", []) if i.get("severity", "") == "information")
        
        # Create summary pie chart
        summary_fig = go.Figure(data=[
            go.Pie(
                labels=["Valid", "Invalid"],
                values=[valid, invalid],
                hole=0.4,
                marker_colors=["#28a745", "#dc3545"]
            )
        ])
        
        summary_fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", y=-0.1)
        )
        
        # Create issues bar chart
        issues_fig = go.Figure(data=[
            go.Bar(
                x=["Errors", "Warnings", "Information"],
                y=[errors, warnings, info],
                marker_color=["#dc3545", "#ffc107", "#17a2b8"]
            )
        ])
        
        issues_fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=30, b=50),
            yaxis_title="Count"
        )
        
        return dbc.Card([
            dbc.CardHeader("Validation Summary"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H4(f"{valid}/{total} Valid Resources", className="text-center"),
                        html.P(f"({round(valid/total*100 if total else 0, 1)}% Valid)", className="text-center"),
                        dcc.Graph(figure=summary_fig, config={"displayModeBar": False})
                    ], width=6),
                    dbc.Col([
                        html.H4("Validation Issues", className="text-center"),
                        html.P(f"Total: {errors + warnings + info}", className="text-center"),
                        dcc.Graph(figure=issues_fig, config={"displayModeBar": False})
                    ], width=6)
                ])
            ])
        ])

    def _create_resource_validation_card(self) -> dbc.Card:
        """Create a card with resource-specific validation results."""
        if not self.validation_data:
            return dbc.Card([
                dbc.CardHeader("Resource Validation"),
                dbc.CardBody("No validation data loaded")
            ])
        
        # Group by resource type
        resource_stats = {}
        for result in self.validation_data:
            resource_type = result.get("resourceType", "Unknown")
            if resource_type not in resource_stats:
                resource_stats[resource_type] = {
                    "total": 0,
                    "valid": 0,
                    "errors": 0,
                    "warnings": 0,
                    "info": 0
                }
            
            stats = resource_stats[resource_type]
            stats["total"] += 1
            if result.get("valid", False):
                stats["valid"] += 1
            
            # Count issues
            for issue in result.get("issues", []):
                severity = issue.get("severity", "").lower()
                if severity == "error":
                    stats["errors"] += 1
                elif severity == "warning":
                    stats["warnings"] += 1
                elif severity in ["information", "info"]:
                    stats["info"] += 1
        
        # Create DataFrame for visualization
        resource_df = pd.DataFrame({
            "Resource Type": [],
            "Metric": [],
            "Value": []
        })
        
        for resource_type, stats in resource_stats.items():
            # Add validity data
            resource_df = pd.concat([
                resource_df,
                pd.DataFrame({
                    "Resource Type": [resource_type, resource_type],
                    "Metric": ["Valid", "Invalid"],
                    "Value": [stats["valid"], stats["total"] - stats["valid"]]
                })
            ])
            
            # Add issue data
            resource_df = pd.concat([
                resource_df,
                pd.DataFrame({
                    "Resource Type": [resource_type] * 3,
                    "Metric": ["Errors", "Warnings", "Information"],
                    "Value": [stats["errors"], stats["warnings"], stats["info"]]
                })
            ])
        
        # Create validity chart
        validity_df = resource_df[resource_df["Metric"].isin(["Valid", "Invalid"])]
        validity_fig = px.bar(
            validity_df,
            x="Resource Type",
            y="Value",
            color="Metric",
            barmode="stack",
            color_discrete_map={
                "Valid": "#28a745",
                "Invalid": "#dc3545"
            }
        )
        
        validity_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=70),
            yaxis_title="Count",
            legend_title_text="Validity"
        )
        
        # Create issues chart
        issues_df = resource_df[resource_df["Metric"].isin(["Errors", "Warnings", "Information"])]
        issues_fig = px.bar(
            issues_df,
            x="Resource Type",
            y="Value",
            color="Metric",
            barmode="group",
            color_discrete_map={
                "Errors": "#dc3545",
                "Warnings": "#ffc107",
                "Information": "#17a2b8"
            }
        )
        
        issues_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=70),
            yaxis_title="Count",
            legend_title_text="Issue Type"
        )
        
        return dbc.Card([
            dbc.CardHeader("Resource Validation"),
            dbc.CardBody([
                dbc.Tabs([
                    dbc.Tab([
                        dcc.Graph(figure=validity_fig, config={"displayModeBar": False})
                    ], label="Validity", className="p-3"),
                    dbc.Tab([
                        dcc.Graph(figure=issues_fig, config={"displayModeBar": False})
                    ], label="Issues", className="p-3")
                ])
            ])
        ])

    def _create_profile_conformance_card(self) -> dbc.Card:
        """Create a card with profile conformance statistics."""
        if not self.profile_data:
            return dbc.Card([
                dbc.CardHeader("Profile Conformance"),
                dbc.CardBody("No profile data available")
            ])
        
        # Extract profile statistics
        profile_stats = []
        for profile_url, stats in self.profile_data.items():
            profile_name = profile_url.split("/")[-1]
            total = stats.get("total", 0)
            conformant = stats.get("conformant", 0)
            
            profile_stats.append({
                "Profile": profile_name,
                "URL": profile_url,
                "Total": total,
                "Conformant": conformant,
                "Non-Conformant": total - conformant,
                "Conformance Rate": (conformant / total * 100) if total > 0 else 0
            })
        
        # Create DataFrame
        profile_df = pd.DataFrame(profile_stats)
        
        # Create conformance rate chart
        rate_fig = px.bar(
            profile_df,
            x="Profile",
            y="Conformance Rate",
            color="Conformance Rate",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            labels={"Conformance Rate": "Conformance Rate (%)"}
        )
        
        rate_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=70),
            yaxis_range=[0, 100]
        )
        
        # Create count chart
        count_df = pd.melt(
            profile_df,
            id_vars=["Profile"],
            value_vars=["Conformant", "Non-Conformant"],
            var_name="Status",
            value_name="Count"
        )
        
        count_fig = px.bar(
            count_df,
            x="Profile",
            y="Count",
            color="Status",
            barmode="stack",
            color_discrete_map={
                "Conformant": "#28a745",
                "Non-Conformant": "#dc3545"
            }
        )
        
        count_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=70)
        )
        
        return dbc.Card([
            dbc.CardHeader("Profile Conformance"),
            dbc.CardBody([
                dbc.Tabs([
                    dbc.Tab([
                        dcc.Graph(figure=rate_fig, config={"displayModeBar": False})
                    ], label="Conformance Rate", className="p-3"),
                    dbc.Tab([
                        dcc.Graph(figure=count_fig, config={"displayModeBar": False})
                    ], label="Resource Counts", className="p-3"),
                    dbc.Tab([
                        html.Div([
                            html.H5("Profile Details"),
                            html.Table([
                                html.Thead(html.Tr([
                                    html.Th("Profile"),
                                    html.Th("URL"),
                                    html.Th("Total"),
                                    html.Th("Conformant"),
                                    html.Th("Rate (%)")
                                ])),
                                html.Tbody([
                                    html.Tr([
                                        html.Td(row["Profile"]),
                                        html.Td(row["URL"], style={"fontSize": "0.8em"}),
                                        html.Td(row["Total"]),
                                        html.Td(row["Conformant"]),
                                        html.Td(f"{row['Conformance Rate']:.1f}%")
                                    ]) for _, row in profile_df.iterrows()
                                ])
                            ], className="table table-striped table-sm")
                        ])
                    ], label="Details", className="p-3")
                ])
            ])
        ])

    def _create_issue_details_card(self) -> dbc.Card:
        """Create a card with detailed validation issues."""
        if not self.validation_data:
            return dbc.Card([
                dbc.CardHeader("Issue Details"),
                dbc.CardBody("No validation data loaded")
            ])
        
        # Extract all issues
        issues = []
        for result in self.validation_data:
            resource_type = result.get("resourceType", "Unknown")
            resource_id = result.get("id", "Unknown")
            
            for issue in result.get("issues", []):
                issues.append({
                    "Resource Type": resource_type,
                    "Resource ID": resource_id,
                    "Severity": issue.get("severity", "Unknown"),
                    "Type": issue.get("type", "Unknown"),
                    "Message": issue.get("message", ""),
                    "Location": ", ".join(issue.get("location", [])) if "location" in issue else ""
                })
        
        # If no issues, create placeholder message
        if not issues:
            return dbc.Card([
                dbc.CardHeader("Issue Details"),
                dbc.CardBody("No validation issues found")
            ])
        
        # Create issue DataFrame
        issue_df = pd.DataFrame(issues)
        
        # Create severity count chart
        severity_counts = issue_df["Severity"].value_counts().reset_index()
        severity_counts.columns = ["Severity", "Count"]
        
        severity_fig = px.pie(
            severity_counts,
            names="Severity",
            values="Count",
            color="Severity",
            color_discrete_map={
                "error": "#dc3545",
                "warning": "#ffc107",
                "information": "#17a2b8",
                "Unknown": "#6c757d"
            },
            hole=0.4
        )
        
        severity_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=50)
        )
        
        # Create type count chart
        type_counts = issue_df["Type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Count"]
        
        type_fig = px.bar(
            type_counts,
            x="Type",
            y="Count",
            color="Count"
        )
        
        type_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=70),
            xaxis_tickangle=-45
        )
        
        # Create resource type issue count
        resource_counts = issue_df["Resource Type"].value_counts().reset_index()
        resource_counts.columns = ["Resource Type", "Count"]
        
        resource_fig = px.bar(
            resource_counts,
            x="Resource Type",
            y="Count",
            color="Count"
        )
        
        resource_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=50)
        )
        
        # Create table of top issues
        issues_by_frequency = issue_df["Message"].value_counts().reset_index()
        issues_by_frequency.columns = ["Message", "Frequency"]
        top_messages = issues_by_frequency.head(10)
        
        issue_table = html.Div([
            html.H5("Most Common Issues"),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Frequency"),
                    html.Th("Message")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(row["Frequency"]),
                        html.Td(row["Message"])
                    ]) for _, row in top_messages.iterrows()
                ])
            ], className="table table-striped table-sm")
        ])
        
        return dbc.Card([
            dbc.CardHeader("Issue Details"),
            dbc.CardBody([
                dbc.Tabs([
                    dbc.Tab([
                        dbc.Row([
                            dbc.Col(dcc.Graph(figure=severity_fig, config={"displayModeBar": False}), width=6),
                            dbc.Col(issue_table, width=6)
                        ])
                    ], label="Summary", className="p-3"),
                    dbc.Tab([
                        dcc.Graph(figure=type_fig, config={"displayModeBar": False})
                    ], label="Issue Types", className="p-3"),
                    dbc.Tab([
                        dcc.Graph(figure=resource_fig, config={"displayModeBar": False})
                    ], label="Resources", className="p-3"),
                    dbc.Tab([
                        html.Div([
                            html.H5("Issue List"),
                            html.Div([
                                html.Table([
                                    html.Thead(html.Tr([
                                        html.Th("Resource"),
                                        html.Th("ID"),
                                        html.Th("Severity"),
                                        html.Th("Type"),
                                        html.Th("Message")
                                    ])),
                                    html.Tbody([
                                        html.Tr([
                                            html.Td(issue["Resource Type"]),
                                            html.Td(issue["Resource ID"][:8] + "..." if len(issue["Resource ID"]) > 8 else issue["Resource ID"]),
                                            html.Td(issue["Severity"], style={"color": "red" if issue["Severity"] == "error" else "orange" if issue["Severity"] == "warning" else "blue"}),
                                            html.Td(issue["Type"]),
                                            html.Td(issue["Message"][:50] + "..." if len(issue["Message"]) > 50 else issue["Message"])
                                        ]) for issue in issues[:100]  # Limit to 100 issues for performance
                                    ])
                                ], className="table table-striped table-sm")
                            ], style={"maxHeight": "500px", "overflow": "auto"})
                        ])
                    ], label="All Issues", className="p-3")
                ])
            ])
        ])

    def create_dashboard(self) -> dash.Dash:
        """
        Create the validation dashboard.

        Returns:
            dash.Dash: The Dash application
        """
        # Initialize Dash app
        app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title=self.title
        )
        
        # Create layout
        app.layout = dbc.Container([
            html.H1(self.title, className="my-4"),
            
            # Summary row
            dbc.Row([
                dbc.Col(self._create_validation_summary_card(), width=12)
            ], className="mb-4"),
            
            # Resource validation row
            dbc.Row([
                dbc.Col(self._create_resource_validation_card(), width=12)
            ], className="mb-4"),
            
            # Profile conformance row
            dbc.Row([
                dbc.Col(self._create_profile_conformance_card(), width=12)
            ], className="mb-4"),
            
            # Issue details row
            dbc.Row([
                dbc.Col(self._create_issue_details_card(), width=12)
            ], className="mb-4"),
            
            # Footer
            html.Footer([
                html.P(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
                html.P("FHIR Validation Dashboard")
            ], className="text-center my-4")
        ], fluid=True)
        
        self.app = app
        return app

    def generate_static_dashboard(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Generate a static HTML dashboard file.

        Args:
            output_path: Optional specific output file path

        Returns:
            Path: Path to the generated HTML file
        """
        if not self.app:
            self.create_dashboard()
            
        if output_path:
            output_file = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"validation_dashboard_{timestamp}.html"
            
        # Ensure directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div class="container-fluid">
        {self.app.index_string}
    </div>
</body>
</html>
"""
        
        # Write to file
        with open(output_file, "w") as f:
            f.write(html_content)
            
        logger.info(f"Static validation dashboard generated at {output_file}")
        return output_file

    def run_dashboard(self) -> None:
        """
        Run the dashboard as a web server.
        """
        if not self.app:
            self.create_dashboard()
            
        logger.info(f"Starting validation dashboard server on port {self.port}")
        self.app.run_server(debug=self.debug, port=self.port)

    @classmethod
    def from_validation_results(
        cls,
        results_path: Union[str, Path],
        output_dir: Union[str, Path],
        title: str = "FHIR Validation Dashboard",
    ) -> "ValidationDashboard":
        """
        Create a dashboard from validation results file.

        Args:
            results_path: Path to the validation results JSON file
            output_dir: Directory to save static dashboard files
            title: Dashboard title

        Returns:
            ValidationDashboard: Dashboard instance
        """
        dashboard = cls(output_dir=output_dir, title=title)
        dashboard.load_validation_results(results_path)
        return dashboard

    @classmethod
    def from_validator(
        cls,
        validator: FHIRValidator,
        resources: List[Dict],
        output_dir: Union[str, Path],
        title: str = "FHIR Validation Dashboard",
    ) -> "ValidationDashboard":
        """
        Create a dashboard by validating resources directly.

        Args:
            validator: FHIRValidator instance
            resources: List of FHIR resources to validate
            output_dir: Directory to save static dashboard files
            title: Dashboard title

        Returns:
            ValidationDashboard: Dashboard instance
        """
        dashboard = cls(output_dir=output_dir, title=title)
        
        # Validate resources
        results = []
        for resource in resources:
            result = validator.validate(resource)
            results.append(result.to_dict())
            
        # Store results
        dashboard.validation_data = results
        
        # Extract profile information if available
        profiles = {}
        for result in results:
            profile_urls = result.get("profiles", [])
            is_valid = result.get("valid", False)
            
            for url in profile_urls:
                if url not in profiles:
                    profiles[url] = {"total": 0, "conformant": 0}
                
                profiles[url]["total"] += 1
                if is_valid:
                    profiles[url]["conformant"] += 1
        
        dashboard.profile_data = profiles
        
        return dashboard

# Backwards compatibility class
class ValidationDashboard:
    """Backwards compatibility wrapper for ValidationDashboardGenerator.
    
    This provides the original interface but sets default values for required parameters.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with default output directory if none provided."""
        # Set default output directory to logs if not provided
        output_dir = kwargs.get('output_dir', 'logs')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Store other arguments
        self.args = args
        self.kwargs = kwargs
        
        # Create placeholder for the dashboard
        self._dashboard = None
        logger.info("ValidationDashboard initialized with compatibility wrapper")
    
    def __getattr__(self, name):
        """Forward attribute access to the underlying dashboard."""
        # Lazy initialize the dashboard when first accessed
        if self._dashboard is None:
            self._dashboard = ValidationDashboardGenerator(
                output_dir=self.kwargs.get('output_dir', 'logs'),
                title=self.kwargs.get('title', 'FHIR Validation Dashboard'),
                port=self.kwargs.get('port', 8051),
                debug=self.kwargs.get('debug', False)
            )
        
        # Forward the attribute access
        return getattr(self._dashboard, name)

    def generate_dashboard(self, validation_file, output_dir=None, static_mode=True):
        """Compatibility method for the original interface used in the test script.
        
        Args:
            validation_file: Path to validation results file
            output_dir: Output directory
            static_mode: Whether to generate a static dashboard
            
        Returns:
            Path to generated dashboard file
        """
        if output_dir:
            self.kwargs['output_dir'] = output_dir
        
        # Initialize the dashboard
        if self._dashboard is None:
            self._dashboard = ValidationDashboardGenerator(
                output_dir=self.kwargs.get('output_dir', 'logs'),
                title=self.kwargs.get('title', 'FHIR Validation Dashboard'),
                port=self.kwargs.get('port', 8051),
                debug=self.kwargs.get('debug', False)
            )
        
        # Load validation results
        try:
            self._dashboard.load_validation_results(validation_file)
        except Exception as e:
            logger.warning(f"Error loading validation results: {e}, using empty data")
        
        # Create dashboard app
        self._dashboard.create_dashboard()
        
        # Generate static dashboard if requested
        if static_mode:
            return self._dashboard.generate_static_dashboard()
        else:
            # For non-static, return a placeholder path
            placeholder_path = Path(output_dir) / "validation_dashboard_placeholder.html"
            logger.info(f"Static mode disabled, dashboard would be served at http://localhost:{self._dashboard.port}/")
            return placeholder_path 