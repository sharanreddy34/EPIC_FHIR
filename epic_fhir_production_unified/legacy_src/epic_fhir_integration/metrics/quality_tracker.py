"""
Quality Tracker module for historical tracking of data quality metrics.

This module provides functionality for tracking, analyzing, and reporting
on data quality metrics over time, including trend analysis and comparison.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from epic_fhir_integration.metrics.collector import MetricsCollector
from epic_fhir_integration.metrics.data_quality import DataQualityDimension

logger = logging.getLogger(__name__)

class QualityTracker:
    """Tracks data quality metrics over time and provides analysis functionality."""
    
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        output_dir: str = None
    ):
        """Initialize the quality tracker.
        
        Args:
            metrics_collector: Metrics collector with recorded metrics
            output_dir: Optional directory for saving quality reports
        """
        self.metrics_collector = metrics_collector
        self.output_dir = output_dir or os.path.join(os.getcwd(), "quality_reports")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def track_quality_metrics(
        self,
        resource_types: Optional[List[str]] = None,
        quality_dimensions: Optional[List[Union[DataQualityDimension, str]]] = None,
        pipeline_stages: Optional[List[str]] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """Track quality metrics over time.
        
        Args:
            resource_types: Optional list of resource types to include
            quality_dimensions: Optional list of quality dimensions to include
            pipeline_stages: Optional list of pipeline stages to include
            time_range: Optional time range for metrics
            interval: Time interval for aggregation (e.g., "1h", "1d", "1w")
            
        Returns:
            Dictionary with tracked metrics and statistics
        """
        # Convert enum values to strings if needed
        if quality_dimensions:
            quality_dimensions = [
                qd.value if hasattr(qd, "value") else qd 
                for qd in quality_dimensions
            ]
        
        # Build filter for metrics
        filter_dict = {}
        if resource_types:
            filter_dict["resource_type"] = resource_types
        if quality_dimensions:
            filter_dict["dimension"] = quality_dimensions
        if pipeline_stages:
            filter_dict["pipeline_stage"] = pipeline_stages
            
        # Get quality metrics
        metrics = self.metrics_collector.query_metrics(
            metric_pattern="data_quality.*.*",
            filter_dict=filter_dict,
            time_range=time_range
        )
        
        # Return early if no metrics found
        if not metrics:
            return {
                "error": "No quality metrics found",
                "filter": filter_dict,
                "time_range": time_range
            }
        
        # Group metrics by resource type, dimension, and timestamp for tracking
        grouped_metrics = self._group_metrics_for_tracking(metrics, interval)
        
        # Calculate statistics for each group
        stats = self._calculate_quality_statistics(grouped_metrics)
        
        # Identify trends
        trends = self._identify_quality_trends(grouped_metrics)
        
        # Return results
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "filter": filter_dict,
            "time_range": {
                "start": time_range["start"].isoformat() if time_range and "start" in time_range else None,
                "end": time_range["end"].isoformat() if time_range and "end" in time_range else None
            } if time_range else None,
            "interval": interval,
            "metrics_count": len(metrics),
            "tracked_metrics": grouped_metrics,
            "statistics": stats,
            "trends": trends
        }
    
    def generate_quality_report(
        self,
        report_name: str,
        tracked_metrics: Dict[str, Any] = None,
        resource_types: Optional[List[str]] = None,
        quality_dimensions: Optional[List[Union[DataQualityDimension, str]]] = None,
        pipeline_stages: Optional[List[str]] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        interval: str = "1d",
        generate_charts: bool = True
    ) -> str:
        """Generate a quality report and save it to the output directory.
        
        Args:
            report_name: Name of the report
            tracked_metrics: Optional pre-tracked metrics, or None to track new metrics
            resource_types: Optional list of resource types to include (if tracking new metrics)
            quality_dimensions: Optional list of quality dimensions to include (if tracking new metrics)
            pipeline_stages: Optional list of pipeline stages to include (if tracking new metrics)
            time_range: Optional time range for metrics (if tracking new metrics)
            interval: Time interval for aggregation (if tracking new metrics)
            generate_charts: Whether to generate charts for the report
            
        Returns:
            Path to the generated report file
        """
        # Track metrics if not provided
        if tracked_metrics is None:
            tracked_metrics = self.track_quality_metrics(
                resource_types=resource_types,
                quality_dimensions=quality_dimensions,
                pipeline_stages=pipeline_stages,
                time_range=time_range,
                interval=interval
            )
        
        # Add report metadata
        report = {
            "report_name": report_name,
            "generated_at": datetime.utcnow().isoformat(),
            **tracked_metrics
        }
        
        # Create directory for this report
        report_dir = os.path.join(self.output_dir, f"{report_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(report_dir, exist_ok=True)
        
        # Save report as JSON
        report_path = os.path.join(report_dir, "quality_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate charts if requested
        if generate_charts and "tracked_metrics" in report:
            chart_paths = self._generate_quality_charts(report, report_dir)
            report["charts"] = chart_paths
            
            # Update report with chart paths
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        
        logger.info(f"Generated quality report: {report_path}")
        return report_path
    
    def compare_quality_metrics(
        self,
        baseline_time_range: Dict[str, datetime],
        comparison_time_range: Dict[str, datetime],
        resource_types: Optional[List[str]] = None,
        quality_dimensions: Optional[List[Union[DataQualityDimension, str]]] = None,
        pipeline_stages: Optional[List[str]] = None,
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """Compare quality metrics between two time periods.
        
        Args:
            baseline_time_range: Time range for baseline metrics
            comparison_time_range: Time range for comparison metrics
            resource_types: Optional list of resource types to include
            quality_dimensions: Optional list of quality dimensions to include
            pipeline_stages: Optional list of pipeline stages to include
            interval: Time interval for aggregation
            
        Returns:
            Dictionary with comparison results
        """
        # Track baseline metrics
        baseline_metrics = self.track_quality_metrics(
            resource_types=resource_types,
            quality_dimensions=quality_dimensions,
            pipeline_stages=pipeline_stages,
            time_range=baseline_time_range,
            interval=interval
        )
        
        # Track comparison metrics
        comparison_metrics = self.track_quality_metrics(
            resource_types=resource_types,
            quality_dimensions=quality_dimensions,
            pipeline_stages=pipeline_stages,
            time_range=comparison_time_range,
            interval=interval
        )
        
        # If either has an error, return it
        if "error" in baseline_metrics:
            return {
                "error": f"Baseline period error: {baseline_metrics['error']}",
                "baseline_time_range": baseline_time_range,
                "comparison_time_range": comparison_time_range
            }
        
        if "error" in comparison_metrics:
            return {
                "error": f"Comparison period error: {comparison_metrics['error']}",
                "baseline_time_range": baseline_time_range,
                "comparison_time_range": comparison_time_range
            }
        
        # Compare statistics
        comparison_results = self._compare_quality_statistics(
            baseline_metrics["statistics"],
            comparison_metrics["statistics"]
        )
        
        # Return results
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "baseline_time_range": {
                "start": baseline_time_range["start"].isoformat(),
                "end": baseline_time_range["end"].isoformat()
            },
            "comparison_time_range": {
                "start": comparison_time_range["start"].isoformat(),
                "end": comparison_time_range["end"].isoformat()
            },
            "filter": {
                "resource_types": resource_types,
                "quality_dimensions": quality_dimensions,
                "pipeline_stages": pipeline_stages
            },
            "interval": interval,
            "baseline": baseline_metrics["statistics"],
            "comparison": comparison_metrics["statistics"],
            "comparison_results": comparison_results
        }
    
    def _group_metrics_for_tracking(
        self,
        metrics: List[Dict[str, Any]],
        interval: str
    ) -> Dict[str, Any]:
        """Group metrics for tracking by resource type, dimension, and time.
        
        Args:
            metrics: List of quality metrics
            interval: Time interval for aggregation
            
        Returns:
            Dictionary with grouped metrics
        """
        # Create a DataFrame from metrics for easier grouping
        records = []
        for metric in metrics:
            # Extract labels
            resource_type = metric.get("labels", {}).get("resource_type", "unknown")
            dimension = metric.get("labels", {}).get("dimension", "unknown")
            pipeline_stage = metric.get("labels", {}).get("pipeline_stage", "unknown")
            
            # Skip if missing key information
            if not all([resource_type, dimension]):
                continue
                
            # Add record
            records.append({
                "timestamp": datetime.fromisoformat(metric["timestamp"].replace("Z", "+00:00")),
                "resource_type": resource_type,
                "dimension": dimension,
                "pipeline_stage": pipeline_stage,
                "value": metric["value"],
                "metric_name": metric["name"]
            })
        
        # Create DataFrame
        if not records:
            return {}
            
        df = pd.DataFrame(records)
        
        # Determine time interval for resampling
        interval_map = {
            "1h": "H",
            "1d": "D",
            "1w": "W",
            "1m": "M"
        }
        resample_freq = interval_map.get(interval, "D")
        
        # Group by resource type, dimension, and time interval
        grouped = {}
        
        # Get unique combinations of resource_type and dimension
        for resource_type in df["resource_type"].unique():
            grouped[resource_type] = {}
            
            for dimension in df[df["resource_type"] == resource_type]["dimension"].unique():
                # Filter data for this resource_type and dimension
                filtered_df = df[(df["resource_type"] == resource_type) & (df["dimension"] == dimension)]
                
                # Set timestamp as index for resampling
                filtered_df = filtered_df.set_index("timestamp")
                
                # Resample to the specified interval
                resampled = filtered_df["value"].resample(resample_freq).mean()
                
                # Convert back to records
                time_series = []
                for timestamp, value in resampled.items():
                    if not pd.isna(value):  # Skip NaN values
                        time_series.append({
                            "timestamp": timestamp.isoformat(),
                            "value": value
                        })
                
                grouped[resource_type][dimension] = time_series
        
        return grouped
    
    def _calculate_quality_statistics(
        self,
        grouped_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        """Calculate statistics for grouped quality metrics.
        
        Args:
            grouped_metrics: Metrics grouped by resource type and dimension
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            "by_resource_type": {},
            "by_dimension": {},
            "overall": {}
        }
        
        # Collect all values for overall statistics
        all_values = []
        
        # Calculate statistics by resource type and dimension
        for resource_type, dimensions in grouped_metrics.items():
            resource_values = []
            
            stats["by_resource_type"][resource_type] = {
                "dimensions": {}
            }
            
            for dimension, time_series in dimensions.items():
                # Get values
                values = [entry["value"] for entry in time_series]
                
                if not values:
                    continue
                    
                # Calculate statistics for this dimension
                dim_stats = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "median": self._calculate_median(values),
                    "std_dev": self._calculate_std_dev(values),
                    "count": len(values)
                }
                
                # Add to resource dimension stats
                stats["by_resource_type"][resource_type]["dimensions"][dimension] = dim_stats
                
                # Add to dimension stats
                if dimension not in stats["by_dimension"]:
                    stats["by_dimension"][dimension] = {
                        "mean": dim_stats["mean"],
                        "min": dim_stats["min"],
                        "max": dim_stats["max"],
                        "median": dim_stats["median"],
                        "std_dev": dim_stats["std_dev"],
                        "count": dim_stats["count"],
                        "resource_count": 1
                    }
                else:
                    # Update dimension stats with running average
                    d_stats = stats["by_dimension"][dimension]
                    total_count = d_stats["count"] + dim_stats["count"]
                    
                    d_stats["mean"] = (d_stats["mean"] * d_stats["count"] + dim_stats["mean"] * dim_stats["count"]) / total_count
                    d_stats["min"] = min(d_stats["min"], dim_stats["min"])
                    d_stats["max"] = max(d_stats["max"], dim_stats["max"])
                    d_stats["count"] = total_count
                    d_stats["resource_count"] += 1
                
                # Add values to resource values and all values
                resource_values.extend(values)
                all_values.extend(values)
            
            # Calculate overall statistics for this resource type
            if resource_values:
                stats["by_resource_type"][resource_type]["overall"] = {
                    "mean": sum(resource_values) / len(resource_values),
                    "min": min(resource_values),
                    "max": max(resource_values),
                    "median": self._calculate_median(resource_values),
                    "std_dev": self._calculate_std_dev(resource_values),
                    "count": len(resource_values)
                }
        
        # Calculate overall statistics
        if all_values:
            stats["overall"] = {
                "mean": sum(all_values) / len(all_values),
                "min": min(all_values),
                "max": max(all_values),
                "median": self._calculate_median(all_values),
                "std_dev": self._calculate_std_dev(all_values),
                "count": len(all_values),
                "resource_type_count": len(stats["by_resource_type"]),
                "dimension_count": len(stats["by_dimension"])
            }
        
        return stats
    
    def _identify_quality_trends(
        self,
        grouped_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        """Identify trends in quality metrics.
        
        Args:
            grouped_metrics: Metrics grouped by resource type and dimension
            
        Returns:
            Dictionary with trend information
        """
        trends = {
            "by_resource_type": {},
            "by_dimension": {},
            "overall": {
                "improving": [],
                "declining": [],
                "stable": []
            }
        }
        
        # Initialize dimension trends
        dimension_trends = {}
        
        # Analyze trends by resource type and dimension
        for resource_type, dimensions in grouped_metrics.items():
            trends["by_resource_type"][resource_type] = {
                "dimensions": {},
                "overall": {}
            }
            
            for dimension, time_series in dimensions.items():
                # Skip if not enough data points
                if len(time_series) < 3:
                    continue
                    
                # Sort by timestamp
                sorted_series = sorted(time_series, key=lambda x: x["timestamp"])
                
                # Calculate trend
                trend_info = self._calculate_trend(sorted_series)
                
                # Add to resource dimension trends
                trends["by_resource_type"][resource_type]["dimensions"][dimension] = trend_info
                
                # Track dimension trends
                if dimension not in dimension_trends:
                    dimension_trends[dimension] = {
                        "slopes": [],
                        "series_count": 0
                    }
                
                dimension_trends[dimension]["slopes"].append(trend_info["slope"])
                dimension_trends[dimension]["series_count"] += 1
                
                # Add to overall trends
                trend_direction = trend_info["direction"]
                trend_key = f"{resource_type}:{dimension}"
                
                if trend_direction == "improving":
                    trends["overall"]["improving"].append(trend_key)
                elif trend_direction == "declining":
                    trends["overall"]["declining"].append(trend_key)
                else:
                    trends["overall"]["stable"].append(trend_key)
        
        # Calculate trends by dimension
        trends["by_dimension"] = {}
        
        for dimension, trend_data in dimension_trends.items():
            if not trend_data["slopes"]:
                continue
                
            avg_slope = sum(trend_data["slopes"]) / len(trend_data["slopes"])
            
            if abs(avg_slope) < 0.01:
                direction = "stable"
            elif avg_slope > 0:
                direction = "improving"
            else:
                direction = "declining"
            
            trends["by_dimension"][dimension] = {
                "slope": avg_slope,
                "direction": direction,
                "series_count": trend_data["series_count"]
            }
        
        # Add summary counts
        trends["summary"] = {
            "improving_count": len(trends["overall"]["improving"]),
            "declining_count": len(trends["overall"]["declining"]),
            "stable_count": len(trends["overall"]["stable"]),
            "total_count": (
                len(trends["overall"]["improving"]) +
                len(trends["overall"]["declining"]) +
                len(trends["overall"]["stable"])
            )
        }
        
        return trends
    
    def _calculate_trend(
        self,
        time_series: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate trend for a time series of quality metrics.
        
        Args:
            time_series: List of quality metrics with timestamp and value
            
        Returns:
            Dictionary with trend information
        """
        # Extract values
        values = [entry["value"] for entry in time_series]
        
        # Calculate simple linear regression
        n = len(values)
        x = list(range(n))
        
        # Calculate means
        mean_x = sum(x) / n
        mean_y = sum(values) / n
        
        # Calculate slope
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Intercept (b)
        intercept = mean_y - slope * mean_x
        
        # Calculate fitted values
        fitted = [slope * x[i] + intercept for i in range(n)]
        
        # Calculate R-squared
        ss_total = sum((values[i] - mean_y) ** 2 for i in range(n))
        ss_residual = sum((values[i] - fitted[i]) ** 2 for i in range(n))
        
        if ss_total == 0:
            r_squared = 0
        else:
            r_squared = 1 - (ss_residual / ss_total)
        
        # Determine if trend is significant
        if abs(slope) < 0.01 or r_squared < 0.3:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "declining"
        
        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "direction": direction,
            "initial_value": values[0],
            "final_value": values[-1],
            "change": values[-1] - values[0],
            "percent_change": ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
        }
    
    def _compare_quality_statistics(
        self,
        baseline_stats: Dict[str, Any],
        comparison_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare quality statistics between baseline and comparison periods.
        
        Args:
            baseline_stats: Statistics from baseline period
            comparison_stats: Statistics from comparison period
            
        Returns:
            Dictionary with comparison results
        """
        comparison_results = {
            "by_resource_type": {},
            "by_dimension": {},
            "overall": {}
        }
        
        # Compare overall statistics
        if "overall" in baseline_stats and "overall" in comparison_stats:
            baseline_overall = baseline_stats["overall"]
            comparison_overall = comparison_stats["overall"]
            
            comparison_results["overall"] = {
                "mean_change": comparison_overall["mean"] - baseline_overall["mean"],
                "mean_percent_change": (
                    ((comparison_overall["mean"] - baseline_overall["mean"]) / baseline_overall["mean"]) * 100
                    if baseline_overall["mean"] != 0 else 0
                ),
                "min_change": comparison_overall["min"] - baseline_overall["min"],
                "max_change": comparison_overall["max"] - baseline_overall["max"],
                "direction": (
                    "improving" if comparison_overall["mean"] > baseline_overall["mean"]
                    else "declining" if comparison_overall["mean"] < baseline_overall["mean"]
                    else "stable"
                )
            }
        
        # Compare statistics by dimension
        for dimension, baseline_dim_stats in baseline_stats.get("by_dimension", {}).items():
            if dimension in comparison_stats.get("by_dimension", {}):
                comparison_dim_stats = comparison_stats["by_dimension"][dimension]
                
                comparison_results["by_dimension"][dimension] = {
                    "mean_change": comparison_dim_stats["mean"] - baseline_dim_stats["mean"],
                    "mean_percent_change": (
                        ((comparison_dim_stats["mean"] - baseline_dim_stats["mean"]) / baseline_dim_stats["mean"]) * 100
                        if baseline_dim_stats["mean"] != 0 else 0
                    ),
                    "min_change": comparison_dim_stats["min"] - baseline_dim_stats["min"],
                    "max_change": comparison_dim_stats["max"] - baseline_dim_stats["max"],
                    "direction": (
                        "improving" if comparison_dim_stats["mean"] > baseline_dim_stats["mean"]
                        else "declining" if comparison_dim_stats["mean"] < baseline_dim_stats["mean"]
                        else "stable"
                    )
                }
        
        # Compare statistics by resource type
        for resource_type, baseline_resource_stats in baseline_stats.get("by_resource_type", {}).items():
            if resource_type in comparison_stats.get("by_resource_type", {}):
                comparison_resource_stats = comparison_stats["by_resource_type"][resource_type]
                
                comparison_results["by_resource_type"][resource_type] = {
                    "dimensions": {},
                    "overall": {}
                }
                
                # Compare overall statistics for this resource type
                if "overall" in baseline_resource_stats and "overall" in comparison_resource_stats:
                    baseline_overall = baseline_resource_stats["overall"]
                    comparison_overall = comparison_resource_stats["overall"]
                    
                    comparison_results["by_resource_type"][resource_type]["overall"] = {
                        "mean_change": comparison_overall["mean"] - baseline_overall["mean"],
                        "mean_percent_change": (
                            ((comparison_overall["mean"] - baseline_overall["mean"]) / baseline_overall["mean"]) * 100
                            if baseline_overall["mean"] != 0 else 0
                        ),
                        "min_change": comparison_overall["min"] - baseline_overall["min"],
                        "max_change": comparison_overall["max"] - baseline_overall["max"],
                        "direction": (
                            "improving" if comparison_overall["mean"] > baseline_overall["mean"]
                            else "declining" if comparison_overall["mean"] < baseline_overall["mean"]
                            else "stable"
                        )
                    }
                
                # Compare dimension statistics for this resource type
                for dimension, baseline_dim_stats in baseline_resource_stats.get("dimensions", {}).items():
                    if dimension in comparison_resource_stats.get("dimensions", {}):
                        comparison_dim_stats = comparison_resource_stats["dimensions"][dimension]
                        
                        comparison_results["by_resource_type"][resource_type]["dimensions"][dimension] = {
                            "mean_change": comparison_dim_stats["mean"] - baseline_dim_stats["mean"],
                            "mean_percent_change": (
                                ((comparison_dim_stats["mean"] - baseline_dim_stats["mean"]) / baseline_dim_stats["mean"]) * 100
                                if baseline_dim_stats["mean"] != 0 else 0
                            ),
                            "min_change": comparison_dim_stats["min"] - baseline_dim_stats["min"],
                            "max_change": comparison_dim_stats["max"] - baseline_dim_stats["max"],
                            "direction": (
                                "improving" if comparison_dim_stats["mean"] > baseline_dim_stats["mean"]
                                else "declining" if comparison_dim_stats["mean"] < baseline_dim_stats["mean"]
                                else "stable"
                            )
                        }
        
        # Add summary counts
        improving_count = 0
        declining_count = 0
        stable_count = 0
        
        # Count by dimension
        for dim_result in comparison_results["by_dimension"].values():
            if dim_result["direction"] == "improving":
                improving_count += 1
            elif dim_result["direction"] == "declining":
                declining_count += 1
            else:
                stable_count += 1
        
        comparison_results["summary"] = {
            "improving_count": improving_count,
            "declining_count": declining_count,
            "stable_count": stable_count,
            "total_count": improving_count + declining_count + stable_count,
            "overall_direction": (
                comparison_results["overall"]["direction"]
                if "direction" in comparison_results.get("overall", {})
                else "unknown"
            )
        }
        
        return comparison_results
    
    def _generate_quality_charts(
        self,
        report: Dict[str, Any],
        report_dir: str
    ) -> List[str]:
        """Generate charts for quality report.
        
        Args:
            report: Quality report data
            report_dir: Directory to save charts
            
        Returns:
            List of chart file paths
        """
        chart_paths = []
        
        # Create charts directory
        charts_dir = os.path.join(report_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        # Get tracked metrics
        tracked_metrics = report.get("tracked_metrics", {})
        
        # Create overall quality chart
        overall_chart_path = os.path.join(charts_dir, "overall_quality.png")
        self._create_overall_quality_chart(tracked_metrics, overall_chart_path)
        if os.path.exists(overall_chart_path):
            chart_paths.append(os.path.relpath(overall_chart_path, start=report_dir))
        
        # Create charts by resource type
        for resource_type, dimensions in tracked_metrics.items():
            resource_chart_path = os.path.join(charts_dir, f"{resource_type}_quality.png")
            self._create_resource_quality_chart(resource_type, dimensions, resource_chart_path)
            if os.path.exists(resource_chart_path):
                chart_paths.append(os.path.relpath(resource_chart_path, start=report_dir))
        
        # Create charts by dimension
        dimension_data = {}
        
        # Reorganize data by dimension
        for resource_type, dimensions in tracked_metrics.items():
            for dimension, time_series in dimensions.items():
                if dimension not in dimension_data:
                    dimension_data[dimension] = {}
                
                dimension_data[dimension][resource_type] = time_series
        
        # Create dimension charts
        for dimension, resources in dimension_data.items():
            dimension_chart_path = os.path.join(charts_dir, f"{dimension}_quality.png")
            self._create_dimension_quality_chart(dimension, resources, dimension_chart_path)
            if os.path.exists(dimension_chart_path):
                chart_paths.append(os.path.relpath(dimension_chart_path, start=report_dir))
        
        return chart_paths
    
    def _create_overall_quality_chart(
        self,
        tracked_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]],
        output_path: str
    ) -> None:
        """Create overall quality chart.
        
        Args:
            tracked_metrics: Tracked metrics by resource type and dimension
            output_path: Path to save the chart
        """
        plt.figure(figsize=(12, 8))
        
        # Collect all series for averaging
        all_series = {}
        
        for resource_type, dimensions in tracked_metrics.items():
            for dimension, time_series in dimensions.items():
                for entry in time_series:
                    timestamp = entry["timestamp"]
                    value = entry["value"]
                    
                    if timestamp not in all_series:
                        all_series[timestamp] = []
                    
                    all_series[timestamp].append(value)
        
        # Calculate average by timestamp
        if not all_series:
            logger.warning("No data for overall quality chart")
            return
            
        # Sort timestamps
        timestamps = sorted(all_series.keys())
        avg_values = [sum(all_series[ts]) / len(all_series[ts]) for ts in timestamps]
        
        # Convert timestamps to datetime for plotting
        x_values = [datetime.fromisoformat(ts.replace("Z", "+00:00")) for ts in timestamps]
        
        # Plot average quality
        plt.plot(x_values, avg_values, "b-", linewidth=2, label="Average Quality")
        
        # Add trend line
        if len(x_values) > 1:
            z = np.polyfit(range(len(x_values)), avg_values, 1)
            p = np.poly1d(z)
            plt.plot(x_values, p(range(len(x_values))), "r--", label="Trend")
        
        plt.title("Overall Quality Metrics Over Time")
        plt.xlabel("Time")
        plt.ylabel("Quality Score")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        # Save chart
        plt.savefig(output_path)
        plt.close()
    
    def _create_resource_quality_chart(
        self,
        resource_type: str,
        dimensions: Dict[str, List[Dict[str, Any]]],
        output_path: str
    ) -> None:
        """Create quality chart for a resource type.
        
        Args:
            resource_type: Resource type
            dimensions: Dimensions and time series for this resource type
            output_path: Path to save the chart
        """
        plt.figure(figsize=(12, 8))
        
        for dimension, time_series in dimensions.items():
            if not time_series:
                continue
                
            # Sort by timestamp
            sorted_series = sorted(time_series, key=lambda x: x["timestamp"])
            
            # Extract values for plotting
            timestamps = [datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) for entry in sorted_series]
            values = [entry["value"] for entry in sorted_series]
            
            # Plot this dimension
            plt.plot(timestamps, values, "o-", linewidth=2, markersize=5, label=dimension)
        
        plt.title(f"Quality Metrics for {resource_type}")
        plt.xlabel("Time")
        plt.ylabel("Quality Score")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        # Save chart
        plt.savefig(output_path)
        plt.close()
    
    def _create_dimension_quality_chart(
        self,
        dimension: str,
        resources: Dict[str, List[Dict[str, Any]]],
        output_path: str
    ) -> None:
        """Create quality chart for a dimension.
        
        Args:
            dimension: Dimension name
            resources: Resource types and time series for this dimension
            output_path: Path to save the chart
        """
        plt.figure(figsize=(12, 8))
        
        for resource_type, time_series in resources.items():
            if not time_series:
                continue
                
            # Sort by timestamp
            sorted_series = sorted(time_series, key=lambda x: x["timestamp"])
            
            # Extract values for plotting
            timestamps = [datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) for entry in sorted_series]
            values = [entry["value"] for entry in sorted_series]
            
            # Plot this resource type
            plt.plot(timestamps, values, "o-", linewidth=2, markersize=5, label=resource_type)
        
        plt.title(f"{dimension} Quality by Resource Type")
        plt.xlabel("Time")
        plt.ylabel("Quality Score")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        # Save chart
        plt.savefig(output_path)
        plt.close()
    
    @staticmethod
    def _calculate_median(values: List[float]) -> float:
        """Calculate the median of a list of values.
        
        Args:
            values: List of values
            
        Returns:
            Median value
        """
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n == 0:
            return 0
            
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]
    
    @staticmethod
    def _calculate_std_dev(values: List[float]) -> float:
        """Calculate the standard deviation of a list of values.
        
        Args:
            values: List of values
            
        Returns:
            Standard deviation
        """
        n = len(values)
        
        if n <= 1:
            return 0
            
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        return variance ** 0.5 