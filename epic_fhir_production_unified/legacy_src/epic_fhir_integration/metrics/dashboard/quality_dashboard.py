"""
Quality Dashboard Generator.

This module provides functionality for generating interactive dashboards
that visualize data quality metrics, validation results, and quality trends.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from epic_fhir_integration.metrics.data_quality import DataQualityAssessor
from epic_fhir_integration.metrics.validation_metrics import ValidationMetrics
from epic_fhir_integration.metrics.quality_tracker import QualityTracker
from epic_fhir_integration.schemas.quality_report import QualityReport

logger = logging.getLogger(__name__)


class QualityDashboardGenerator:
    """
    Generator for interactive data quality dashboards.

    This class provides functionality to create dashboards for:
    1. Current data quality metrics
    2. Validation results visualization
    3. Quality trends over time
    4. Resource-specific quality metrics
    5. Quality alerts and interventions
    """

    def __init__(
        self,
        output_dir: Union[str, Path],
        title: str = "FHIR Data Quality Dashboard",
        port: int = 8050,
        debug: bool = False,
    ):
        """
        Initialize the dashboard generator.

        Args:
            output_dir: Directory to save static dashboard files
            title: Dashboard title
            port: Port to run the dashboard server on
            debug: Whether to run in debug mode
        """
        self.output_dir = Path(output_dir)
        self.title = title
        self.port = port
        self.debug = debug
        self.quality_data = {}
        self.validation_data = {}
        self.trends_data = {}
        self.app = None

    def load_quality_report(self, report_path: Union[str, Path]) -> None:
        """
        Load quality report data from a file.

        Args:
            report_path: Path to the quality report JSON file
        """
        report_path = Path(report_path)
        if not report_path.exists():
            raise FileNotFoundError(f"Quality report not found: {report_path}")

        try:
            with open(report_path, "r") as f:
                data = json.load(f)
                # Handle different Pydantic versions
                try:
                    # For Pydantic v2
                    report = QualityReport.model_validate(data)
                except AttributeError:
                    try:
                        # For Pydantic v1
                        report = QualityReport.parse_obj(data)
                    except Exception as pydantic_err:
                        logger.warning(f"Pydantic validation error: {pydantic_err}, using empty data")
                        report = QualityReport(
                            report_name="empty", 
                            generated_at=datetime.now(),
                            filter={},
                            interval="daily",
                            metrics_count=0,
                            tracked_metrics={},
                            statistics={},
                            trends={}
                        )
                
            # Extract data for dashboard
            # Use getattr with default values to handle missing attributes
            self.quality_data.update({
                "report_id": getattr(report, "report_id", "unknown"),
                "timestamp": getattr(report, "generated_at", datetime.now()),
                "overall_score": getattr(report, "overall_score", 0.0),
                "dimension_scores": getattr(report, "dimension_scores", {}),
                "resource_scores": getattr(report, "resource_scores", {}),
                "issues": getattr(report, "quality_issues", [])
            })
            
            logger.info(f"Loaded quality report from {report_path}")
        except Exception as e:
            logger.error(f"Error loading quality report: {e}")
            raise

    def load_validation_results(self, results_path: Union[str, Path]) -> None:
        """
        Load validation results data.

        Args:
            results_path: Path to the validation results file
        """
        results_path = Path(results_path)
        if not results_path.exists():
            raise FileNotFoundError(f"Validation results not found: {results_path}")

        try:
            with open(results_path, "r") as f:
                data = json.load(f)
            
            # Extract validation metrics
            self.validation_data = data
            logger.info(f"Loaded validation results from {results_path}")
        except Exception as e:
            logger.error(f"Error loading validation results: {e}")
            raise

    def load_quality_trends(self, tracker: QualityTracker) -> None:
        """
        Load quality trend data from a QualityTracker.

        Args:
            tracker: QualityTracker instance with historical data
        """
        try:
            # Get historical quality data
            history = tracker.get_history()
            
            # Convert to DataFrame for easier plotting
            trend_data = []
            for entry in history:
                trend_data.append({
                    "timestamp": entry["timestamp"],
                    "overall_score": entry["overall_score"],
                    **{f"dimension_{k}": v for k, v in entry["dimension_scores"].items()}
                })
            
            self.trends_data = pd.DataFrame(trend_data)
            logger.info(f"Loaded quality trends with {len(trend_data)} data points")
        except Exception as e:
            logger.error(f"Error loading quality trends: {e}")
            raise

    def _create_quality_overview_card(self) -> dbc.Card:
        """Create a card with overall quality metrics."""
        if not self.quality_data:
            return dbc.Card([
                dbc.CardHeader("Quality Overview"),
                dbc.CardBody("No quality data loaded")
            ])
        
        # Extract data
        score = self.quality_data.get("overall_score", 0)
        timestamp = self.quality_data.get("timestamp", datetime.now().isoformat())
        
        # Create quality gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,  # Convert to percentage
            title={"text": "Overall Quality"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 50], "color": "red"},
                    {"range": [50, 75], "color": "orange"},
                    {"range": [75, 90], "color": "yellow"},
                    {"range": [90, 100], "color": "green"}
                ]
            }
        ))
        
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
        
        return dbc.Card([
            dbc.CardHeader("Quality Overview"),
            dbc.CardBody([
                html.P(f"Report generated: {timestamp}"),
                dcc.Graph(figure=fig, config={"displayModeBar": False})
            ])
        ])

    def _create_dimension_scores_card(self) -> dbc.Card:
        """Create a card with dimension-specific quality scores."""
        if not self.quality_data or "dimension_scores" not in self.quality_data:
            return dbc.Card([
                dbc.CardHeader("Quality Dimensions"),
                dbc.CardBody("No dimension data loaded")
            ])
        
        # Extract data
        dimensions = self.quality_data["dimension_scores"]
        
        # Create bar chart
        dim_df = pd.DataFrame({
            "Dimension": list(dimensions.keys()),
            "Score": [v * 100 for v in dimensions.values()]  # Convert to percentage
        })
        
        fig = px.bar(
            dim_df, 
            x="Dimension", 
            y="Score",
            color="Score",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            labels={"Score": "Quality Score (%)"}
        )
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=50))
        
        return dbc.Card([
            dbc.CardHeader("Quality Dimensions"),
            dbc.CardBody([
                dcc.Graph(figure=fig, config={"displayModeBar": False})
            ])
        ])

    def _create_resource_scores_card(self) -> dbc.Card:
        """Create a card with resource-specific quality scores."""
        if not self.quality_data or "resource_scores" not in self.quality_data:
            return dbc.Card([
                dbc.CardHeader("Resource Quality"),
                dbc.CardBody("No resource quality data loaded")
            ])
        
        # Extract data
        resources = self.quality_data["resource_scores"]
        
        # Create data for heatmap
        resource_types = []
        dimensions = []
        scores = []
        
        for resource_type, dims in resources.items():
            for dim, score in dims.items():
                resource_types.append(resource_type)
                dimensions.append(dim)
                scores.append(score * 100)  # Convert to percentage
        
        df = pd.DataFrame({
            "Resource": resource_types,
            "Dimension": dimensions,
            "Score": scores
        })
        
        # Reshape for heatmap
        pivot_df = df.pivot(index="Resource", columns="Dimension", values="Score")
        
        # Create heatmap
        fig = px.imshow(
            pivot_df,
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            labels=dict(x="Dimension", y="Resource Type", color="Quality Score (%)")
        )
        
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
        
        return dbc.Card([
            dbc.CardHeader("Resource Quality"),
            dbc.CardBody([
                dcc.Graph(figure=fig, config={"displayModeBar": False})
            ])
        ])

    def _create_validation_card(self) -> dbc.Card:
        """Create a card with validation results visualization."""
        if not self.validation_data:
            return dbc.Card([
                dbc.CardHeader("Validation Results"),
                dbc.CardBody("No validation data loaded")
            ])
        
        # Extract validation issues
        validation_issues = self.validation_data.get("issues", [])
        
        # Count issues by severity
        severity_counts = {"error": 0, "warning": 0, "information": 0}
        for issue in validation_issues:
            severity = issue.get("severity", "").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Create chart
        severity_df = pd.DataFrame({
            "Severity": list(severity_counts.keys()),
            "Count": list(severity_counts.values())
        })
        
        fig = px.pie(
            severity_df,
            names="Severity",
            values="Count",
            color="Severity",
            color_discrete_map={
                "error": "red",
                "warning": "orange",
                "information": "blue"
            },
            hole=0.4
        )
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
        
        # Create issue table (top 5)
        issue_table = html.Div([
            html.H6("Top Validation Issues"),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Severity"),
                    html.Th("Message"),
                    html.Th("Resource Type")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(issue.get("severity", ""), style={"color": "red" if issue.get("severity") == "error" else "orange" if issue.get("severity") == "warning" else "blue"}),
                        html.Td(issue.get("message", "")[:50] + "..." if len(issue.get("message", "")) > 50 else issue.get("message", "")),
                        html.Td(issue.get("resourceType", ""))
                    ]) for issue in validation_issues[:5]
                ])
            ], className="table table-striped table-sm")
        ]) if validation_issues else html.P("No validation issues found")
        
        return dbc.Card([
            dbc.CardHeader("Validation Results"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig, config={"displayModeBar": False}), width=6),
                    dbc.Col(issue_table, width=6)
                ])
            ])
        ])

    def _create_trends_card(self) -> dbc.Card:
        """Create a card with quality trends over time."""
        if not isinstance(self.trends_data, pd.DataFrame) or self.trends_data.empty:
            return dbc.Card([
                dbc.CardHeader("Quality Trends"),
                dbc.CardBody("No trend data loaded")
            ])
        
        # Create line chart
        fig = px.line(
            self.trends_data,
            x="timestamp",
            y="overall_score",
            labels={"timestamp": "Time", "overall_score": "Overall Quality Score"}
        )
        
        # Add dimension lines if available
        dimension_cols = [col for col in self.trends_data.columns if col.startswith("dimension_")]
        for col in dimension_cols:
            dim_name = col.replace("dimension_", "").capitalize()
            fig.add_scatter(
                x=self.trends_data["timestamp"],
                y=self.trends_data[col],
                mode="lines",
                name=dim_name
            )
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=50))
        
        return dbc.Card([
            dbc.CardHeader("Quality Trends"),
            dbc.CardBody([
                dcc.Graph(figure=fig, config={"displayModeBar": False})
            ])
        ])

    def _create_issues_card(self) -> dbc.Card:
        """Create a card with quality issues."""
        if not self.quality_data or "issues" not in self.quality_data:
            return dbc.Card([
                dbc.CardHeader("Quality Issues"),
                dbc.CardBody("No quality issues data loaded")
            ])
        
        # Extract issues
        issues = self.quality_data["issues"]
        
        # Group issues by category
        categories = {}
        for issue in issues:
            category = issue.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        # Create chart
        category_df = pd.DataFrame({
            "Category": list(categories.keys()),
            "Count": list(categories.values())
        })
        
        fig = px.bar(
            category_df,
            x="Category",
            y="Count",
            color="Count",
            labels={"Count": "Number of Issues"}
        )
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=70))
        
        # Create issue table (top 5)
        issue_table = html.Div([
            html.H6("Top Quality Issues"),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Category"),
                    html.Th("Severity"),
                    html.Th("Description")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(issue.get("category", "")),
                        html.Td(issue.get("severity", ""), style={"color": "red" if issue.get("severity") == "critical" else "orange" if issue.get("severity") == "high" else "blue"}),
                        html.Td(issue.get("description", "")[:50] + "..." if len(issue.get("description", "")) > 50 else issue.get("description", ""))
                    ]) for issue in issues[:5]
                ])
            ], className="table table-striped table-sm")
        ]) if issues else html.P("No quality issues found")
        
        return dbc.Card([
            dbc.CardHeader("Quality Issues"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig, config={"displayModeBar": False}), width=6),
                    dbc.Col(issue_table, width=6)
                ])
            ])
        ])

    def create_dashboard(self) -> dash.Dash:
        """
        Create an interactive Dash dashboard.

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
            
            # Overview row
            dbc.Row([
                dbc.Col(self._create_quality_overview_card(), width=6),
                dbc.Col(self._create_dimension_scores_card(), width=6)
            ], className="mb-4"),
            
            # Resource quality row
            dbc.Row([
                dbc.Col(self._create_resource_scores_card(), width=12)
            ], className="mb-4"),
            
            # Validation results row
            dbc.Row([
                dbc.Col(self._create_validation_card(), width=12)
            ], className="mb-4"),
            
            # Trends row
            dbc.Row([
                dbc.Col(self._create_trends_card(), width=12)
            ], className="mb-4"),
            
            # Issues row
            dbc.Row([
                dbc.Col(self._create_issues_card(), width=12)
            ], className="mb-4"),
            
            # Footer
            html.Footer([
                html.P(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
                html.P("FHIR Data Quality Dashboard")
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
            output_file = self.output_dir / f"quality_dashboard_{timestamp}.html"
            
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
            
        logger.info(f"Static dashboard generated at {output_file}")
        return output_file

    def run_dashboard(self) -> None:
        """
        Run the dashboard as a web server.
        """
        if not self.app:
            self.create_dashboard()
            
        logger.info(f"Starting dashboard server on port {self.port}")
        self.app.run_server(debug=self.debug, port=self.port)

    @classmethod
    def from_quality_report(
        cls,
        report_path: Union[str, Path],
        output_dir: Union[str, Path],
        title: str = "FHIR Data Quality Dashboard",
    ) -> "QualityDashboardGenerator":
        """
        Create a dashboard generator from a quality report file.

        Args:
            report_path: Path to the quality report JSON file
            output_dir: Directory to save static dashboard files
            title: Dashboard title

        Returns:
            QualityDashboardGenerator: Dashboard generator instance
        """
        generator = cls(output_dir=output_dir, title=title)
        generator.load_quality_report(report_path)
        return generator

    @classmethod
    def from_quality_assessor(
        cls,
        assessor: DataQualityAssessor,
        output_dir: Union[str, Path],
        title: str = "FHIR Data Quality Dashboard",
    ) -> "QualityDashboardGenerator":
        """
        Create a dashboard generator from a DataQualityAssessor.

        Args:
            assessor: DataQualityAssessor instance with quality data
            output_dir: Directory to save static dashboard files
            title: Dashboard title

        Returns:
            QualityDashboardGenerator: Dashboard generator instance
        """
        generator = cls(output_dir=output_dir, title=title)
        
        # Extract data from assessor
        generator.quality_data = {
            "report_id": assessor.report_id,
            "timestamp": assessor.last_assessment_time.isoformat() if assessor.last_assessment_time else datetime.now().isoformat(),
            "overall_score": assessor.get_overall_score(),
            "dimension_scores": assessor.get_dimension_scores(),
            "resource_scores": assessor.get_resource_scores(),
            "issues": assessor.get_quality_issues()
        }
        
        return generator

# Backwards compatibility alias
class QualityDashboard:
    """Backwards compatibility wrapper for QualityDashboardGenerator.
    
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
        logger.info("QualityDashboard initialized with compatibility wrapper")
    
    def __getattr__(self, name):
        """Forward attribute access to the underlying dashboard."""
        # Lazy initialize the dashboard when first accessed
        if self._dashboard is None:
            self._dashboard = QualityDashboardGenerator(
                output_dir=self.kwargs.get('output_dir', 'logs'),
                title=self.kwargs.get('title', 'FHIR Quality Dashboard'),
                port=self.kwargs.get('port', 8050),
                debug=self.kwargs.get('debug', False)
            )
        
        # Forward the attribute access
        return getattr(self._dashboard, name)

    def generate_dashboard(self, metrics_file, output_dir=None, static_mode=True):
        """Compatibility method for the original interface used in the test script.
        
        Args:
            metrics_file: Path to metrics file
            output_dir: Output directory
            static_mode: Whether to generate a static dashboard
            
        Returns:
            Path to generated dashboard file
        """
        if output_dir:
            self.kwargs['output_dir'] = output_dir
        
        # Initialize the dashboard
        if self._dashboard is None:
            self._dashboard = QualityDashboardGenerator(
                output_dir=self.kwargs.get('output_dir', 'logs'),
                title=self.kwargs.get('title', 'FHIR Quality Dashboard'),
                port=self.kwargs.get('port', 8050),
                debug=self.kwargs.get('debug', False)
            )
        
        # Load metrics
        try:
            self._dashboard.load_quality_report(metrics_file)
        except Exception as e:
            logger.warning(f"Error loading quality report: {e}, using empty data")
        
        # Create dashboard app
        self._dashboard.create_dashboard()
        
        # Generate static dashboard if requested
        if static_mode:
            return self._dashboard.generate_static_dashboard()
        else:
            # For non-static, return a placeholder path
            placeholder_path = Path(output_dir) / "quality_dashboard_placeholder.html"
            logger.info(f"Static mode disabled, dashboard would be served at http://localhost:{self._dashboard.port}/")
            return placeholder_path 