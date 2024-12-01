"""
CLI commands for FHIR data science.

This module provides CLI commands for creating datasets from FHIR resources
using FHIR-PYrate and other data science tools.
"""

import os
import json
import logging
import click
from typing import List, Optional, Dict
import pandas as pd

from ..datascience import FHIRDatasetBuilder, CohortBuilder

logger = logging.getLogger(__name__)

@click.group()
def datascience():
    """Commands for FHIR data science tasks."""
    pass

@datascience.command('create-dataset')
@click.argument('input_files', type=click.Path(exists=True), nargs=-1)
@click.option('--config', '-c', type=click.Path(exists=True), help='Dataset configuration file (JSON)')
@click.option('--output', '-o', help='Output file for dataset (CSV)')
@click.option('--resource-type', '-r', multiple=True, 
             help='Resource type for each input file (format: type:file)')
@click.option('--column', multiple=True, 
             help='Column to extract (format: name:type:fhirpath[:default])')
def create_dataset(input_files: List[str], config: Optional[str] = None,
                  output: Optional[str] = None, resource_type: Optional[List[str]] = None,
                  column: Optional[List[str]] = None):
    """
    Create a dataset from FHIR resources.
    
    INPUT_FILES are the paths to NDJSON files containing FHIR resources.
    """
    try:
        # Initialize the dataset builder
        builder = FHIRDatasetBuilder()
        
        # Load configuration from file if provided
        if config:
            with open(config, 'r') as f:
                config_data = json.load(f)
                
            # Process resource types from config
            if 'resource_types' in config_data:
                for rt_config in config_data['resource_types']:
                    rt_type = rt_config['type']
                    rt_file = rt_config['file']
                    
                    # Load resources
                    resources = []
                    with open(rt_file, 'r') as f:
                        for line in f:
                            resources.append(json.loads(line))
                            
                    click.echo(f"Loaded {len(resources)} {rt_type} resources from {rt_file}")
                    builder.add_resources(rt_type, resources)
                    
            # Process columns from config
            if 'columns' in config_data:
                for col_config in config_data['columns']:
                    builder.add_column(
                        name=col_config['name'],
                        resource_type=col_config['resource_type'],
                        fhirpath=col_config['fhirpath'],
                        default_value=col_config.get('default_value')
                    )
                    
            # Process index column
            if 'index_column' in config_data:
                builder.set_index(config_data['index_column'])
                
            # Process point-in-time analysis
            if 'point_in_time' in config_data and config_data['point_in_time'].get('enabled', False):
                pit_config = config_data['point_in_time']
                builder.use_point_in_time_analysis(
                    reference_date=pit_config.get('reference_date'),
                    reference_column=pit_config.get('reference_column')
                )
        else:
            # Process resource types from command line
            for rt in resource_type or []:
                rt_parts = rt.split(':', 1)
                if len(rt_parts) != 2:
                    click.secho(f"Invalid resource type format: {rt}", fg='red')
                    continue
                    
                rt_type, rt_file = rt_parts
                
                # Find the corresponding input file
                if rt_file not in input_files:
                    click.secho(f"File not found: {rt_file}", fg='red')
                    continue
                    
                # Load resources
                resources = []
                with open(rt_file, 'r') as f:
                    for line in f:
                        resources.append(json.loads(line))
                        
                click.echo(f"Loaded {len(resources)} {rt_type} resources from {rt_file}")
                builder.add_resources(rt_type, resources)
                
            # Process columns from command line
            for col in column or []:
                col_parts = col.split(':')
                if len(col_parts) < 3:
                    click.secho(f"Invalid column format: {col}", fg='red')
                    continue
                    
                col_name = col_parts[0]
                col_type = col_parts[1]
                col_path = col_parts[2]
                col_default = None if len(col_parts) < 4 else col_parts[3]
                
                builder.add_column(
                    name=col_name,
                    resource_type=col_type,
                    fhirpath=col_path,
                    default_value=col_default
                )
        
        # Build the dataset
        dataset = builder.build()
        
        # Print the dataset
        click.echo(dataset.dataframe.head())
        
        # Write output if specified
        if output:
            if output.endswith('.csv'):
                dataset.to_csv(output)
            elif output.endswith('.parquet'):
                dataset.to_parquet(output)
            else:
                dataset.to_csv(output)
                
            click.secho(f"Dataset written to {output}", fg='green')
            
        return True
                
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False
    
@datascience.command('create-cohort')
@click.argument('patients_file', type=click.Path(exists=True))
@click.option('--resource-file', '-r', multiple=True, 
             help='Additional resource file (format: type:file)')
@click.option('--criterion', '-c', multiple=True, 
             help='Criterion for cohort inclusion (format: name:code[:system])')
@click.option('--output', '-o', help='Output file for cohort (CSV, JSON)')
def create_cohort(patients_file: str, resource_file: Optional[List[str]] = None,
                 criterion: Optional[List[str]] = None, output: Optional[str] = None):
    """
    Create a patient cohort from FHIR resources.
    
    PATIENTS_FILE is the path to a NDJSON file containing Patient resources.
    """
    try:
        # Load patients
        patients = []
        with open(patients_file, 'r') as f:
            for line in f:
                patients.append(json.loads(line))
                
        click.echo(f"Loaded {len(patients)} Patient resources")
        
        # Load additional resources
        resources = {}
        for rf in resource_file or []:
            rf_parts = rf.split(':', 1)
            if len(rf_parts) != 2:
                click.secho(f"Invalid resource file format: {rf}", fg='red')
                continue
                
            rf_type, rf_file = rf_parts
            
            # Load resources
            resources[rf_type] = []
            with open(rf_file, 'r') as f:
                for line in f:
                    resources[rf_type].append(json.loads(line))
                    
            click.echo(f"Loaded {len(resources[rf_type])} {rf_type} resources")
        
        # Initialize the cohort builder
        builder = CohortBuilder(patients, resources)
        
        # Add criteria
        for crit in criterion or []:
            crit_parts = crit.split(':')
            if len(crit_parts) < 2:
                click.secho(f"Invalid criterion format: {crit}", fg='red')
                continue
                
            crit_name = crit_parts[0]
            crit_code = crit_parts[1]
            crit_system = None if len(crit_parts) < 3 else crit_parts[2]
            
            # Add criterion based on observations
            builder.add_observation_criteria(crit_name, crit_code, crit_system)
        
        # Build the cohort
        cohort = builder.build()
        
        click.echo(f"Cohort includes {len(cohort)} patients")
        
        # Convert to dataframe
        df = builder.to_dataframe()
        
        # Write output if specified
        if output:
            if output.endswith('.csv'):
                df.to_csv(output, index=False)
            elif output.endswith('.json'):
                with open(output, 'w') as f:
                    json.dump([p for p in cohort], f, indent=2)
            else:
                df.to_csv(output, index=False)
                
            click.secho(f"Cohort written to {output}", fg='green')
            
        return True
                
    except Exception as e:
        logger.error(f"Error creating cohort: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False 