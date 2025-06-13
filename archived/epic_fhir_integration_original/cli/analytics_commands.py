"""
CLI commands for FHIR analytics.

This module provides CLI commands for performing analytics on FHIR resources
using Pathling and other advanced FHIR analytics tools.
"""

import os
import json
import logging
import click
from typing import List, Optional

import pandas as pd

from ..analytics import PathlingService

logger = logging.getLogger(__name__)

@click.group()
def analytics():
    """Commands for analyzing FHIR resources."""
    pass

@analytics.command('aggregate')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--resource-type', '-r', required=True, help='Resource type to aggregate')
@click.option('--aggregation', '-a', multiple=True, required=True, help='Aggregation expression')
@click.option('--grouping', '-g', multiple=True, help='Grouping expression')
@click.option('--filter', '-f', multiple=True, help='Filter expression')
@click.option('--output', '-o', help='Output file for results (CSV)')
def aggregate_command(input_file: str, resource_type: str, aggregation: List[str],
                     grouping: Optional[List[str]] = None, filter: Optional[List[str]] = None,
                     output: Optional[str] = None):
    """
    Perform aggregation analytics on FHIR resources.
    
    INPUT_FILE is the path to a NDJSON file containing FHIR resources.
    """
    try:
        # Initialize the Pathling service
        service = PathlingService()
        
        # Read the resources
        resources = []
        with open(input_file, 'r') as f:
            for line in f:
                resources.append(json.loads(line))
                
        click.echo(f"Loaded {len(resources)} resources")
        
        # Load the resources into Pathling
        service.load_resources(resources, resource_type)
        
        # Perform the aggregation
        result = service.aggregate(
            resource_type=resource_type,
            aggregations=list(aggregation),
            filters=list(filter) if filter else None,
            groupings=list(grouping) if grouping else None
        )
        
        # Print the results
        click.echo(result)
        
        # Write output if specified
        if output:
            result.to_csv(output, index=False)
            click.secho(f"Results written to {output}", fg='green')
            
        return True
                
    except Exception as e:
        logger.error(f"Error performing aggregation: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False

@analytics.command('extract')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--resource-type', '-r', required=True, help='Resource type to extract from')
@click.option('--column', '-c', multiple=True, required=True, help='Column expression')
@click.option('--filter', '-f', multiple=True, help='Filter expression')
@click.option('--output', '-o', help='Output file for results (CSV)')
def extract_command(input_file: str, resource_type: str, column: List[str],
                   filter: Optional[List[str]] = None, output: Optional[str] = None):
    """
    Extract a dataset from FHIR resources.
    
    INPUT_FILE is the path to a NDJSON file containing FHIR resources.
    """
    try:
        # Initialize the Pathling service
        service = PathlingService()
        
        # Read the resources
        resources = []
        with open(input_file, 'r') as f:
            for line in f:
                resources.append(json.loads(line))
                
        click.echo(f"Loaded {len(resources)} resources")
        
        # Load the resources into Pathling
        service.load_resources(resources, resource_type)
        
        # Extract the dataset
        result = service.extract_dataset(
            resource_type=resource_type,
            columns=list(column),
            filters=list(filter) if filter else None
        )
        
        # Print the results
        click.echo(result)
        
        # Write output if specified
        if output:
            result.to_csv(output, index=False)
            click.secho(f"Results written to {output}", fg='green')
            
        return True
                
    except Exception as e:
        logger.error(f"Error extracting dataset: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False

@analytics.command('measure')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--resource-type', '-r', required=True, help='Resource type to measure')
@click.option('--population', '-p', multiple=True, required=True, 
             help='Population name and filter expression (name=expression)')
@click.option('--stratifier', '-s', multiple=True, help='Stratification expression')
@click.option('--output', '-o', help='Output file for results (JSON)')
def measure_command(input_file: str, resource_type: str, population: List[str],
                   stratifier: Optional[List[str]] = None, output: Optional[str] = None):
    """
    Calculate a measure on FHIR resources.
    
    INPUT_FILE is the path to a NDJSON file containing FHIR resources.
    """
    try:
        # Initialize the Pathling service
        service = PathlingService()
        
        # Read the resources
        resources = []
        with open(input_file, 'r') as f:
            for line in f:
                resources.append(json.loads(line))
                
        click.echo(f"Loaded {len(resources)} resources")
        
        # Load the resources into Pathling
        service.load_resources(resources, resource_type)
        
        # Parse population definitions
        populations = {}
        for pop in population:
            name, expr = pop.split('=', 1)
            populations[name] = expr
            
        # Calculate the measure
        result = service.calculate_measure(
            resource_type=resource_type,
            population_filters=populations,
            stratifiers=list(stratifier) if stratifier else None
        )
        
        # Print the results
        click.echo(json.dumps(result, indent=2))
        
        # Write output if specified
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            click.secho(f"Results written to {output}", fg='green')
            
        return True
                
    except Exception as e:
        logger.error(f"Error calculating measure: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False 