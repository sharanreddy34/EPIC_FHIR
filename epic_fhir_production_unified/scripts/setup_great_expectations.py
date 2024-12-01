#!/usr/bin/env python3
"""
Setup script for Great Expectations.

This script sets up Great Expectations for data quality monitoring of FHIR data.
It creates a Great Expectations directory, configures datasources, and creates
basic expectation suites for FHIR data.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ge_installation() -> bool:
    """
    Check if Great Expectations is installed.
    
    Returns:
        True if Great Expectations is installed, False otherwise
    """
    try:
        import great_expectations
        logger.info(f"Great Expectations version {great_expectations.__version__} is installed")
        return True
    except ImportError:
        logger.error("Great Expectations is not installed")
        return False

def install_great_expectations() -> bool:
    """
    Install Great Expectations and required dependencies.
    
    Returns:
        True if installation was successful, False otherwise
    """
    try:
        logger.info("Installing Great Expectations...")
        
        # Install Great Expectations with required dependencies for this project
        packages = [
            "great-expectations",
            "pandas",
            "sqlalchemy",
            "pyspark",
        ]
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Great Expectations installed successfully")
        return True
        
    except subprocess.SubprocessError as e:
        logger.error(f"Error installing Great Expectations: {e}")
        logger.error(f"Stdout: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        logger.error(f"Stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        return False

def init_ge_project(project_dir: Path) -> bool:
    """
    Initialize a Great Expectations project.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        logger.info(f"Initializing Great Expectations project in {project_dir}")
        
        # Import Great Expectations
        import great_expectations as ge
        from great_expectations.data_context.types.base import DataContextConfig
        from great_expectations.data_context import BaseDataContext
        
        # Create GE project directory
        ge_dir = project_dir / "great_expectations"
        ge_dir.mkdir(parents=True, exist_ok=True)
        
        # Create basic configuration
        config = DataContextConfig(
            config_version=3.0,
            plugins_directory=str(ge_dir / "plugins"),
            evaluation_parameter_store_name="evaluation_parameter_store",
            expectations_store_name="expectations_store",
            validations_store_name="validations_store",
            checkpoint_store_name="checkpoint_store",
            store_backend_defaults=None,
            stores={
                "expectations_store": {
                    "class_name": "ExpectationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": str(ge_dir / "expectations"),
                    }
                },
                "validations_store": {
                    "class_name": "ValidationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": str(ge_dir / "validations"),
                    }
                },
                "evaluation_parameter_store": {
                    "class_name": "EvaluationParameterStore"
                },
                "checkpoint_store": {
                    "class_name": "CheckpointStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": str(ge_dir / "checkpoints"),
                    }
                },
            },
            data_docs_sites={
                "local_site": {
                    "class_name": "SiteBuilder",
                    "show_how_to_buttons": True,
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": str(ge_dir / "data_docs"),
                    },
                    "site_index_builder": {
                        "class_name": "DefaultSiteIndexBuilder",
                    }
                }
            },
            anonymous_usage_statistics={
                "enabled": False
            }
        )
        
        # Write the config to disk
        with open(ge_dir / "great_expectations.yml", "w") as f:
            f.write(config.to_yaml_str())
        
        # Create directories
        for dir_name in ["expectations", "validations", "checkpoints", "plugins", "data_docs"]:
            (ge_dir / dir_name).mkdir(exist_ok=True)
        
        logger.info("Great Expectations project initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Great Expectations project: {e}")
        return False

def add_filesystem_datasource(
    project_dir: Path,
    datasource_name: str,
    data_dir: Path,
    data_type: str = "parquet"
) -> bool:
    """
    Add a filesystem datasource to the Great Expectations project.
    
    Args:
        project_dir: Path to the project directory
        datasource_name: Name of the datasource to add
        data_dir: Path to the data directory
        data_type: Type of data (csv, parquet, etc.)
        
    Returns:
        True if datasource was added successfully, False otherwise
    """
    try:
        logger.info(f"Adding {datasource_name} datasource for {data_type} files in {data_dir}")
        
        # Import Great Expectations
        import great_expectations as ge
        from great_expectations.data_context import DataContext
        
        # Load the context
        context = DataContext(str(project_dir / "great_expectations"))
        
        # Define datasource config
        if data_type.lower() == "parquet":
            datasource_config = {
                "name": datasource_name,
                "class_name": "Datasource",
                "execution_engine": {
                    "class_name": "PandasExecutionEngine"
                },
                "data_connectors": {
                    "default_inferred_data_connector_name": {
                        "class_name": "InferredAssetFilesystemDataConnector",
                        "base_directory": str(data_dir),
                        "default_regex": {
                            "group_names": ["data_asset_name"],
                            "pattern": "(.*)\\.parquet"
                        }
                    }
                }
            }
        elif data_type.lower() == "csv":
            datasource_config = {
                "name": datasource_name,
                "class_name": "Datasource",
                "execution_engine": {
                    "class_name": "PandasExecutionEngine"
                },
                "data_connectors": {
                    "default_inferred_data_connector_name": {
                        "class_name": "InferredAssetFilesystemDataConnector",
                        "base_directory": str(data_dir),
                        "default_regex": {
                            "group_names": ["data_asset_name"],
                            "pattern": "(.*)\\.csv"
                        }
                    }
                }
            }
        else:
            logger.error(f"Unsupported data type: {data_type}")
            return False
        
        # Add the datasource
        context.add_datasource(**datasource_config)
        
        logger.info(f"Datasource {datasource_name} added successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error adding datasource: {e}")
        return False

def create_fhir_expectation_suite(
    project_dir: Path,
    suite_name: str,
    resource_type: str = "Patient"
) -> bool:
    """
    Create an expectation suite for FHIR data.
    
    Args:
        project_dir: Path to the project directory
        suite_name: Name of the expectation suite
        resource_type: FHIR resource type (Patient, Observation, etc.)
        
    Returns:
        True if expectation suite was created successfully, False otherwise
    """
    try:
        logger.info(f"Creating expectation suite {suite_name} for {resource_type} resources")
        
        # Import Great Expectations
        import great_expectations as ge
        from great_expectations.data_context import DataContext
        from great_expectations.core.expectation_suite import ExpectationSuite
        from great_expectations.core.expectation_configuration import ExpectationConfiguration
        
        # Load the context
        context = DataContext(str(project_dir / "great_expectations"))
        
        # Create a new empty suite
        suite = ExpectationSuite(expectation_suite_name=suite_name)
        
        # Add common FHIR resource expectations
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_to_exist",
                kwargs={"column": "resourceType"}
            )
        )
        
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": "resourceType"}
            )
        )
        
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_in_set",
                kwargs={"column": "resourceType", "value_set": [resource_type]}
            )
        )
        
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_to_exist",
                kwargs={"column": "id"}
            )
        )
        
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": "id"}
            )
        )
        
        # Add resource-specific expectations
        if resource_type == "Patient":
            # For Patient resources
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_to_exist",
                    kwargs={"column": "gender"}
                )
            )
            
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_be_in_set",
                    kwargs={"column": "gender", "value_set": ["male", "female", "other", "unknown"]}
                )
            )
            
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_to_exist",
                    kwargs={"column": "birthDate"}
                )
            )
            
        elif resource_type == "Observation":
            # For Observation resources
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_to_exist",
                    kwargs={"column": "status"}
                )
            )
            
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_be_in_set",
                    kwargs={"column": "status", "value_set": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"]}
                )
            )
            
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_to_exist",
                    kwargs={"column": "code"}
                )
            )
            
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_to_exist",
                    kwargs={"column": "subject"}
                )
            )
            
        # Save the suite
        context.save_expectation_suite(expectation_suite=suite)
        
        logger.info(f"Expectation suite {suite_name} created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating expectation suite: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up Great Expectations for FHIR data")
    parser.add_argument(
        "--project-dir", 
        help="Project directory", 
        default="."
    )
    parser.add_argument(
        "--data-dir", 
        help="Data directory", 
        default="output"
    )
    parser.add_argument(
        "--resources", 
        nargs="+", 
        help="FHIR resource types to create expectation suites for",
        default=["Patient", "Observation", "Encounter"]
    )
    parser.add_argument(
        "--install", 
        action="store_true", 
        help="Install Great Expectations if not already installed"
    )
    
    args = parser.parse_args()
    
    # Convert paths to absolute paths
    project_dir = Path(args.project_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    
    # Check if Great Expectations is installed
    if not check_ge_installation():
        if args.install:
            if not install_great_expectations():
                logger.error("Failed to install Great Expectations. Exiting.")
                sys.exit(1)
        else:
            logger.error("Great Expectations is not installed. Use --install to install it.")
            sys.exit(1)
    
    # Initialize Great Expectations project
    if not init_ge_project(project_dir):
        logger.error("Failed to initialize Great Expectations project. Exiting.")
        sys.exit(1)
    
    # Add datasources for Bronze, Silver, and Gold layers
    for layer in ["bronze", "silver", "gold"]:
        layer_dir = data_dir / layer
        if layer_dir.exists():
            data_type = "parquet" if layer in ["silver", "gold"] else "json"
            if not add_filesystem_datasource(project_dir, f"{layer}_datasource", layer_dir, data_type):
                logger.warning(f"Failed to add {layer} datasource.")
    
    # Create expectation suites for each resource type
    for resource_type in args.resources:
        suite_name = f"{resource_type.lower()}_suite"
        if not create_fhir_expectation_suite(project_dir, suite_name, resource_type):
            logger.warning(f"Failed to create expectation suite for {resource_type}.")
    
    logger.info("Great Expectations setup completed successfully")
    logger.info(f"Great Expectations project directory: {project_dir / 'great_expectations'}")
    logger.info("To generate data docs: great_expectations docs build")

if __name__ == "__main__":
    main() 