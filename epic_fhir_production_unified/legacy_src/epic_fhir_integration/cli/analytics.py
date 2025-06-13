"""
Command-line interface for FHIR analytics operations using Pathling.

This module provides commands for performing analytics operations on FHIR data
using the Pathling analytics engine.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List

import click
import pandas as pd

from epic_fhir_integration.analytics.pathling_service import PathlingService
from epic_fhir_integration.config import settings

logger = logging.getLogger(__name__)

@click.group()
def analytics():
    """Commands for FHIR analytics operations using Pathling."""
    pass

@analytics.command("start-server")
@click.option("--data-dir", "-d", type=str, help="Directory containing FHIR data files")
@click.option("--port", "-p", type=int, default=8080, help="Port to run the Pathling server on")
def start_server(data_dir: Optional[str], port: int):
    """Start the Pathling analytics server using Docker."""
    try:
        # Override the docker-compose file to use the specified port
        compose_file = "docker-compose.yml"
        with open(compose_file, "w") as f:
            f.write(f"""version: '3'

services:
  pathling:
    image: aehrc/pathling:6.3.0
    ports:
      - "{port}:8080"
    volumes:
      - ./{data_dir or 'data'}:/app/data
    environment:
      - JAVA_TOOL_OPTIONS=-Xmx4g
""")
        
        # Create data directory if specified
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
        
        # Start Pathling server
        service = PathlingService(use_docker=True)
        service.start_server(data_dir)
        
        click.echo(f"Pathling server started on http://localhost:{port}/fhir")
        click.echo("Press Ctrl+C to stop the server")
        
        # Keep the server running until user interrupts
        try:
            while True:
                pass
        except KeyboardInterrupt:
            click.echo("Stopping Pathling server...")
            service.stop_server()
            click.echo("Pathling server stopped")
            
    except Exception as e:
        logger.error(f"Failed to start Pathling server: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@analytics.command("stop-server")
def stop_server():
    """Stop the Pathling analytics server."""
    try:
        service = PathlingService(use_docker=True)
        service.stop_server()
        click.echo("Pathling server stopped")
    except Exception as e:
        logger.error(f"Failed to stop Pathling server: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@analytics.command("load")
@click.option("--input-dir", "-i", type=str, required=True, help="Directory containing FHIR resources in NDJSON format")
@click.option("--resource-type", "-r", type=str, required=True, help="FHIR resource type to load")
@click.option("--server-url", "-s", type=str, default="http://localhost:8080/fhir", help="Pathling server URL")
def load_resources(input_dir: str, resource_type: str, server_url: str):
    """Load FHIR resources into the Pathling server from NDJSON files."""
    try:
        service = PathlingService(base_url=server_url)
        
        # Get all NDJSON files in the input directory
        input_path = Path(input_dir)
        if not input_path.exists():
            click.echo(f"Error: Input directory '{input_dir}' does not exist", err=True)
            sys.exit(1)
            
        ndjson_files = list(input_path.glob("*.ndjson"))
        if not ndjson_files:
            click.echo(f"Warning: No NDJSON files found in '{input_dir}'", err=True)
            sys.exit(1)
        
        # Process each file
        for file_path in ndjson_files:
            click.echo(f"Loading {file_path}...")
            
            # Read resources from the file
            resources = []
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        resources.append(json.loads(line))
            
            # Load resources into Pathling
            if resources:
                success = service.load_resources(resources, resource_type)
                if success:
                    click.echo(f"Successfully loaded {len(resources)} resources from {file_path}")
                else:
                    click.echo(f"Failed to load resources from {file_path}", err=True)
            
        click.echo(f"Completed loading {resource_type} resources")
        
    except Exception as e:
        logger.error(f"Failed to load resources: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@analytics.command("aggregate")
@click.option("--resource-type", "-r", type=str, required=True, help="FHIR resource type to aggregate")
@click.option("--aggregation", "-a", type=str, multiple=True, required=True, help="Aggregation expressions")
@click.option("--grouping", "-g", type=str, multiple=True, help="Grouping expressions")
@click.option("--filter", "-f", type=str, multiple=True, help="Filter expressions")
@click.option("--output", "-o", type=str, help="Output file path (CSV format)")
@click.option("--server-url", "-s", type=str, default="http://localhost:8080/fhir", help="Pathling server URL")
def aggregate_resources(resource_type: str, aggregation: List[str], grouping: List[str], 
                        filter: List[str], output: Optional[str], server_url: str):
    """Perform aggregation analytics on FHIR resources."""
    try:
        service = PathlingService(base_url=server_url)
        
        # Execute aggregation
        results = service.aggregate(
            resource_type=resource_type,
            aggregations=aggregation,
            grouping=grouping if grouping else None,
            filters=filter if filter else None
        )
        
        # Display results
        if results.empty:
            click.echo("No results returned from aggregation")
            return
            
        # Format results for display
        click.echo("\nAggregation Results:")
        click.echo(results.to_string(index=False))
        
        # Save results to file if specified
        if output:
            results.to_csv(output, index=False)
            click.echo(f"\nResults saved to {output}")
            
    except Exception as e:
        logger.error(f"Failed to execute aggregation: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@analytics.command("extract")
@click.option("--resource-type", "-r", type=str, required=True, help="FHIR resource type to extract from")
@click.option("--column", "-c", type=str, multiple=True, required=True, help="Column expressions")
@click.option("--filter", "-f", type=str, multiple=True, help="Filter expressions")
@click.option("--output", "-o", type=str, help="Output file path (CSV format)")
@click.option("--server-url", "-s", type=str, default="http://localhost:8080/fhir", help="Pathling server URL")
def extract_dataset(resource_type: str, column: List[str], filter: List[str], 
                    output: Optional[str], server_url: str):
    """Extract a dataset from FHIR resources."""
    try:
        service = PathlingService(base_url=server_url)
        
        # Execute extraction
        results = service.extract_dataset(
            resource_type=resource_type,
            columns=column,
            filters=filter if filter else None
        )
        
        # Display results
        if results.empty:
            click.echo("No results returned from extraction")
            return
            
        # Format results for display (limit to first 10 rows)
        click.echo("\nExtraction Results (first 10 rows):")
        click.echo(results.head(10).to_string(index=False))
        click.echo(f"\nTotal rows: {len(results)}")
        
        # Save results to file if specified
        if output:
            results.to_csv(output, index=False)
            click.echo(f"\nResults saved to {output}")
            
    except Exception as e:
        logger.error(f"Failed to execute extraction: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@analytics.command("measure")
@click.option("--measure-path", "-m", type=str, required=True, help="Path to FHIR Measure resource JSON file")
@click.option("--output", "-o", type=str, help="Output file path (JSON format)")
@click.option("--server-url", "-s", type=str, default="http://localhost:8080/fhir", help="Pathling server URL")
def execute_measure(measure_path: str, output: Optional[str], server_url: str):
    """Execute a FHIR Measure against the loaded resources."""
    try:
        service = PathlingService(base_url=server_url)
        
        # Check if measure file exists
        if not os.path.exists(measure_path):
            click.echo(f"Error: Measure file '{measure_path}' does not exist", err=True)
            sys.exit(1)
        
        # Execute measure
        results = service.execute_measure(measure_path)
        
        # Display results
        if not results:
            click.echo("No results returned from measure execution")
            return
            
        # Format results for display
        click.echo("\nMeasure Evaluation Results:")
        click.echo(json.dumps(results, indent=2))
        
        # Save results to file if specified
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            click.echo(f"\nResults saved to {output}")
            
    except Exception as e:
        logger.error(f"Failed to execute measure: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    analytics() 