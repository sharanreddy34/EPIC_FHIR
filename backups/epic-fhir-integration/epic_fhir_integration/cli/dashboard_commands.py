"""
CLI commands for generating and running FHIR data quality dashboards.

This module provides commands for generating and running dashboards
for FHIR data quality metrics and validation results.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import click

from epic_fhir_integration.metrics.dashboard.quality_dashboard import QualityDashboardGenerator
from epic_fhir_integration.metrics.dashboard.validation_dashboard import ValidationDashboard
from epic_fhir_integration.metrics.data_quality import DataQualityAssessor
from epic_fhir_integration.metrics.validation_metrics import ValidationMetrics
from epic_fhir_integration.validation.validator import FHIRValidator


logger = logging.getLogger(__name__)


@click.group(name="dashboard")
def dashboard_group():
    """Commands for generating and running quality dashboards."""
    pass


@dashboard_group.command(name="quality")
@click.option(
    "--report-path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to quality report JSON file"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output/dashboards",
    help="Directory to save dashboard output"
)
@click.option(
    "--title",
    default="FHIR Data Quality Dashboard",
    help="Dashboard title"
)
@click.option(
    "--port",
    type=int,
    default=8050,
    help="Port to run the dashboard server on"
)
@click.option(
    "--static-only",
    is_flag=True,
    help="Generate static HTML file only (don't run server)"
)
@click.option(
    "--output-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path for static HTML output (if static-only is specified)"
)
def quality_dashboard(
    report_path: Optional[str],
    output_dir: str,
    title: str,
    port: int,
    static_only: bool,
    output_file: Optional[str]
):
    """Generate and run quality dashboard."""
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Log parameters
    logger.info(f"Generating quality dashboard with title: {title}")
    logger.info(f"Output directory: {output_dir}")
    
    if report_path:
        # Load from report file
        logger.info(f"Loading quality report from: {report_path}")
        dashboard = QualityDashboardGenerator.from_quality_report(
            report_path=report_path,
            output_dir=output_dir,
            title=title
        )
    else:
        # Create empty dashboard (can be populated later)
        logger.info("Creating empty quality dashboard (no report specified)")
        dashboard = QualityDashboardGenerator(
            output_dir=output_dir,
            title=title,
            port=port
        )
    
    # Set port
    dashboard.port = port
    
    if static_only:
        # Generate static HTML file
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = None
            
        result_path = dashboard.generate_static_dashboard(output_path)
        logger.info(f"Static dashboard generated: {result_path}")
        click.echo(f"Static dashboard generated: {result_path}")
    else:
        # Run dashboard server
        logger.info(f"Starting dashboard server on port {port}")
        click.echo(f"Starting dashboard server on port {port}...")
        dashboard.run_dashboard()


@dashboard_group.command(name="validation")
@click.option(
    "--results-path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to validation results JSON file"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output/dashboards",
    help="Directory to save dashboard output"
)
@click.option(
    "--title",
    default="FHIR Validation Dashboard",
    help="Dashboard title"
)
@click.option(
    "--port",
    type=int,
    default=8051,
    help="Port to run the dashboard server on"
)
@click.option(
    "--static-only",
    is_flag=True,
    help="Generate static HTML file only (don't run server)"
)
@click.option(
    "--output-file",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Path for static HTML output (if static-only is specified)"
)
def validation_dashboard(
    results_path: Optional[str],
    output_dir: str,
    title: str,
    port: int,
    static_only: bool,
    output_file: Optional[str]
):
    """Generate and run validation dashboard."""
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Log parameters
    logger.info(f"Generating validation dashboard with title: {title}")
    logger.info(f"Output directory: {output_dir}")
    
    if results_path:
        # Load from validation results file
        logger.info(f"Loading validation results from: {results_path}")
        dashboard = ValidationDashboard.from_validation_results(
            results_path=results_path,
            output_dir=output_dir,
            title=title
        )
    else:
        # Create empty dashboard (can be populated later)
        logger.info("Creating empty validation dashboard (no results specified)")
        dashboard = ValidationDashboard(
            output_dir=output_dir,
            title=title,
            port=port
        )
    
    # Set port
    dashboard.port = port
    
    if static_only:
        # Generate static HTML file
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = None
            
        result_path = dashboard.generate_static_dashboard(output_path)
        logger.info(f"Static validation dashboard generated: {result_path}")
        click.echo(f"Static validation dashboard generated: {result_path}")
    else:
        # Run dashboard server
        logger.info(f"Starting validation dashboard server on port {port}")
        click.echo(f"Starting validation dashboard server on port {port}...")
        dashboard.run_dashboard()


@dashboard_group.command(name="combined")
@click.option(
    "--quality-report",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to quality report JSON file"
)
@click.option(
    "--validation-results",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to validation results JSON file"
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output/dashboards",
    help="Directory to save dashboard output"
)
@click.option(
    "--quality-port",
    type=int,
    default=8050,
    help="Port for quality dashboard server"
)
@click.option(
    "--validation-port",
    type=int,
    default=8051,
    help="Port for validation dashboard server"
)
@click.option(
    "--static-only",
    is_flag=True,
    help="Generate static HTML files only (don't run servers)"
)
def combined_dashboard(
    quality_report: Optional[str],
    validation_results: Optional[str],
    output_dir: str,
    quality_port: int,
    validation_port: int,
    static_only: bool
):
    """Generate and run both quality and validation dashboards."""
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Log parameters
    logger.info("Generating combined dashboards")
    logger.info(f"Output directory: {output_dir}")
    
    # Create quality dashboard
    if quality_report:
        logger.info(f"Loading quality report from: {quality_report}")
        quality_dashboard = QualityDashboardGenerator.from_quality_report(
            report_path=quality_report,
            output_dir=output_dir,
            title="FHIR Data Quality Dashboard"
        )
        quality_dashboard.port = quality_port
        
        if static_only:
            quality_result = quality_dashboard.generate_static_dashboard()
            logger.info(f"Static quality dashboard generated: {quality_result}")
            click.echo(f"Static quality dashboard generated: {quality_result}")
    
    # Create validation dashboard
    if validation_results:
        logger.info(f"Loading validation results from: {validation_results}")
        validation_dashboard = ValidationDashboard.from_validation_results(
            results_path=validation_results,
            output_dir=output_dir,
            title="FHIR Validation Dashboard"
        )
        validation_dashboard.port = validation_port
        
        if static_only:
            validation_result = validation_dashboard.generate_static_dashboard()
            logger.info(f"Static validation dashboard generated: {validation_result}")
            click.echo(f"Static validation dashboard generated: {validation_result}")
    
    if not static_only:
        # Run both dashboards
        if quality_report:
            logger.info(f"Starting quality dashboard server on port {quality_port}")
            click.echo(f"Starting quality dashboard server on port {quality_port}...")
            
            # We can't run both servers in the same process, so we'll just run one
            # and provide instructions for the other
            click.echo("\nNOTE: To run the validation dashboard, open another terminal and run:")
            click.echo(f"  epic-fhir dashboard validation --results-path {validation_results} --port {validation_port}")
            
            quality_dashboard.run_dashboard()
        elif validation_results:
            logger.info(f"Starting validation dashboard server on port {validation_port}")
            click.echo(f"Starting validation dashboard server on port {validation_port}...")
            validation_dashboard.run_dashboard()
        else:
            click.echo("No dashboards to run. Specify at least one of --quality-report or --validation-results")


@dashboard_group.command(name="create-examples")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output/dashboards",
    help="Directory to save example dashboards"
)
def create_examples(output_dir: str):
    """Generate example dashboards with sample data."""
    # Create output directory if it doesn't exist
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Log parameters
    logger.info("Generating example dashboards")
    logger.info(f"Output directory: {output_dir}")
    
    # Create sample quality report
    from datetime import datetime
    import json
    
    quality_report = {
        "report_id": "example-report-" + datetime.now().strftime("%Y%m%d"),
        "timestamp": datetime.now().isoformat(),
        "overall_score": 0.82,
        "dimension_scores": {
            "completeness": 0.88,
            "conformance": 0.75,
            "consistency": 0.85,
            "timeliness": 0.80
        },
        "resource_scores": {
            "Patient": {
                "completeness": 0.90,
                "conformance": 0.85,
                "consistency": 0.88
            },
            "Observation": {
                "completeness": 0.75,
                "conformance": 0.70,
                "consistency": 0.82
            },
            "Condition": {
                "completeness": 0.85,
                "conformance": 0.78,
                "consistency": 0.80
            }
        },
        "quality_issues": [
            {
                "category": "Missing Data",
                "severity": "medium",
                "description": "Patient resources missing address information",
                "affected_count": 12,
                "total_count": 100
            },
            {
                "category": "Terminology",
                "severity": "high",
                "description": "Non-standard codes in Observation resources",
                "affected_count": 25,
                "total_count": 150
            },
            {
                "category": "Consistency",
                "severity": "low",
                "description": "Inconsistent units in lab results",
                "affected_count": 8,
                "total_count": 200
            }
        ]
    }
    
    # Create sample validation results
    validation_results = {
        "results": [
            {
                "resourceType": "Patient",
                "id": "patient-example-1",
                "valid": True,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
                "issues": []
            },
            {
                "resourceType": "Patient",
                "id": "patient-example-2",
                "valid": False,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
                "issues": [
                    {
                        "severity": "error",
                        "type": "required",
                        "message": "Patient.name: minimum required = 1, but only found 0",
                        "location": ["Patient.name"]
                    }
                ]
            },
            {
                "resourceType": "Observation",
                "id": "observation-example-1",
                "valid": True,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"],
                "issues": []
            },
            {
                "resourceType": "Observation",
                "id": "observation-example-2",
                "valid": False,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab"],
                "issues": [
                    {
                        "severity": "warning",
                        "type": "value",
                        "message": "Observation.value[x]: None of the types are valid",
                        "location": ["Observation.value[x]"]
                    },
                    {
                        "severity": "information",
                        "type": "informational",
                        "message": "Observation.code: A code with this value should come from a standard terminology"
                    }
                ]
            },
            {
                "resourceType": "Condition",
                "id": "condition-example-1",
                "valid": True,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"],
                "issues": []
            },
            {
                "resourceType": "Condition",
                "id": "condition-example-2",
                "valid": False,
                "profiles": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition"],
                "issues": [
                    {
                        "severity": "error",
                        "type": "value",
                        "message": "Condition.subject: No Reference provided, or Reference could not be resolved",
                        "location": ["Condition.subject"]
                    }
                ]
            }
        ],
        "profiles": {
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient": {
                "total": 2,
                "conformant": 1
            },
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab": {
                "total": 2,
                "conformant": 1
            },
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition": {
                "total": 2,
                "conformant": 1
            }
        }
    }
    
    # Save sample data to files
    quality_report_path = output_dir_path / "example_quality_report.json"
    validation_results_path = output_dir_path / "example_validation_results.json"
    
    with open(quality_report_path, "w") as f:
        json.dump(quality_report, f, indent=2)
    
    with open(validation_results_path, "w") as f:
        json.dump(validation_results, f, indent=2)
    
    # Create dashboards
    quality_dashboard = QualityDashboardGenerator.from_quality_report(
        report_path=quality_report_path,
        output_dir=output_dir,
        title="Example Quality Dashboard"
    )
    
    validation_dashboard = ValidationDashboard.from_validation_results(
        results_path=validation_results_path,
        output_dir=output_dir,
        title="Example Validation Dashboard"
    )
    
    # Generate static dashboards
    quality_output = quality_dashboard.generate_static_dashboard(
        output_path=output_dir_path / "example_quality_dashboard.html"
    )
    
    validation_output = validation_dashboard.generate_static_dashboard(
        output_path=output_dir_path / "example_validation_dashboard.html"
    )
    
    # Output paths
    logger.info(f"Created example quality report: {quality_report_path}")
    logger.info(f"Created example validation results: {validation_results_path}")
    logger.info(f"Generated example quality dashboard: {quality_output}")
    logger.info(f"Generated example validation dashboard: {validation_output}")
    
    click.echo(f"Example quality report created: {quality_report_path}")
    click.echo(f"Example validation results created: {validation_results_path}")
    click.echo(f"Example quality dashboard generated: {quality_output}")
    click.echo(f"Example validation dashboard generated: {validation_output}")
    click.echo("\nTo run these dashboards:")
    click.echo(f"  epic-fhir dashboard quality --report-path {quality_report_path}")
    click.echo(f"  epic-fhir dashboard validation --results-path {validation_results_path}")


def register_commands(cli):
    """Register dashboard commands with the CLI."""
    cli.add_command(dashboard_group) 