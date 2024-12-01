"""
Quality Dashboard Module.

This module provides tools for generating interactive visualizations of
data quality metrics to help users monitor and improve data quality.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from epic_fhir_integration.metrics.data_quality import QualityReport

logger = logging.getLogger(__name__)


class QualityDashboard:
    """Dashboard for visualizing data quality metrics.
    
    This class provides methods for generating visualizations of data quality
    metrics and exporting them as HTML or image files.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the quality dashboard.
        
        Args:
            output_dir: Directory to save dashboard outputs.
                If not specified, a default directory is used.
        """
        self.output_dir = Path(output_dir) if output_dir else Path("quality_dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure default plot style
        plt.style.use("seaborn-v0_8-whitegrid")
        self.figsize = (10, 6)
        self.dpi = 100
        
    def visualize_report(
        self,
        report: QualityReport,
        save_format: str = "png",
    ) -> Dict[str, str]:
        """Visualize a quality report.
        
        Args:
            report: Quality report to visualize.
            save_format: Format to save visualizations in ("png", "svg", "pdf").
            
        Returns:
            Dictionary mapping visualization names to file paths.
        """
        # Create a timestamped directory for this report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"{report.resource_type}_{timestamp}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the report as JSON
        report_path = report_dir / "report.json"
        with open(report_path, "w") as f:
            f.write(report.to_json())
            
        # Generate visualizations
        visualizations = {}
        
        # Overall quality score
        overall_score_path = self._visualize_overall_score(report, report_dir, save_format)
        visualizations["overall_score"] = str(overall_score_path)
        
        # Dimension scores
        dimension_scores_path = self._visualize_dimension_scores(report, report_dir, save_format)
        visualizations["dimension_scores"] = str(dimension_scores_path)
        
        # Resource-specific visualizations
        if report.resource_type == "Patient":
            patient_viz_path = self._visualize_patient_quality(report, report_dir, save_format)
            visualizations["patient_quality"] = str(patient_viz_path)
        elif report.resource_type == "Observation":
            observation_viz_path = self._visualize_observation_quality(report, report_dir, save_format)
            visualizations["observation_quality"] = str(observation_viz_path)
            
        # Generate an HTML index
        index_path = self._generate_html_index(report, visualizations, report_dir)
        visualizations["index"] = str(index_path)
        
        logger.info(f"Generated quality dashboard in {report_dir}")
        return visualizations
    
    def _visualize_overall_score(
        self,
        report: QualityReport,
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize the overall quality score.
        
        Args:
            report: Quality report to visualize.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Create a gauge chart for the overall score
        score = report.overall_score
        gauge_colors = [(0.7, 0.2, 0.2), (0.8, 0.7, 0.2), (0.2, 0.7, 0.2)]
        
        # Create a simple gauge chart
        ax.pie(
            [0.33, 0.33, 0.33],
            colors=gauge_colors,
            startangle=90,
            counterclock=False,
            radius=1.0,
            wedgeprops={"width": 0.3, "edgecolor": "w", "linewidth": 2},
        )
        
        # Add arrow to indicate score
        arrow_angle = 90 - 180 * score
        arrow_length = 0.8
        arrow_x = arrow_length * np.cos(np.radians(arrow_angle))
        arrow_y = arrow_length * np.sin(np.radians(arrow_angle))
        ax.arrow(
            0, 0, arrow_x, arrow_y,
            head_width=0.05, head_length=0.1,
            fc="k", ec="k", linewidth=2,
        )
        
        # Add score text
        ax.text(
            0, 0, f"{score:.2f}",
            ha="center", va="center",
            fontsize=24, fontweight="bold",
        )
        
        # Add title
        ax.set_title(
            f"Overall Quality Score: {report.resource_type}",
            fontsize=16, fontweight="bold", pad=20,
        )
        
        # Add labels
        ax.text(-1.2, -0.2, "Poor", fontsize=12, ha="center")
        ax.text(0, -1.2, "Average", fontsize=12, ha="center")
        ax.text(1.2, -0.2, "Good", fontsize=12, ha="center")
        
        # Set equal aspect ratio
        ax.set_aspect("equal")
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        
        # Remove axes
        ax.axis("off")
        
        # Save the figure
        output_path = output_dir / f"overall_score.{save_format}"
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        
        return output_path
    
    def _visualize_dimension_scores(
        self,
        report: QualityReport,
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize dimension scores.
        
        Args:
            report: Quality report to visualize.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Extract dimension scores
        dimensions = [dim.name.capitalize() for dim in report.dimensions]
        scores = [dim.score for dim in report.dimensions]
        
        # Sort by score
        sorted_indices = np.argsort(scores)
        dimensions = [dimensions[i] for i in sorted_indices]
        scores = [scores[i] for i in sorted_indices]
        
        # Create color map based on scores
        colors = [
            (0.7, 0.2, 0.2) if score < 0.6 else
            (0.8, 0.7, 0.2) if score < 0.8 else
            (0.2, 0.7, 0.2)
            for score in scores
        ]
        
        # Create horizontal bar chart
        bars = ax.barh(dimensions, scores, color=colors)
        
        # Add score labels
        for bar, score in zip(bars, scores):
            ax.text(
                bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{score:.2f}",
                va="center", fontsize=10,
            )
        
        # Add title and labels
        ax.set_title(
            f"Quality Dimension Scores: {report.resource_type}",
            fontsize=16, fontweight="bold", pad=20,
        )
        ax.set_xlabel("Score (0.0 - 1.0)")
        
        # Add gridlines
        ax.grid(True, axis="x", linestyle="--", alpha=0.7)
        
        # Set x-axis limits
        ax.set_xlim(0, 1.05)
        
        # Save the figure
        output_path = output_dir / f"dimension_scores.{save_format}"
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        
        return output_path
    
    def _visualize_patient_quality(
        self,
        report: QualityReport,
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize Patient resource quality.
        
        Args:
            report: Quality report to visualize.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        # Find completeness dimension
        completeness_dim = next(
            (dim for dim in report.dimensions if dim.name == "completeness"),
            None,
        )
        
        if not completeness_dim:
            logger.warning("Completeness dimension not found in report")
            return None
            
        # Extract missing fields
        missing_fields = completeness_dim.details.get("missing_fields", {})
        
        if not missing_fields:
            logger.info("No missing fields to visualize")
            return None
            
        # Create a figure
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Extract field names and counts
        fields = list(missing_fields.keys())
        counts = list(missing_fields.values())
        
        # Sort by count
        sorted_indices = np.argsort(counts)
        fields = [fields[i] for i in sorted_indices]
        counts = [counts[i] for i in sorted_indices]
        
        # Calculate percentage of resources
        total_resources = report.resource_count
        percentages = [count / total_resources * 100 for count in counts]
        
        # Create horizontal bar chart
        bars = ax.barh(fields, percentages)
        
        # Add percentage labels
        for bar, pct in zip(bars, percentages):
            ax.text(
                bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}%",
                va="center", fontsize=10,
            )
        
        # Add title and labels
        ax.set_title(
            f"Missing Fields in Patient Resources",
            fontsize=16, fontweight="bold", pad=20,
        )
        ax.set_xlabel("Percentage of Resources (%)")
        
        # Add gridlines
        ax.grid(True, axis="x", linestyle="--", alpha=0.7)
        
        # Set x-axis limits
        ax.set_xlim(0, max(percentages) * 1.1)
        
        # Save the figure
        output_path = output_dir / f"patient_missing_fields.{save_format}"
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        
        return output_path
    
    def _visualize_observation_quality(
        self,
        report: QualityReport,
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize Observation resource quality.
        
        Args:
            report: Quality report to visualize.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        # Similar to patient quality, but for Observations
        # This is a simplified placeholder implementation
        return self._visualize_patient_quality(report, output_dir, save_format)
    
    def _generate_html_index(
        self,
        report: QualityReport,
        visualizations: Dict[str, str],
        output_dir: Path,
    ) -> Path:
        """Generate an HTML index for the dashboard.
        
        Args:
            report: Quality report to visualize.
            visualizations: Dictionary mapping visualization names to file paths.
            output_dir: Directory to save the index.
            
        Returns:
            Path to the saved index.
        """
        # Create a simple HTML index
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quality Dashboard: {report.resource_type}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333366; }}
        .viz-container {{ margin: 20px 0; }}
        .viz-title {{ font-weight: bold; margin-bottom: 10px; }}
        .score-card {{ 
            display: inline-block;
            padding: 15px;
            margin: 10px;
            border-radius: 5px;
            text-align: center;
            color: white;
            width: 200px;
        }}
        .good {{ background-color: #4CAF50; }}
        .average {{ background-color: #FFC107; }}
        .poor {{ background-color: #F44336; }}
    </style>
</head>
<body>
    <h1>Quality Dashboard: {report.resource_type}</h1>
    <p>Report generated on: {report.timestamp}</p>
    <p>Total resources: {report.resource_count}</p>
    
    <div class="score-cards">
"""
        
        # Add score cards
        overall_class = "good" if report.overall_score >= 0.8 else "average" if report.overall_score >= 0.6 else "poor"
        html_content += f"""
        <div class="score-card {overall_class}">
            <h3>Overall Score</h3>
            <h2>{report.overall_score:.2f}</h2>
        </div>
"""
        
        # Add dimension scores
        for dim in report.dimensions:
            dim_class = "good" if dim.score >= 0.8 else "average" if dim.score >= 0.6 else "poor"
            html_content += f"""
        <div class="score-card {dim_class}">
            <h3>{dim.name.capitalize()}</h3>
            <h2>{dim.score:.2f}</h2>
        </div>
"""
        
        html_content += """
    </div>
    
    <h2>Visualizations</h2>
"""
        
        # Add visualization images
        for name, path in visualizations.items():
            if name != "index":
                # Convert path to relative path
                rel_path = os.path.basename(path)
                html_content += f"""
    <div class="viz-container">
        <div class="viz-title">{name.replace('_', ' ').title()}</div>
        <img src="{rel_path}" alt="{name}" style="max-width: 100%;">
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Save the HTML index
        output_path = output_dir / "index.html"
        with open(output_path, "w") as f:
            f.write(html_content)
            
        return output_path
    
    def load_reports(self, reports_dir: str) -> List[QualityReport]:
        """Load quality reports from a directory.
        
        Args:
            reports_dir: Directory containing quality reports.
            
        Returns:
            List of quality reports.
        """
        reports = []
        reports_dir = Path(reports_dir)
        
        # Find all JSON files in the directory
        for json_file in reports_dir.glob("**/*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    
                # Create quality report from JSON
                report = self._report_from_dict(data)
                reports.append(report)
                
            except Exception as e:
                logger.error(f"Error loading report from {json_file}: {e}")
                
        return reports
    
    def _report_from_dict(self, data: Dict[str, Any]) -> QualityReport:
        """Create a quality report from a dictionary.
        
        Args:
            data: Dictionary representation of a quality report.
            
        Returns:
            Quality report.
        """
        from epic_fhir_integration.metrics.data_quality import QualityDimension
        
        # Create dimensions
        dimensions = []
        for dim_data in data.get("dimensions", []):
            dimension = QualityDimension(
                name=dim_data.get("name", ""),
                score=dim_data.get("score", 0.0),
                details=dim_data.get("details", {}),
            )
            dimensions.append(dimension)
            
        # Create report
        report = QualityReport(
            resource_type=data.get("resource_type", "unknown"),
            resource_count=data.get("resource_count", 0),
            overall_score=data.get("overall_score", 0.0),
            dimensions=dimensions,
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        return report
    
    def generate_trend_dashboard(
        self,
        reports: List[QualityReport],
        save_format: str = "png",
    ) -> Dict[str, str]:
        """Generate a dashboard showing quality trends over time.
        
        Args:
            reports: List of quality reports.
            save_format: Format to save visualizations in.
            
        Returns:
            Dictionary mapping visualization names to file paths.
        """
        if not reports:
            logger.warning("No reports to generate trend dashboard")
            return {}
            
        # Create a timestamped directory for this dashboard
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dashboard_dir = self.output_dir / f"trend_dashboard_{timestamp}"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate visualizations
        visualizations = {}
        
        # Overall score trend
        overall_trend_path = self._visualize_overall_trend(reports, dashboard_dir, save_format)
        visualizations["overall_trend"] = str(overall_trend_path)
        
        # Dimension score trends
        dimension_trend_path = self._visualize_dimension_trends(reports, dashboard_dir, save_format)
        visualizations["dimension_trends"] = str(dimension_trend_path)
        
        # Generate an HTML index
        index_path = self._generate_trend_html_index(reports, visualizations, dashboard_dir)
        visualizations["index"] = str(index_path)
        
        logger.info(f"Generated trend dashboard in {dashboard_dir}")
        return visualizations
    
    def _visualize_overall_trend(
        self,
        reports: List[QualityReport],
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize overall quality score trend.
        
        Args:
            reports: List of quality reports.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Extract timestamps and overall scores
        timestamps = []
        scores = []
        
        for report in reports:
            try:
                timestamp = datetime.fromisoformat(report.timestamp.replace("Z", "+00:00"))
                timestamps.append(timestamp)
                scores.append(report.overall_score)
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing timestamp: {e}")
                
        # Sort by timestamp
        sorted_indices = np.argsort(timestamps)
        timestamps = [timestamps[i] for i in sorted_indices]
        scores = [scores[i] for i in sorted_indices]
        
        # Create line chart
        ax.plot(timestamps, scores, marker="o", linestyle="-", linewidth=2)
        
        # Add title and labels
        ax.set_title(
            f"Overall Quality Score Trend: {reports[0].resource_type}",
            fontsize=16, fontweight="bold", pad=20,
        )
        ax.set_xlabel("Date")
        ax.set_ylabel("Overall Score")
        
        # Add gridlines
        ax.grid(True, linestyle="--", alpha=0.7)
        
        # Set y-axis limits
        ax.set_ylim(0, 1.05)
        
        # Format x-axis ticks
        fig.autofmt_xdate()
        
        # Save the figure
        output_path = output_dir / f"overall_trend.{save_format}"
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        
        return output_path
    
    def _visualize_dimension_trends(
        self,
        reports: List[QualityReport],
        output_dir: Path,
        save_format: str,
    ) -> Path:
        """Visualize dimension score trends.
        
        Args:
            reports: List of quality reports.
            output_dir: Directory to save visualization.
            save_format: Format to save visualization in.
            
        Returns:
            Path to the saved visualization.
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Extract timestamps and dimension scores
        timestamps = []
        dimension_scores = {}
        
        for report in reports:
            try:
                timestamp = datetime.fromisoformat(report.timestamp.replace("Z", "+00:00"))
                timestamps.append(timestamp)
                
                # Extract dimension scores
                for dim in report.dimensions:
                    if dim.name not in dimension_scores:
                        dimension_scores[dim.name] = []
                    dimension_scores[dim.name].append(dim.score)
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing timestamp: {e}")
                
        # Sort by timestamp
        sorted_indices = np.argsort(timestamps)
        timestamps = [timestamps[i] for i in sorted_indices]
        
        for dim_name, scores in dimension_scores.items():
            # Ensure scores match timestamps
            if len(scores) == len(timestamps):
                sorted_scores = [scores[i] for i in sorted_indices]
                
                # Create line chart
                ax.plot(
                    timestamps, sorted_scores,
                    marker="o", linestyle="-", linewidth=2,
                    label=dim_name.capitalize(),
                )
        
        # Add title and labels
        ax.set_title(
            f"Quality Dimension Score Trends: {reports[0].resource_type}",
            fontsize=16, fontweight="bold", pad=20,
        )
        ax.set_xlabel("Date")
        ax.set_ylabel("Score")
        
        # Add legend
        ax.legend()
        
        # Add gridlines
        ax.grid(True, linestyle="--", alpha=0.7)
        
        # Set y-axis limits
        ax.set_ylim(0, 1.05)
        
        # Format x-axis ticks
        fig.autofmt_xdate()
        
        # Save the figure
        output_path = output_dir / f"dimension_trends.{save_format}"
        plt.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        
        return output_path
    
    def _generate_trend_html_index(
        self,
        reports: List[QualityReport],
        visualizations: Dict[str, str],
        output_dir: Path,
    ) -> Path:
        """Generate an HTML index for the trend dashboard.
        
        Args:
            reports: List of quality reports.
            visualizations: Dictionary mapping visualization names to file paths.
            output_dir: Directory to save the index.
            
        Returns:
            Path to the saved index.
        """
        # Create a simple HTML index
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quality Trend Dashboard: {reports[0].resource_type}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333366; }}
        .viz-container {{ margin: 20px 0; }}
        .viz-title {{ font-weight: bold; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <h1>Quality Trend Dashboard: {reports[0].resource_type}</h1>
    <p>Dashboard generated on: {datetime.now().isoformat()}</p>
    <p>Number of reports: {len(reports)}</p>
    
    <h2>Visualizations</h2>
"""
        
        # Add visualization images
        for name, path in visualizations.items():
            if name != "index":
                # Convert path to relative path
                rel_path = os.path.basename(path)
                html_content += f"""
    <div class="viz-container">
        <div class="viz-title">{name.replace('_', ' ').title()}</div>
        <img src="{rel_path}" alt="{name}" style="max-width: 100%;">
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Save the HTML index
        output_path = output_dir / "index.html"
        with open(output_path, "w") as f:
            f.write(html_content)
            
        return output_path 