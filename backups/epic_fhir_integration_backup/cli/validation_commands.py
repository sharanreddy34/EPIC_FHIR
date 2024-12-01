"""
CLI commands for FHIR validation.

This module provides CLI commands for validating FHIR resources using
HAPI FHIR Validator and FHIR Shorthand profiles.
"""

import os
import json
import logging
import click
from typing import List, Optional

from ..validation import FHIRValidator, ValidationResult

logger = logging.getLogger(__name__)

@click.group()
def validate():
    """Commands for validating FHIR resources."""
    pass

@validate.command('resource')
@click.argument('resource_path', type=click.Path(exists=True))
@click.option('--profile', '-p', help='Path to FHIR profile or IG directory')
@click.option('--fhir-version', default='R4', help='FHIR version to validate against')
@click.option('--output', '-o', help='Output file for validation results')
def validate_resource(resource_path: str, profile: Optional[str] = None, 
                     fhir_version: str = 'R4', output: Optional[str] = None):
    """
    Validate a FHIR resource against profiles.
    
    RESOURCE_PATH is the path to the FHIR resource JSON file.
    """
    try:
        # Initialize the validator
        validator = FHIRValidator(
            ig_directory=profile,
            fhir_version=fhir_version
        )
        
        # Read the resource
        with open(resource_path, 'r') as f:
            resource = json.load(f)
            
        # Validate the resource
        result = validator.validate(resource)
        
        # Print the results
        if result.is_valid:
            click.secho(f"Resource is valid", fg='green')
        else:
            click.secho(f"Resource is invalid - {len(result.get_errors())} errors", fg='red')
            
        if result.has_warnings():
            click.secho(f"Warnings: {len(result.get_warnings())}", fg='yellow')
            
        # Print errors and warnings
        for error in result.get_errors():
            click.secho(f"Error: {error.get('message')}", fg='red')
            
        for warning in result.get_warnings():
            click.secho(f"Warning: {warning.get('message')}", fg='yellow')
            
        # Write output if specified
        if output:
            with open(output, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
                
        return result.is_valid
                
    except Exception as e:
        logger.error(f"Error validating resource: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False

@validate.command('batch')
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--profile', '-p', help='Path to FHIR profile or IG directory')
@click.option('--fhir-version', default='R4', help='FHIR version to validate against')
@click.option('--output', '-o', help='Output directory for validation results')
@click.option('--pattern', default='*.json', help='File pattern to match')
def validate_batch(directory: str, profile: Optional[str] = None,
                  fhir_version: str = 'R4', output: Optional[str] = None,
                  pattern: str = '*.json'):
    """
    Validate multiple FHIR resources against profiles.
    
    DIRECTORY is the path to a directory containing FHIR resource JSON files.
    """
    try:
        import glob
        from pathlib import Path
        
        # Initialize the validator
        validator = FHIRValidator(
            ig_directory=profile,
            fhir_version=fhir_version
        )
        
        # Find all matching files
        files = glob.glob(os.path.join(directory, pattern))
        
        if not files:
            click.secho(f"No files matching pattern '{pattern}' found in {directory}", fg='yellow')
            return True
            
        click.echo(f"Found {len(files)} files to validate")
        
        # Create output directory if needed
        if output:
            os.makedirs(output, exist_ok=True)
            
        # Validate each file
        valid_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    resource = json.load(f)
                    
                # Validate the resource
                result = validator.validate(resource)
                
                # Check validity
                if result.is_valid:
                    valid_count += 1
                else:
                    error_count += 1
                    click.secho(f"Invalid: {file_path} - {len(result.get_errors())} errors", fg='red')
                    
                # Write output if specified
                if output:
                    file_name = os.path.basename(file_path)
                    output_path = os.path.join(output, f"{file_name}.validation.json")
                    with open(output_path, 'w') as f:
                        json.dump(result.to_dict(), f, indent=2)
                        
            except Exception as e:
                error_count += 1
                click.secho(f"Error validating {file_path}: {str(e)}", fg='red')
                
        # Print summary
        click.secho(f"Validation complete: {valid_count} valid, {error_count} invalid", 
                   fg='green' if error_count == 0 else 'red')
                
        return error_count == 0
                
    except Exception as e:
        logger.error(f"Error validating batch: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False

@validate.command('compile')
@click.argument('fsh_directory', type=click.Path(exists=True, file_okay=False))
@click.option('--output', '-o', help='Output directory for compiled resources')
def compile_fsh(fsh_directory: str, output: Optional[str] = None):
    """
    Compile FHIR Shorthand (FSH) files to FHIR resources.
    
    FSH_DIRECTORY is the path to a directory containing FSH files.
    """
    try:
        # Initialize the validator
        validator = FHIRValidator()
        
        # Compile FSH files
        output_dir = validator.compile_fsh(fsh_directory, output)
        
        click.secho(f"FSH files compiled successfully to {output_dir}", fg='green')
        return True
                
    except Exception as e:
        logger.error(f"Error compiling FSH files: {e}")
        click.secho(f"Error: {str(e)}", fg='red')
        return False 