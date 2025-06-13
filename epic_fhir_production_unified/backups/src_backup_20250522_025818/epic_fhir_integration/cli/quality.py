"""
CLI commands for data quality assessment and reporting.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from epic_fhir_integration.metrics.collector import MetricsCollector
from epic_fhir_integration.metrics.data_quality import DataQualityAssessor
from epic_fhir_integration.metrics.great_expectations_validator import GreatExpectationsValidator
from epic_fhir_integration.metrics.quality_alerts import AlertCategory, AlertSeverity, QualityAlert
from epic_fhir_integration.metrics.quality_interventions import (
    InterventionManager, InterventionStatus, create_intervention_for_completeness_issue
)
from epic_fhir_integration.metrics.quality_tracker import QualityTracker
from epic_fhir_integration.metrics.validation_metrics import ValidationMetricsRecorder

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def quality():
    """Commands for data quality assessment and reporting."""
    pass


@quality.command(name="assess")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--resource-type", 
    type=str, 
    help="Resource type to assess"
)
@click.option(
    "--output", 
    type=click.Path(), 
    help="Output file for quality assessment results"
)
@click.option(
    "--metrics-dir",
    type=click.Path(),
    help="Directory to store metrics data"
)
@click.option(
    "--expectation-dir",
    type=click.Path(),
    help="Directory for Great Expectations suites"
)
def assess_quality(
    input_file: str,
    resource_type: Optional[str] = None,
    output: Optional[str] = None,
    metrics_dir: Optional[str] = None,
    expectation_dir: Optional[str] = None
):
    """Assess the quality of FHIR resources.
    
    INPUT_FILE: Path to a FHIR resource file (JSON)
    """
    try:
        # Initialize metrics collector
        metrics_collector = MetricsCollector(storage_dir=metrics_dir) if metrics_dir else None
        
        # Initialize data quality assessor
        data_quality_assessor = DataQualityAssessor(metrics_collector)
        
        # Initialize validation tools
        validation_metrics_recorder = ValidationMetricsRecorder(metrics_collector)
        
        # Initialize Great Expectations validator
        ge_validator = GreatExpectationsValidator(
            validation_metrics_recorder=validation_metrics_recorder,
            expectation_suite_dir=expectation_dir
        )
        
        # Load FHIR resource(s)
        with open(input_file, "r") as f:
            data = json.load(f)
        
        # Handle bundle vs. single resource
        resources = []
        if isinstance(data, list):
            resources = data
        elif data.get("resourceType") == "Bundle" and "entry" in data:
            resources = [entry.get("resource", {}) for entry in data.get("entry", [])]
        else:
            resources = [data]
        
        console.print(f"Loaded [bold]{len(resources)}[/bold] resources")
        
        # Determine resource types if not specified
        if not resource_type:
            resource_types = set(r.get("resourceType") for r in resources if r.get("resourceType"))
            console.print(f"Found resource types: [bold]{', '.join(resource_types)}[/bold]")
        else:
            # Filter by resource type if specified
            resources = [r for r in resources if r.get("resourceType") == resource_type]
            console.print(f"Filtered to [bold]{len(resources)}[/bold] {resource_type} resources")
        
        # Assess quality of each resource
        quality_results = []
        validation_results = []
        
        for resource in resources:
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id", "unknown")
            
            # Skip if resource type is missing
            if not resource_type:
                console.print(f"[yellow]Warning: Resource missing resourceType, skipping[/yellow]")
                continue
            
            # Validate resource
            expectation_suite = resource_type.lower()
            if resource_type == "MedicationRequest":
                expectation_suite = "medication_request"
                
            validation_result = ge_validator.validate_resource(
                resource=resource,
                expectation_suite_name=expectation_suite,
                pipeline_stage="assess"
            )
            validation_results.append(validation_result)
            
            # Assess resource quality
            quality_result = data_quality_assessor.assess_overall_quality(resource)
            quality_result["resource_type"] = resource_type
            quality_result["resource_id"] = resource_id
            quality_results.append(quality_result)
        
        # Output summary table
        table = Table(title="Quality Assessment Summary")
        table.add_column("Resource Type")
        table.add_column("Resource ID")
        table.add_column("Quality Score")
        table.add_column("Valid")
        table.add_column("Issues")
        
        for i, result in enumerate(quality_results):
            resource_type = result["resource_type"]
            resource_id = result["resource_id"]
            quality_score = result["overall_quality_score"]
            is_valid = validation_results[i]["is_valid"]
            issue_count = len(validation_results[i]["issues"])
            
            # Format score
            score_str = f"{quality_score:.2f}"
            if quality_score >= 0.8:
                score_str = f"[green]{score_str}[/green]"
            elif quality_score >= 0.6:
                score_str = f"[yellow]{score_str}[/yellow]"
            else:
                score_str = f"[red]{score_str}[/red]"
            
            # Format valid
            valid_str = "[green]Yes[/green]" if is_valid else "[red]No[/red]"
            
            # Format issues
            issues_str = str(issue_count)
            if issue_count > 0:
                issues_str = f"[red]{issues_str}[/red]"
            
            table.add_row(resource_type, resource_id, score_str, valid_str, issues_str)
        
        console.print(table)
        
        # Calculate overall statistics
        valid_count = sum(1 for r in validation_results if r["is_valid"])
        total_issues = sum(len(r["issues"]) for r in validation_results)
        avg_quality = sum(r["overall_quality_score"] for r in quality_results) / len(quality_results) if quality_results else 0
        
        console.print(f"Overall quality score: [bold]{avg_quality:.2f}[/bold]")
        console.print(f"Valid resources: [bold]{valid_count}/{len(validation_results)}[/bold]")
        console.print(f"Total issues: [bold]{total_issues}[/bold]")
        
        # Save results if output specified
        if output:
            combined_results = {
                "timestamp": datetime.utcnow().isoformat(),
                "input_file": input_file,
                "resource_count": len(resources),
                "quality_results": quality_results,
                "validation_results": validation_results,
                "summary": {
                    "average_quality_score": avg_quality,
                    "valid_resources": valid_count,
                    "total_resources": len(validation_results),
                    "total_issues": total_issues
                }
            }
            
            with open(output, "w") as f:
                json.dump(combined_results, f, indent=2)
                
            console.print(f"Results saved to [bold]{output}[/bold]")
        
        # Flush metrics collector if available
        if metrics_collector:
            metrics_collector.flush()
            console.print(f"Metrics saved to [bold]{metrics_dir}[/bold]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error during quality assessment")
        return 1
    
    return 0


@quality.command(name="report")
@click.option(
    "--metrics-dir",
    type=click.Path(exists=True),
    required=True,
    help="Directory with metrics data"
)
@click.option(
    "--output-dir",
    type=click.Path(),
    help="Directory to save quality reports"
)
@click.option(
    "--report-name",
    type=str,
    default="quality_report",
    help="Name for the quality report"
)
@click.option(
    "--resource-type",
    type=str,
    multiple=True,
    help="Filter to specific resource types"
)
@click.option(
    "--days",
    type=int,
    default=7,
    help="Number of days to include in the report"
)
@click.option(
    "--generate-charts/--no-charts",
    default=True,
    help="Whether to generate charts"
)
def generate_report(
    metrics_dir: str,
    output_dir: Optional[str] = None,
    report_name: str = "quality_report",
    resource_type: List[str] = None,
    days: int = 7,
    generate_charts: bool = True
):
    """Generate a quality report from collected metrics.
    
    This command analyzes metrics data and generates a quality report with
    trends, statistics, and visualizations.
    """
    try:
        # Initialize metrics collector with stored data
        metrics_collector = MetricsCollector(storage_dir=metrics_dir, load_existing=True)
        
        # Initialize quality tracker
        tracker = QualityTracker(
            metrics_collector=metrics_collector,
            output_dir=output_dir
        )
        
        # Define time range
        time_range = None
        if days > 0:
            now = datetime.utcnow()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = start_time.replace(day=start_time.day - days)
            time_range = {"start": start_time, "end": now}
            
            console.print(f"Analyzing quality metrics from [bold]{start_time.strftime('%Y-%m-%d')}[/bold] to [bold]{now.strftime('%Y-%m-%d')}[/bold]")
        
        # Generate quality report
        report_path = tracker.generate_quality_report(
            report_name=report_name,
            resource_types=resource_type if resource_type else None,
            time_range=time_range,
            interval="1d",
            generate_charts=generate_charts
        )
        
        console.print(f"Generated quality report: [bold]{report_path}[/bold]")
        
        # Load report for display
        with open(report_path, "r") as f:
            report = json.load(f)
        
        # Display summary statistics
        if "statistics" in report and "overall" in report["statistics"]:
            overall = report["statistics"]["overall"]
            
            table = Table(title="Quality Report Summary")
            table.add_column("Metric")
            table.add_column("Value")
            
            table.add_row("Average Quality Score", f"{overall.get('mean', 0):.2f}")
            table.add_row("Minimum Quality Score", f"{overall.get('min', 0):.2f}")
            table.add_row("Maximum Quality Score", f"{overall.get('max', 0):.2f}")
            table.add_row("Standard Deviation", f"{overall.get('std_dev', 0):.2f}")
            table.add_row("Resource Types", str(overall.get("resource_type_count", 0)))
            table.add_row("Quality Dimensions", str(overall.get("dimension_count", 0)))
            
            console.print(table)
        
        # Display trends
        if "trends" in report and "summary" in report["trends"]:
            trends = report["trends"]["summary"]
            
            table = Table(title="Quality Trends")
            table.add_column("Trend")
            table.add_column("Count")
            
            table.add_row("Improving", str(trends.get("improving_count", 0)))
            table.add_row("Declining", str(trends.get("declining_count", 0)))
            table.add_row("Stable", str(trends.get("stable_count", 0)))
            
            console.print(table)
        
        # Display chart information if available
        if "charts" in report and report["charts"]:
            console.print(f"[bold]Generated Charts:[/bold]")
            for chart_path in report["charts"]:
                console.print(f"  - {chart_path}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error during report generation")
        return 1
    
    return 0


@quality.command(name="compare")
@click.option(
    "--metrics-dir",
    type=click.Path(exists=True),
    required=True,
    help="Directory with metrics data"
)
@click.option(
    "--baseline-days",
    type=int,
    default=14,
    help="Number of days ago to start baseline period"
)
@click.option(
    "--baseline-length",
    type=int,
    default=7,
    help="Length of baseline period in days"
)
@click.option(
    "--comparison-days",
    type=int,
    default=7,
    help="Number of days ago to start comparison period"
)
@click.option(
    "--comparison-length",
    type=int,
    default=7,
    help="Length of comparison period in days"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file for comparison results"
)
@click.option(
    "--resource-type",
    type=str,
    multiple=True,
    help="Filter to specific resource types"
)
def compare_quality(
    metrics_dir: str,
    baseline_days: int = 14,
    baseline_length: int = 7,
    comparison_days: int = 7,
    comparison_length: int = 7,
    output: Optional[str] = None,
    resource_type: List[str] = None
):
    """Compare quality metrics between two time periods.
    
    This command compares quality metrics between a baseline period and
    a comparison period to identify improvements or regressions.
    """
    try:
        # Initialize metrics collector with stored data
        metrics_collector = MetricsCollector(storage_dir=metrics_dir, load_existing=True)
        
        # Initialize quality tracker
        tracker = QualityTracker(
            metrics_collector=metrics_collector
        )
        
        # Calculate time ranges
        now = datetime.utcnow()
        
        # Baseline period
        baseline_end = now.replace(day=now.day - baseline_days)
        baseline_start = baseline_end.replace(day=baseline_end.day - baseline_length)
        baseline_range = {"start": baseline_start, "end": baseline_end}
        
        # Comparison period
        comparison_end = now.replace(day=now.day - comparison_days)
        comparison_start = comparison_end.replace(day=comparison_end.day - comparison_length)
        comparison_range = {"start": comparison_start, "end": comparison_end}
        
        console.print(f"Baseline period: [bold]{baseline_start.strftime('%Y-%m-%d')}[/bold] to [bold]{baseline_end.strftime('%Y-%m-%d')}[/bold]")
        console.print(f"Comparison period: [bold]{comparison_start.strftime('%Y-%m-%d')}[/bold] to [bold]{comparison_end.strftime('%Y-%m-%d')}[/bold]")
        
        # Compare quality metrics
        comparison = tracker.compare_quality_metrics(
            baseline_time_range=baseline_range,
            comparison_time_range=comparison_range,
            resource_types=resource_type if resource_type else None
        )
        
        # Display comparison results
        table = Table(title="Quality Comparison")
        table.add_column("Metric")
        table.add_column("Baseline")
        table.add_column("Comparison")
        table.add_column("Change")
        table.add_column("% Change")
        
        # Overall comparison
        if "overall" in comparison["comparison_results"]:
            overall = comparison["comparison_results"]["overall"]
            baseline_avg = comparison["baseline"]["overall"]["mean"]
            comparison_avg = comparison["comparison"]["overall"]["mean"]
            
            mean_change = overall["mean_change"]
            mean_percent_change = overall["mean_percent_change"]
            direction = overall["direction"]
            
            # Format change
            change_str = f"{mean_change:.2f}"
            if mean_change > 0:
                change_str = f"[green]+{change_str}[/green]"
            elif mean_change < 0:
                change_str = f"[red]{change_str}[/red]"
                
            # Format percent change
            percent_str = f"{mean_percent_change:.1f}%"
            if mean_percent_change > 0:
                percent_str = f"[green]+{percent_str}[/green]"
            elif mean_percent_change < 0:
                percent_str = f"[red]{percent_str}[/red]"
                
            table.add_row(
                "Overall Quality", 
                f"{baseline_avg:.2f}",
                f"{comparison_avg:.2f}",
                change_str,
                percent_str
            )
            
        console.print(table)
        
        # Display dimension comparison
        if "by_dimension" in comparison["comparison_results"]:
            table = Table(title="Quality by Dimension")
            table.add_column("Dimension")
            table.add_column("Baseline")
            table.add_column("Comparison")
            table.add_column("Change")
            table.add_column("Direction")
            
            for dimension, results in comparison["comparison_results"]["by_dimension"].items():
                baseline_val = None
                comparison_val = None
                
                # Find values in baseline and comparison
                if dimension in comparison["baseline"].get("by_dimension", {}):
                    baseline_val = comparison["baseline"]["by_dimension"][dimension]["mean"]
                    
                if dimension in comparison["comparison"].get("by_dimension", {}):
                    comparison_val = comparison["comparison"]["by_dimension"][dimension]["mean"]
                
                if baseline_val is None or comparison_val is None:
                    continue
                    
                change = results["mean_change"]
                direction = results["direction"]
                
                # Format direction
                direction_str = direction
                if direction == "improving":
                    direction_str = f"[green]{direction}[/green]"
                elif direction == "declining":
                    direction_str = f"[red]{direction}[/red]"
                else:
                    direction_str = f"[yellow]{direction}[/yellow]"
                
                # Format change
                change_str = f"{change:.2f}"
                if change > 0:
                    change_str = f"[green]+{change_str}[/green]"
                elif change < 0:
                    change_str = f"[red]{change_str}[/red]"
                
                table.add_row(
                    dimension,
                    f"{baseline_val:.2f}",
                    f"{comparison_val:.2f}",
                    change_str,
                    direction_str
                )
                
            console.print(table)
        
        # Save comparison if output specified
        if output:
            with open(output, "w") as f:
                json.dump(comparison, f, indent=2)
                
            console.print(f"Comparison saved to [bold]{output}[/bold]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error during quality comparison")
        return 1
    
    return 0


@quality.command(name="interventions")
@click.option(
    "--alerts-file",
    type=click.Path(exists=True),
    help="File containing quality alerts to process"
)
@click.option(
    "--intervention-dir",
    type=click.Path(),
    help="Directory to store intervention records"
)
@click.option(
    "--list-active",
    is_flag=True,
    help="List active interventions"
)
@click.option(
    "--resource-file",
    type=click.Path(exists=True),
    help="FHIR resource file for direct intervention creation"
)
@click.option(
    "--resource-type",
    type=str,
    help="Resource type for direct intervention"
)
@click.option(
    "--issue-type",
    type=click.Choice(["completeness", "conformance", "consistency", "validation"]),
    help="Type of issue for direct intervention"
)
@click.option(
    "--severity",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="high",
    help="Severity level for direct intervention"
)
def manage_interventions(
    alerts_file: Optional[str] = None,
    intervention_dir: Optional[str] = None,
    list_active: bool = False,
    resource_file: Optional[str] = None,
    resource_type: Optional[str] = None,
    issue_type: Optional[str] = None,
    severity: str = "high"
):
    """Manage quality interventions.
    
    This command processes quality alerts and creates appropriate 
    interventions based on alert type and severity. It can also
    create interventions directly from FHIR resources with issues.
    """
    try:
        # Set up intervention manager
        intervention_manager = InterventionManager(
            storage_dir=intervention_dir
        )
        
        # If list_active flag is set, just list active interventions and exit
        if list_active and intervention_dir:
            _list_interventions(intervention_dir)
            return 0
        
        # Process alerts if file provided
        if alerts_file:
            # Load alerts from file
            with open(alerts_file, "r") as f:
                alerts_data = json.load(f)
                
            alerts = []
            # Convert JSON to QualityAlert objects
            for alert_data in alerts_data:
                alert = QualityAlert(
                    definition=None,
                    metric_value=alert_data.get("metric_value", 0.0),
                    details=alert_data.get("details", {}),
                    timestamp=datetime.fromisoformat(alert_data.get("timestamp", datetime.utcnow().isoformat()))
                )
                alert.id = alert_data.get("id", f"alert_{len(alerts)}")
                alert.name = alert_data.get("name", "Unknown alert")
                alert.description = alert_data.get("description", "")
                alert.severity = alert_data.get("severity", "medium")
                alert.category = alert_data.get("category", "unknown")
                alert.status = alert_data.get("status", "active")
                
                alerts.append(alert)
                
            console.print(f"Loaded [bold]{len(alerts)}[/bold] alerts from {alerts_file}")
            
            # Process each alert
            processed_count = 0
            intervention_table = Table(title="Created Interventions")
            intervention_table.add_column("Alert")
            intervention_table.add_column("Type")
            intervention_table.add_column("Priority")
            intervention_table.add_column("Status")
            
            for alert in alerts:
                if alert.status != "active":
                    continue
                    
                intervention = intervention_manager.process_alert(alert)
                if intervention:
                    processed_count += 1
                    intervention_table.add_row(
                        alert.name,
                        str(intervention.intervention_type),
                        str(intervention.priority),
                        str(intervention.status)
                    )
            
            console.print(f"Created [bold]{processed_count}[/bold] interventions for alerts")
            if processed_count > 0:
                console.print(intervention_table)
        
        # Create intervention directly from resource if provided
        if resource_file and issue_type:
            # Load resource
            with open(resource_file, "r") as f:
                resource_data = json.load(f)
            
            # Get resource type if not provided
            if not resource_type:
                resource_type = resource_data.get("resourceType", "Unknown")
            
            console.print(f"Creating intervention for {resource_type} resource with {issue_type} issue")
            
            # Map severity string to enum
            severity_map = {
                "critical": AlertSeverity.CRITICAL,
                "high": AlertSeverity.HIGH,
                "medium": AlertSeverity.MEDIUM,
                "low": AlertSeverity.LOW
            }
            severity_value = severity_map.get(severity, AlertSeverity.HIGH)
            
            # Create appropriate intervention based on issue type
            if issue_type == "completeness":
                # For demonstration, we'll assume these fields are missing
                missing_fields = []
                
                # Check if we're dealing with a bundle vs single resource
                resources = []
                if resource_data.get("resourceType") == "Bundle" and "entry" in resource_data:
                    resources = [entry.get("resource", {}) for entry in resource_data.get("entry", [])]
                    # Filter to requested resource type if specified
                    if resource_type != "Unknown":
                        resources = [r for r in resources if r.get("resourceType") == resource_type]
                else:
                    resources = [resource_data]
                
                interventions = []
                
                # Process each resource
                for resource in resources:
                    # Identify missing fields based on resource type
                    if resource.get("resourceType") == "Patient":
                        for field in ["name", "gender", "birthDate"]:
                            if field not in resource:
                                missing_fields.append(field)
                    elif resource.get("resourceType") == "Observation":
                        for field in ["status", "code", "subject"]:
                            if field not in resource:
                                missing_fields.append(field)
                    
                    if missing_fields:
                        intervention = create_intervention_for_completeness_issue(
                            resource=resource,
                            missing_fields=missing_fields,
                            severity=severity_value
                        )
                        
                        # Execute the intervention
                        intervention_manager.execute_intervention(intervention)
                        interventions.append(intervention)
                
                if interventions:
                    console.print(f"Created and executed [bold]{len(interventions)}[/bold] completeness interventions")
                    
                    # Show table of created interventions
                    table = Table(title="Completeness Interventions")
                    table.add_column("Resource Type")
                    table.add_column("Resource ID")
                    table.add_column("Missing Fields")
                    table.add_column("Status")
                    
                    for intervention in interventions:
                        resource_id = intervention.alert.details.get("resource_id", "unknown")
                        resource_type = intervention.alert.details.get("resource_type", "Unknown")
                        missing_fields_str = ", ".join(intervention.alert.details.get("missing_fields", []))
                        
                        table.add_row(
                            resource_type,
                            resource_id,
                            missing_fields_str,
                            str(intervention.status)
                        )
                    
                    console.print(table)
                else:
                    console.print("[yellow]No completeness issues found requiring intervention[/yellow]")
        
            # Handle other issue types similarly
            # (conformance, consistency, validation)
        
        if not alerts_file and not resource_file and not list_active:
            console.print("[yellow]No action specified. Use --alerts-file, --resource-file, or --list-active[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Error during intervention management")
        return 1
    
    return 0

def _list_interventions(intervention_dir: str) -> None:
    """List interventions from the intervention directory.
    
    Args:
        intervention_dir: Directory containing intervention records
    """
    # Check if directory exists
    if not os.path.exists(intervention_dir):
        console.print(f"[yellow]Intervention directory {intervention_dir} does not exist[/yellow]")
        return
    
    # Find all JSON files in the directory
    json_files = [f for f in os.listdir(intervention_dir) if f.endswith('.json')]
    
    if not json_files:
        console.print(f"[yellow]No intervention records found in {intervention_dir}[/yellow]")
        return
    
    console.print(f"Found [bold]{len(json_files)}[/bold] intervention records")
    
    # Load and display interventions
    interventions = []
    for filename in json_files:
        try:
            with open(os.path.join(intervention_dir, filename), "r") as f:
                intervention_data = json.load(f)
                interventions.append(intervention_data)
        except Exception as e:
            console.print(f"[red]Error loading {filename}: {str(e)}[/red]")
    
    # Create table of interventions
    table = Table(title="Quality Interventions")
    table.add_column("Alert")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Completed")
    
    # Sort by creation date, newest first
    interventions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    for intervention in interventions:
        # Format dates
        created_at = intervention.get("created_at", "")
        if created_at:
            created_at = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
            
        completed_at = intervention.get("completed_at")
        if completed_at:
            completed_at = datetime.fromisoformat(completed_at).strftime("%Y-%m-%d %H:%M")
        else:
            completed_at = ""
        
        # Format status with color
        status = intervention.get("status", "")
        if status == InterventionStatus.COMPLETED:
            status = f"[green]{status}[/green]"
        elif status == InterventionStatus.FAILED:
            status = f"[red]{status}[/red]"
        elif status == InterventionStatus.IN_PROGRESS:
            status = f"[blue]{status}[/blue]"
        elif status == InterventionStatus.PENDING:
            status = f"[yellow]{status}[/yellow]"
        
        table.add_row(
            intervention.get("alert_name", ""),
            intervention.get("intervention_type", ""),
            status,
            created_at,
            completed_at
        )
    
    console.print(table) 