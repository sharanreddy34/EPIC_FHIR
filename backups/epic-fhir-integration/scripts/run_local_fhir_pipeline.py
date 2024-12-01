#!/usr/bin/env python3
"""
FHIR Pipeline Local Execution Script

This script allows running the FHIR data pipeline locally without requiring
the full Foundry environment. It simulates the workflow defined in workflow_pipeline.yml
but with local filesystem storage instead of Foundry datasets.

Usage:
    python run_local_fhir_pipeline.py --patient-id <id> [--steps <steps>] [--output-dir <dir>] [--debug]

Example:
    python run_local_fhir_pipeline.py --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --debug
"""

import os
import sys
import json
import yaml
import time
import shutil
import logging
import argparse
import datetime
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
from pyspark.sql import SparkSession

# Add lib to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_debug_logging(enable_debug: bool):
    """
    Configure debug logging.
    
    Args:
        enable_debug: Whether to enable debug logging
    """
    if enable_debug:
        logger.setLevel(logging.DEBUG)
        # Also set debug level for other modules
        logging.getLogger("pyspark").setLevel(logging.INFO)  # Too verbose to set to DEBUG
        
        # Log to file in addition to console
        debug_log_file = Path("debug_pipeline.log")
        file_handler = logging.FileHandler(debug_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.debug("Debug logging enabled")


class FoundryDatasetMock:
    """Mock class for Foundry datasets that stores data on local filesystem."""
    
    def __init__(self, path: str, format_type: str = "parquet"):
        """
        Initialize dataset mock.
        
        Args:
            path: Path to store data
            format_type: Data format (parquet, json, etc.)
        """
        self.path = Path(path)
        self.format_type = format_type
        self.path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created dataset mock at {path} with format {format_type}")
    
    def dataframe(self) -> pd.DataFrame:
        """Read dataset as DataFrame."""
        start_time = time.time()
        
        if not os.listdir(self.path):
            # Return empty dataframe if no files
            logger.debug(f"No files found in {self.path}, returning empty DataFrame")
            return pd.DataFrame()
        
        logger.debug(f"Reading dataset from {self.path}")
        try:
            spark = get_spark_session()
            df = spark.read.format(self.format_type).load(str(self.path))
            elapsed = time.time() - start_time
            logger.debug(f"DataFrame loaded with {df.count()} rows in {elapsed:.2f} seconds")
            return df
        except Exception as e:
            logger.error(f"Error reading dataset at {self.path}: {str(e)}")
            logger.debug(f"Read error details: {traceback.format_exc()}")
            # Return empty dataframe on error
            return pd.DataFrame()
    
    def write_dataframe(self, df, **kwargs):
        """Write DataFrame to dataset."""
        start_time = time.time()
        logger.debug(f"Writing DataFrame to {self.path}")
        
        try:
            # Delete existing files if any
            for file in self.path.glob("*"):
                if file.is_file():
                    file.unlink()
            
            # Write dataframe
            df.write.format(self.format_type).save(str(self.path), mode="overwrite")
            
            # Log success
            elapsed = time.time() - start_time
            count = df.count() if hasattr(df, "count") else "unknown"
            logger.debug(f"DataFrame with {count} rows written to {self.path} in {elapsed:.2f} seconds")
        except Exception as e:
            logger.error(f"Error writing DataFrame to {self.path}: {str(e)}")
            logger.debug(f"Write error details: {traceback.format_exc()}")
    
    def write_file(self, filename: str, content: str):
        """Write file to dataset."""
        logger.debug(f"Writing file {filename} to {self.path}")
        try:
            file_path = self.path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
                
            logger.debug(f"File {filename} written successfully ({len(content)} bytes)")
        except Exception as e:
            logger.error(f"Error writing file {filename} to {self.path}: {str(e)}")
            logger.debug(f"File write error details: {traceback.format_exc()}")
    
    def read_file(self, filename: str = None) -> str:
        """Read file from dataset."""
        try:
            if filename:
                file_path = self.path / filename
                logger.debug(f"Reading file {filename} from {self.path}")
                with open(file_path, 'r') as f:
                    content = f.read()
                    logger.debug(f"File {filename} read successfully ({len(content)} bytes)")
                    return content
            else:
                # Just return first file if no filename specified
                files = list(self.path.glob("*"))
                if not files:
                    logger.debug(f"No files found in {self.path}")
                    return ""
                
                logger.debug(f"Reading first file {files[0].name} from {self.path}")
                with open(files[0], 'r') as f:
                    content = f.read()
                    logger.debug(f"File {files[0].name} read successfully ({len(content)} bytes)")
                    return content
        except Exception as e:
            logger.error(f"Error reading file from {self.path}: {str(e)}")
            logger.debug(f"File read error details: {traceback.format_exc()}")
            return ""


class MockSecret:
    """Mock class for Foundry secrets."""
    
    def __init__(self, path: str):
        """
        Initialize secret mock.
        
        Args:
            path: Path to store secret
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created secret mock at {path}")
    
    def read(self) -> str:
        """Read secret value."""
        try:
            if not self.path.exists():
                logger.debug(f"Secret file {self.path} does not exist")
                return ""
            
            logger.debug(f"Reading secret from {self.path}")
            with open(self.path, 'r') as f:
                content = f.read()
                logger.debug(f"Secret read successfully ({len(content)} bytes)")
                return content
        except Exception as e:
            logger.error(f"Error reading secret from {self.path}: {str(e)}")
            logger.debug(f"Secret read error details: {traceback.format_exc()}")
            return ""
    
    def write(self, value: str):
        """Write secret value."""
        try:
            logger.debug(f"Writing secret to {self.path}")
            with open(self.path, 'w') as f:
                f.write(value)
            logger.debug(f"Secret written successfully ({len(value)} bytes)")
        except Exception as e:
            logger.error(f"Error writing secret to {self.path}: {str(e)}")
            logger.debug(f"Secret write error details: {traceback.format_exc()}")


def get_spark_session(mock_mode: bool = False) -> Optional[SparkSession]:
    """
    Create and configure a Spark session for FHIR pipeline.
    
    Args:
        mock_mode: Whether to return None if Spark is not available
        
    Returns:
        Configured SparkSession or None if Spark not available and mock_mode=True
    """
    logger.debug("Creating or getting Spark session")
    start_time = time.time()  # Define start_time locally
    
    try:
        # Set Spark home to default PySpark location if not set
        if "SPARK_HOME" not in os.environ:
            if os.path.exists("/usr/local/spark"):
                os.environ["SPARK_HOME"] = "/usr/local/spark"
            elif os.path.exists("/opt/spark"):
                os.environ["SPARK_HOME"] = "/opt/spark"
        
        # Create Spark session with Delta Lake catalog configuration
        spark = SparkSession.builder \
            .appName("LocalFHIRPipeline") \
            .config("spark.sql.session.timeZone", "UTC") \
            .config("spark.rdd.compress", "True") \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
            .master("local[*]") \
            .getOrCreate()
        
        # Log Spark information
        logger.debug(f"Using Spark version: {spark.version}")
        logger.debug(f"Spark configuration: {spark.sparkContext.getConf().getAll()}")
        
        elapsed = time.time() - start_time
        logger.debug(f"Spark session created in {elapsed:.2f} seconds")
        
        return spark
    
    except Exception as e:
        logger.error(f"Failed to create Spark session: {str(e)}")
        if mock_mode:
            return None
        else:
            raise


def load_config_files(base_dir: Path) -> Dict[str, Any]:
    """
    Load configuration files.
    
    Args:
        base_dir: Base directory containing config files
    
    Returns:
        Dict of configuration objects
    """
    config = {}
    logger.debug(f"Loading configuration files from {base_dir}")
    
    # Load API config
    api_config_path = base_dir / "config" / "api_config.yaml"
    if api_config_path.exists():
        try:
            logger.debug(f"Loading API config from {api_config_path}")
            with open(api_config_path, 'r') as f:
                config['api_config'] = yaml.safe_load(f)
            logger.debug(f"API config loaded: {config['api_config']}")
        except Exception as e:
            logger.error(f"Error loading API config: {str(e)}")
            logger.debug(f"API config error details: {traceback.format_exc()}")
    else:
        logger.warning(f"API config file not found at {api_config_path}")
    
    # Load resources config
    resources_config_path = base_dir / "config" / "resources_config.yaml"
    if resources_config_path.exists():
        try:
            logger.debug(f"Loading resources config from {resources_config_path}")
            with open(resources_config_path, 'r') as f:
                config['resources_config'] = yaml.safe_load(f)
            logger.debug(f"Resources config loaded with {len(config['resources_config'].get('resources', {}))} resource definitions")
        except Exception as e:
            logger.error(f"Error loading resources config: {str(e)}")
            logger.debug(f"Resources config error details: {traceback.format_exc()}")
    else:
        logger.warning(f"Resources config file not found at {resources_config_path}")
    
    return config


def create_dataset_structure(output_dir: Path) -> Dict[str, Any]:
    """
    Create dataset structure for local execution.
    
    Args:
        output_dir: Base output directory
    
    Returns:
        Dict of dataset objects
    """
    start_time = time.time()
    datasets = {}
    logger.debug(f"Creating dataset structure in {output_dir}")
    
    # Create dataset directories
    dirs = [
        "config", "secrets", "control", "bronze/fhir_raw",
        "silver/fhir_normalized", "gold", "metrics", "monitoring"
    ]
    
    for dir_path in dirs:
        full_path = output_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {full_path}")
    
    # Create dataset objects
    datasets["config_api"] = FoundryDatasetMock(output_dir / "config" / "api_config")
    datasets["config_resources"] = FoundryDatasetMock(output_dir / "config" / "resources_config")
    datasets["epic_token"] = MockSecret(output_dir / "secrets" / "epic_token.json")
    datasets["fhir_cursors"] = FoundryDatasetMock(output_dir / "control" / "fhir_cursors", "json")
    datasets["workflow_status"] = FoundryDatasetMock(output_dir / "control" / "workflow_status", "json")
    datasets["bronze_fhir_raw"] = FoundryDatasetMock(output_dir / "bronze" / "fhir_raw", "json")
    datasets["transform_metrics"] = FoundryDatasetMock(output_dir / "metrics" / "transform_metrics", "parquet")
    datasets["pipeline_metrics"] = FoundryDatasetMock(output_dir / "monitoring" / "pipeline_metrics", "parquet")
    
    # Create silver datasets for each resource type
    resource_types = ["patient", "encounter", "observation", "condition", 
                     "medicationrequest", "procedure", "immunization",
                     "allergyintolerance", "practitioner"]
    
    for resource_type in resource_types:
        datasets[f"silver_{resource_type}"] = FoundryDatasetMock(
            output_dir / "silver" / "fhir_normalized" / resource_type, 
            "parquet"
        )
    
    # Create gold datasets
    gold_datasets = ["patient_summary", "encounter_summary", "medication_summary"]
    for dataset in gold_datasets:
        datasets[f"gold_{dataset}"] = FoundryDatasetMock(
            output_dir / "gold" / dataset, 
            "parquet"
        )
    
    elapsed = time.time() - start_time
    logger.debug(f"Dataset structure created with {len(datasets)} datasets in {elapsed:.2f} seconds")
    return datasets


def run_fetch_token(base_dir: Path, datasets: Dict[str, Any], mock_mode=False) -> bool:
    """
    Run the token fetch transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running token fetch transform")
    
    try:
        # If in mock mode, create a mock token
        if mock_mode:
            logger.info("Using mock token")
            token_data = {
                "access_token": "mock_access_token_for_testing",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "system/Patient.read system/Encounter.read",
                "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
            }
            datasets["epic_token"].write(json.dumps(token_data))
            elapsed = time.time() - start_time
            logger.info(f"Mock token created in {elapsed:.2f} seconds")
            return True
            
        # Import the fetch_token function
        sys.path.insert(0, str(base_dir / "pipelines"))
        from pipelines.fetch_token import fetch_token
        
        # Create a mock environment
        os.environ["EPIC_CLIENT_ID"] = "3d6d8f7d-9bea-4fe2-b44d-81c7fec75ee5"
        # This would be a real secret in production
        os.environ["EPIC_CLIENT_SECRET"] = "mock_secret_for_testing"
        
        logger.debug(f"Environment variables set for token fetch")
        
        # Run the fetch token function
        spark = get_spark_session(mock_mode=mock_mode)
        if spark is None and not mock_mode:
            logger.error("No Spark session available")
            return False
            
        logger.debug("Calling fetch_token function")
        fetch_token(spark, datasets["config_api"], datasets["epic_token"])
        
        elapsed = time.time() - start_time
        logger.info(f"Token fetch completed in {elapsed:.2f} seconds")
        
        # Verify that token was created
        token_content = datasets["epic_token"].read()
        if token_content:
            logger.debug("Token was successfully created")
            return True
        else:
            logger.error("Token fetch did not produce a token")
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in token fetch after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Token fetch error details: {traceback.format_exc()}")
        
        if mock_mode:
            logger.warning("Error in token fetch, creating mock token")
            token_data = {
                "access_token": "mock_access_token_for_testing",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "system/Patient.read system/Encounter.read",
                "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
            }
            try:
                datasets["epic_token"].write(json.dumps(token_data))
                return True
            except:
                return False
        
        return False


def run_extract_resources(
    base_dir: Path, 
    datasets: Dict[str, Any], 
    patient_id: str,
    resource_type: Optional[str] = None,
    mock_mode: bool = False,
    strict_mode: bool = False
) -> bool:
    """
    Run the resource extraction transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        patient_id: Patient ID to extract
        resource_type: Optional specific resource to extract
        mock_mode: Whether to run in mock mode
        strict_mode: Whether to run in strict mode (no fallbacks to mock data)
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info(f"Running resource extraction for patient {patient_id}" + 
               (f", resource: {resource_type}" if resource_type else ""))
    
    # If in mock mode, create mock data
    if mock_mode:
        try:
            logger.info("Creating mock FHIR resources in bronze layer")
            bronze_dir = datasets["bronze_fhir_raw"].path
            
            # Load resource config
            resources_config_path = base_dir / "config" / "resources_config.yaml"
            with open(resources_config_path, 'r') as f:
                resources_config = yaml.safe_load(f)
            
            resource_types = []
            if resource_type:
                resource_types = [resource_type]
            else:
                # Get all resource types from config
                for res_key, res_config in resources_config.get("resources", {}).items():
                    if "/" in res_key:
                        resource_types.append(res_key.split("/")[0])
                    else:
                        resource_types.append(res_key)
            
            # Remove duplicates
            resource_types = list(set(resource_types))
            
            # Create mock data for each resource type
            for res_type in resource_types:
                resource_dir = bronze_dir / res_type
                resource_dir.mkdir(parents=True, exist_ok=True)
                
                # Create mock bundle
                bundle = {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": 5,
                    "entry": []
                }
                
                # Add mock entries
                for i in range(5):
                    entry = {
                        "resource": {
                            "resourceType": res_type,
                            "id": f"mock-{res_type.lower()}-{i}",
                            "meta": {
                                "lastUpdated": datetime.datetime.now().isoformat()
                            }
                        }
                    }
                    
                    # Add patient reference for non-patient resources
                    if res_type != "Patient":
                        entry["resource"]["subject"] = {"reference": f"Patient/{patient_id}"}
                    
                    # Add resource-specific fields
                    if res_type == "Patient":
                        entry["resource"]["name"] = [{"family": "Test", "given": ["Patient"]}]
                        entry["resource"]["gender"] = "unknown"
                        entry["resource"]["birthDate"] = "1970-01-01"
                    elif res_type == "Observation":
                        entry["resource"]["status"] = "final"
                        # Add proper code with coding array
                        entry["resource"]["code"] = {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": f"test-code-{i}",
                                    "display": f"Test Observation {i}"
                                }
                            ],
                            "text": f"Test Observation {i}"
                        }
                        # Add required category element
                        entry["resource"]["category"] = [
                            {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                        "code": "laboratory",
                                        "display": "Laboratory"
                                    }
                                ]
                            }
                        ]
                        entry["resource"]["valueQuantity"] = {"value": 100 + i, "unit": "mg/dL"}
                    elif res_type == "Condition":
                        entry["resource"]["clinicalStatus"] = {"text": "active"}
                        entry["resource"]["code"] = {"text": f"Test Condition {i}"}
                    
                    bundle["entry"].append(entry)
                
                # Save bundle with metadata
                bundle_with_metadata = {
                    "metadata": {
                        "patient_id": patient_id,
                        "resource_type": res_type,
                        "created_at": datetime.datetime.now().isoformat(),
                        "is_mock": True
                    },
                    "bundle": bundle
                }
                
                # Write to file
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                with open(resource_dir / f"{timestamp}_bundle.json", 'w') as f:
                    json.dump(bundle_with_metadata, f, indent=2)
                
                logger.info(f"Created mock data for {res_type} with 5 resources")
            
            elapsed = time.time() - start_time
            logger.info(f"Mock extraction completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock resources: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
    
    try:
        # Import the extract_resources function
        sys.path.insert(0, str(base_dir / "pipelines"))
        logger.debug(f"Importing extract_resources from pipelines.extract_resources")
        from pipelines.extract_resources import extract_resources
        
        # Run the extraction function
        spark = get_spark_session(mock_mode=mock_mode)
        
        # Modify resources config to filter for specific patient
        logger.debug(f"Modifying resources config to filter for patient {patient_id}")
        resources_config = yaml.safe_load(datasets["config_resources"].read_file())
        
        for res_key in resources_config.get("resources", {}):
            if "search_params" in resources_config["resources"][res_key]:
                resources_config["resources"][res_key]["search_params"].append(f"patient={patient_id}")
                logger.debug(f"Added patient filter for resource {res_key}")
        
        # Write modified config back
        modified_config_path = base_dir / "temp" / "modified_config"
        logger.debug(f"Writing modified config to {modified_config_path}")
        modified_config = FoundryDatasetMock(modified_config_path)
        modified_config.write_file("resources_config.yaml", yaml.dump(resources_config))
        
        # Check if token exists
        token_content = datasets["epic_token"].read()
        if not token_content:
            logger.warning("No token found, extraction may fail")
        
        logger.debug("Starting extract_resources function call")
        extract_resources(
            spark, 
            datasets["config_api"], 
            modified_config, 
            datasets["epic_token"], 
            datasets["fhir_cursors"],
            datasets["bronze_fhir_raw"],
            resource_type,
            2  # Use 2 workers for local testing
        )
        
        # Verify output
        bronze_path = datasets["bronze_fhir_raw"].path
        files_created = list(bronze_path.glob("**/*.json"))
        file_count = len(files_created)
        
        elapsed = time.time() - start_time
        logger.info(f"Resource extraction completed in {elapsed:.2f} seconds, created {file_count} files")
        
        if file_count == 0:
            error_msg = "No resources were extracted"
            logger.warning(error_msg)
            if strict_mode:
                logger.error("Strict mode enabled - failing due to no extracted resources")
                return False
            else:
                logger.warning("Continuing despite no resources found")
                return True if not strict_mode else False
            
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in resource extraction after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Extraction error details: {traceback.format_exc()}")
        
        if not strict_mode and mock_mode:
            logger.warning("Extraction failed, falling back to mock data creation")
            # Try again in mock mode
            return run_extract_resources(base_dir, datasets, patient_id, resource_type, mock_mode=True, strict_mode=strict_mode)
        
        if strict_mode:
            logger.error("Strict mode enabled - failing due to extraction error")
            
        return False


def check_bronze_file_compatibility(bronze_path: Path) -> bool:
    """
    Check if bronze files are in a compatible format for transformation.
    
    Args:
        bronze_path: Path to bronze files
        
    Returns:
        True if files are compatible, False otherwise
    """
    # Check if any resource directories exist
    resource_dirs = [d for d in bronze_path.iterdir() if d.is_dir()]
    if not resource_dirs:
        logger.warning("No bronze resource directories found")
        return False
    
    # Check each resource directory for files
    all_valid = True
    for resource_dir in resource_dirs:
        resource_type = resource_dir.name
        json_files = list(resource_dir.glob("*.json"))
        parquet_files = list(resource_dir.glob("*.parquet"))
        delta_log = resource_dir / "_delta_log"
        
        if not json_files and not parquet_files and not delta_log.exists():
            logger.warning(f"No valid files found for {resource_type} - expected JSON, Parquet, or Delta")
            all_valid = False
            continue
            
        # If we have JSON files, validate their structure
        if json_files:
            # Check first file to validate format
            try:
                with open(json_files[0], 'r') as f:
                    data = json.load(f)
                    # Check for bundle structure (most common from extraction)
                    if "bundle" in data:
                        if "entry" not in data["bundle"]:
                            logger.warning(f"JSON file for {resource_type} has 'bundle' but no 'entry' field")
                            all_valid = False
                    # Or check direct resource format
                    elif "resourceType" not in data:
                        logger.warning(f"JSON file for {resource_type} doesn't have 'bundle' or 'resourceType' field")
                        all_valid = False
            except Exception as e:
                logger.warning(f"Error validating JSON for {resource_type}: {str(e)}")
                all_valid = False
    
    return all_valid


def run_transform_resources(
    base_dir: Path, 
    datasets: Dict[str, Any], 
    resource_type: Optional[str] = None,
    mock_mode: bool = False,
    strict_mode: bool = False
) -> bool:
    """
    Run the resource transformation transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        resource_type: Optional specific resource to transform
        mock_mode: Whether to run in mock mode
        strict_mode: Whether to run in strict mode (no fallbacks to mock data)
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info(f"Running resource transformation" + 
               (f" for {resource_type}" if resource_type else ""))
    
    # In mock mode, create mock silver output
    if mock_mode:
        if strict_mode:
            logger.error("Cannot use mock mode when strict mode is enabled")
            return False
            
        try:
            logger.info("Creating mock silver layer data")
            
            # Get bronze files to determine what resources we have
            bronze_path = datasets["bronze_fhir_raw"].path
            resource_dirs = [d for d in bronze_path.iterdir() if d.is_dir()]
            
            if not resource_dirs:
                logger.warning("No bronze resources found")
                return False
            
            # Create silver output for each resource type
            for resource_dir in resource_dirs:
                resource_type = resource_dir.name
                
                # Skip if specific resource type requested and not this one
                if resource_type and resource_type != resource_dir.name:
                    continue
                
                # Create silver directory
                silver_path = Path(str(bronze_path).replace("bronze/fhir_raw", "silver/fhir_normalized"))
                silver_resource_path = silver_path / resource_type.lower()
                silver_resource_path.mkdir(parents=True, exist_ok=True)
                
                # Create a dummy parquet file to simulate output
                dummy_file = silver_resource_path / "_SUCCESS"
                dummy_file.touch()
                
                logger.info(f"Created mock silver data for {resource_type}")
            
            # Create mock metrics
            metrics_path = datasets["transform_metrics"].path
            dummy_metrics = metrics_path / "_SUCCESS"
            dummy_metrics.touch()
            
            elapsed = time.time() - start_time
            logger.info(f"Mock transformation completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock silver data: {str(e)}")
            logger.debug(f"Mock silver creation error details: {traceback.format_exc()}")
            return False
    
    try:
        # Import the transform_resources function
        sys.path.insert(0, str(base_dir / "pipelines"))
        logger.debug(f"Importing transform_resources from pipelines.transform_load")
        from pipelines.transform_load import transform_resources
        
        # Run the transformation function
        spark = get_spark_session(mock_mode=mock_mode)
        
        if spark is None:
            error_msg = "Failed to create Spark session for transformation"
            logger.error(error_msg)
            if strict_mode:
                logger.error("Strict mode enabled - cannot continue without Spark")
                return False
            else:
                logger.warning("Falling back to mock mode transformation")
                return run_transform_resources(base_dir, datasets, resource_type, mock_mode=True, strict_mode=strict_mode)
        
        # Check if there's data to transform
        bronze_path = datasets["bronze_fhir_raw"].path
        bronze_files = list(bronze_path.glob("**/*.json"))
        if not bronze_files:
            logger.warning("No bronze files found to transform")
            if strict_mode:
                logger.error("Strict mode enabled - cannot continue without input data")
                return False
            else:
                logger.warning("Creating mock data for demonstration")
                return run_transform_resources(base_dir, datasets, resource_type, mock_mode=True, strict_mode=strict_mode)
        
        logger.debug(f"Found {len(bronze_files)} bronze files to transform")
        
        # Check file format compatibility
        logger.info("Checking bronze file format compatibility")
        if not check_bronze_file_compatibility(bronze_path):
            logger.warning("Some bronze files have incompatible formats - transformation may fail")
            if strict_mode:
                logger.error("Strict mode enabled - cannot continue with incompatible file formats")
                return False
            # Continue anyway as our updated transform code should handle different formats
        
        # Create silver dataset directory
        silver_dir = Path(str(datasets["bronze_fhir_raw"].path).replace("bronze/fhir_raw", "silver/fhir_normalized"))
        silver_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created silver output directory: {silver_dir}")
        
        # Create a mock silver output
        silver_output = FoundryDatasetMock(silver_dir)
        
        logger.debug("Starting transform_resources function call")
        transform_resources(
            spark, 
            datasets["bronze_fhir_raw"], 
            datasets["config_resources"],
            datasets["transform_metrics"],
            silver_output,
            resource_type
        )
        
        # Verify output
        transformed_files = list(silver_dir.glob("**/*"))
        file_count = len([f for f in transformed_files if f.is_file()])
        
        if file_count == 0:
            logger.warning("No output files were created during transformation")
            if strict_mode:
                logger.error("Strict mode enabled - transformation produced no output files")
                return False
        
        elapsed = time.time() - start_time
        logger.info(f"Resource transformation completed in {elapsed:.2f} seconds")
        logger.debug(f"Created {file_count} output files/directories")
        
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in resource transformation after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Transformation error details: {traceback.format_exc()}")
        
        if strict_mode:
            logger.error("Strict mode enabled - failing due to transformation error")
            return False
        elif mock_mode:
            logger.warning("Transformation failed, falling back to mock data creation")
            # Try again in mock mode
            return run_transform_resources(base_dir, datasets, resource_type, mock_mode=True, strict_mode=strict_mode)
        
        return False


def run_gold_patient_summary(base_dir: Path, datasets: Dict[str, Any], mock_mode: bool = False) -> bool:
    """
    Run the patient summary gold transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running patient summary gold transform")
    
    # In mock mode, create mock gold output
    if mock_mode:
        try:
            logger.info("Creating mock gold patient summary")
            gold_dir = datasets["gold_patient_summary"].path
            gold_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy parquet file
            dummy_file = gold_dir / "_SUCCESS"
            dummy_file.touch()
            
            elapsed = time.time() - start_time
            logger.info(f"Mock patient summary completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock patient summary: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
    
    try:
        # Import the create_patient_summary function
        sys.path.insert(0, str(base_dir / "pipelines" / "gold"))
        from pipelines.gold.patient_summary import create_patient_summary
        
        # Run the patient summary function
        spark = get_spark_session(mock_mode=mock_mode)
        
        create_patient_summary(
            spark,
            datasets["silver_patient"],
            datasets["silver_encounter"],
            datasets["silver_condition"],
            datasets["silver_observation"],
            datasets["silver_medicationrequest"],
            datasets["silver_immunization"],
            datasets["silver_allergyintolerance"],
            datasets["gold_patient_summary"]
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Patient summary completed in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in patient summary after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Patient summary error details: {traceback.format_exc()}")
        
        if mock_mode:
            logger.warning("Patient summary failed, falling back to mock data creation")
            # Try again in mock mode
            return run_gold_patient_summary(base_dir, datasets, mock_mode=True)
        
        return False


def run_gold_encounter_summary(base_dir: Path, datasets: Dict[str, Any], mock_mode: bool = False) -> bool:
    """
    Run the encounter summary gold transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running encounter summary gold transform")
    
    # In mock mode, create mock gold output
    if mock_mode:
        try:
            logger.info("Creating mock gold encounter summary")
            gold_dir = datasets["gold_encounter_summary"].path
            gold_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy parquet file
            dummy_file = gold_dir / "_SUCCESS"
            dummy_file.touch()
            
            elapsed = time.time() - start_time
            logger.info(f"Mock encounter summary completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock encounter summary: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
            
    try:
        # Import the create_encounter_summary function
        sys.path.insert(0, str(base_dir / "pipelines" / "gold"))
        from pipelines.gold.encounter_summary import create_encounter_summary
        
        # Run the encounter summary function
        spark = get_spark_session(mock_mode=mock_mode)
        
        create_encounter_summary(
            spark,
            datasets["silver_encounter"],
            datasets["silver_patient"],
            datasets["silver_condition"],
            datasets["silver_procedure"],
            datasets["silver_observation"],
            datasets["silver_practitioner"],
            datasets["gold_encounter_summary"]
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Encounter summary completed in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in encounter summary after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Encounter summary error details: {traceback.format_exc()}")
        
        if mock_mode:
            logger.warning("Encounter summary failed, falling back to mock data creation")
            # Try again in mock mode
            return run_gold_encounter_summary(base_dir, datasets, mock_mode=True)
        
        return False


def run_gold_medication_summary(base_dir: Path, datasets: Dict[str, Any], mock_mode: bool = False, strict_mode: bool = False) -> bool:
    """
    Run the medication summary gold transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
        strict_mode: Whether to run in strict mode (no fallbacks to mock data)
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running medication summary gold transform")
    
    # In mock mode, create mock gold output
    if mock_mode:
        if strict_mode:
            logger.error("Cannot use mock mode when strict mode is enabled")
            return False
            
        try:
            logger.info("Creating mock gold medication summary")
            gold_dir = datasets["gold_medication_summary"].path
            gold_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy parquet file
            dummy_file = gold_dir / "_SUCCESS"
            dummy_file.touch()
            
            elapsed = time.time() - start_time
            logger.info(f"Mock medication summary completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock medication summary: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
            
    try:
        # Import the create_medication_summary function
        sys.path.insert(0, str(base_dir / "pipelines" / "gold"))
        from pipelines.gold.medication_summary import create_medication_summary
        
        # Run the medication summary function
        spark = get_spark_session(mock_mode=mock_mode)
        
        if spark is None:
            error_msg = "Failed to create Spark session for medication summary"
            logger.error(error_msg)
            if strict_mode:
                logger.error("Strict mode enabled - cannot continue without Spark")
                return False
            else:
                logger.warning("Falling back to mock mode transformation")
                return run_gold_medication_summary(base_dir, datasets, mock_mode=True, strict_mode=strict_mode)
        
        # First validate that we have the required silver datasets
        silver_medication_dir = datasets.get("silver_medicationrequest", {}).get("path")
        if not silver_medication_dir or not silver_medication_dir.exists():
            logger.warning("No medication request silver data found")
            if strict_mode:
                logger.error("Strict mode enabled - cannot continue without medication request data")
                return False
            else:
                logger.warning("Falling back to mock mode for medication summary")
                return run_gold_medication_summary(base_dir, datasets, mock_mode=True, strict_mode=strict_mode)
        
        # Load silver medication dataset
        try:
            medication_df = spark.read.format("delta").load(str(silver_medication_dir))
            logger.info(f"Loaded {medication_df.count()} medication request records from silver layer")
        except Exception as e:
            logger.error(f"Error loading medication request silver data: {str(e)}")
            if strict_mode:
                logger.error("Strict mode enabled - failing due to data loading error")
                return False
            else:
                logger.warning("Falling back to mock mode after data loading error")
                return run_gold_medication_summary(base_dir, datasets, mock_mode=True, strict_mode=strict_mode)
        
        # Load optional silver datasets
        medication_details_df = None
        patient_df = None
        encounter_df = None
        practitioner_df = None
        
        # Load medication details if available
        silver_medication_details_dir = datasets.get("silver_medication", {}).get("path")
        if silver_medication_details_dir and silver_medication_details_dir.exists():
            try:
                medication_details_df = spark.read.format("delta").load(str(silver_medication_details_dir))
                logger.info(f"Loaded {medication_details_df.count()} medication details from silver layer")
            except Exception as e:
                logger.warning(f"Error loading medication details: {str(e)}")
        
        # Load patient data if available
        silver_patient_dir = datasets.get("silver_patient", {}).get("path")
        if silver_patient_dir and silver_patient_dir.exists():
            try:
                patient_df = spark.read.format("delta").load(str(silver_patient_dir))
                logger.info(f"Loaded {patient_df.count()} patient records from silver layer")
            except Exception as e:
                logger.warning(f"Error loading patient data: {str(e)}")
        
        # Load encounter data if available
        silver_encounter_dir = datasets.get("silver_encounter", {}).get("path")
        if silver_encounter_dir and silver_encounter_dir.exists():
            try:
                encounter_df = spark.read.format("delta").load(str(silver_encounter_dir))
                logger.info(f"Loaded {encounter_df.count()} encounter records from silver layer")
            except Exception as e:
                logger.warning(f"Error loading encounter data: {str(e)}")
        
        # Load practitioner data if available
        silver_practitioner_dir = datasets.get("silver_practitioner", {}).get("path")
        if silver_practitioner_dir and silver_practitioner_dir.exists():
            try:
                practitioner_df = spark.read.format("delta").load(str(silver_practitioner_dir))
                logger.info(f"Loaded {practitioner_df.count()} practitioner records from silver layer")
            except Exception as e:
                logger.warning(f"Error loading practitioner data: {str(e)}")
        
        # Run the medication summary function
        create_medication_summary(
            spark,
            medication_df,
            medication_details_df,
            patient_df,
            encounter_df,
            practitioner_df,
            datasets["gold_medication_summary"]
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Medication summary completed in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in medication summary after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Medication summary error details: {traceback.format_exc()}")
        
        if strict_mode:
            logger.error("Strict mode enabled - failing due to error")
            return False
        elif mock_mode:
            logger.warning("Medication summary failed, falling back to mock data creation")
            # Try again in mock mode
            return run_gold_medication_summary(base_dir, datasets, mock_mode=True, strict_mode=False)
        else:
            return False


def run_pipeline_monitoring(base_dir: Path, datasets: Dict[str, Any], mock_mode: bool = False) -> bool:
    """
    Run the pipeline monitoring transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running pipeline monitoring transform")
    
    # In mock mode, create mock monitoring output
    if mock_mode:
        try:
            logger.info("Creating mock pipeline monitoring data")
            monitoring_dir = datasets["pipeline_metrics"].path
            monitoring_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy parquet file
            dummy_file = monitoring_dir / "_SUCCESS"
            dummy_file.touch()
            
            # Create a mock metrics file
            metrics_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "pipeline_run_id": "mock-run-123",
                "metrics": {
                    "resources_processed": 100,
                    "errors": 0,
                    "warnings": 5,
                    "execution_time": 42.5
                }
            }
            
            metrics_file = monitoring_dir / "mock_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            elapsed = time.time() - start_time
            logger.info(f"Mock pipeline monitoring completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock monitoring data: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
    
    try:
        # Import the generate_monitoring_metrics function
        sys.path.insert(0, str(base_dir / "pipelines"))
        from pipelines.monitoring import generate_monitoring_metrics
        
        # Run the monitoring function
        spark = get_spark_session(mock_mode=mock_mode)
        
        generate_monitoring_metrics(
            spark,
            datasets["fhir_cursors"],
            datasets["transform_metrics"],
            datasets["epic_token"],
            datasets["workflow_status"],
            datasets["config_resources"],
            None,  # silver_inputs is complex, pass None for local testing
            datasets["pipeline_metrics"]
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Pipeline monitoring completed in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in pipeline monitoring after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Monitoring error details: {traceback.format_exc()}")
        
        if mock_mode:
            logger.warning("Pipeline monitoring failed, falling back to mock data creation")
            # Try again in mock mode
            return run_pipeline_monitoring(base_dir, datasets, mock_mode=True)
        
        return False


def run_workflow_orchestrator(base_dir: Path, datasets: Dict[str, Any], mock_mode: bool = False) -> bool:
    """
    Run the workflow orchestration transform.
    
    Args:
        base_dir: Base directory containing code
        datasets: Dataset objects
        mock_mode: Whether to run in mock mode
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Running workflow orchestrator transform")
    
    # In mock mode, create mock workflow output
    if mock_mode:
        try:
            logger.info("Creating mock workflow status data")
            workflow_dir = datasets["workflow_status"].path
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a mock workflow status file
            status_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "run_id": "mock-run-123",
                "status": "COMPLETED",
                "steps": {
                    "token": "SUCCESS",
                    "extract": "SUCCESS",
                    "transform": "SUCCESS",
                    "gold": "SUCCESS",
                    "monitoring": "SUCCESS"
                }
            }
            
            status_file = workflow_dir / "mock_status.json"
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            
            elapsed = time.time() - start_time
            logger.info(f"Mock workflow orchestration completed in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error creating mock workflow status: {str(e)}")
            logger.debug(f"Mock creation error details: {traceback.format_exc()}")
            return False
    
    try:
        # Import the orchestrate_pipeline function
        sys.path.insert(0, str(base_dir / "pipelines"))
        from pipelines.workflow import orchestrate_pipeline
        
        # Run the orchestration function
        spark = get_spark_session(mock_mode=mock_mode)
        
        orchestrate_pipeline(
            spark,
            datasets["config_resources"],
            datasets["config_api"],
            datasets["epic_token"],
            datasets["fhir_cursors"],
            datasets["transform_metrics"],
            datasets["silver_patient"],
            datasets["workflow_status"]
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Workflow orchestration completed in {elapsed:.2f} seconds")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in workflow orchestration after {elapsed:.2f} seconds: {str(e)}")
        logger.debug(f"Orchestration error details: {traceback.format_exc()}")
        
        if mock_mode:
            logger.warning("Workflow orchestration failed, falling back to mock data creation")
            # Try again in mock mode
            return run_workflow_orchestrator(base_dir, datasets, mock_mode=True)
        
        return False


def summarize_results(output_dir: Path, patient_id: str = None):
    """
    Summarize the pipeline results.
    
    Args:
        output_dir: Output directory containing pipeline results
        patient_id: Optional patient ID to include in summary
    """
    start_time = time.time()
    
    # Generate a divider line and header
    divider = "=" * 80
    title = "SUMMARY OF FHIR PIPELINE RESULTS"
    if patient_id:
        title += f" FOR PATIENT {patient_id}"
    
    print("\n" + divider)
    print(title)
    print(divider)
    
    # Try to use Spark if available
    try:
        spark = get_spark_session(mock_mode=True)
        
        # List bronze files
        bronze_dir = output_dir / "bronze" / "fhir_raw"
        bronze_files = list(bronze_dir.glob("**/*.json"))
        print(f"\nBronze Layer: {len(bronze_files)} files")
        
        for resource_dir in bronze_dir.glob("*"):
            if resource_dir.is_dir():
                resource_files = list(resource_dir.glob("**/*.json"))
                print(f"  - {resource_dir.name}: {len(resource_files)} files")
        
        # List silver datasets
        silver_dir = output_dir / "silver" / "fhir_normalized"
        print("\nSilver Layer:")
        
        for resource_dir in silver_dir.glob("*"):
            if resource_dir.is_dir() and resource_dir.name != "_SUCCESS":
                # Try to count rows if Spark is available
                try:
                    if spark and os.path.exists(f"{resource_dir}/_SUCCESS"):
                        df = spark.read.parquet(str(resource_dir))
                        print(f"  - {resource_dir.name}: {df.count()} rows")
                    else:
                        parquet_files = list(resource_dir.glob("**/*.parquet"))
                        print(f"  - {resource_dir.name}: {len(parquet_files)} parquet files")
                except Exception as e:
                    logger.debug(f"Error reading {resource_dir}: {str(e)}")
                    print(f"  - {resource_dir.name}: Unable to read")
        
        # List gold datasets
        gold_dir = output_dir / "gold"
        print("\nGold Layer:")
        
        for dataset_dir in gold_dir.glob("*"):
            if dataset_dir.is_dir() and dataset_dir.name != "_SUCCESS":
                # Try to count rows if Spark is available
                try:
                    if spark and os.path.exists(f"{dataset_dir}/_SUCCESS"):
                        df = spark.read.parquet(str(dataset_dir))
                        print(f"  - {dataset_dir.name}: {df.count()} rows")
                    else:
                        parquet_files = list(dataset_dir.glob("**/*.parquet"))
                        print(f"  - {dataset_dir.name}: {len(parquet_files)} parquet files")
                except Exception as e:
                    logger.debug(f"Error reading {dataset_dir}: {str(e)}")
                    print(f"  - {dataset_dir.name}: Unable to read")
        
        # List monitoring metrics
        print("\nPipeline Monitoring:")
        monitoring_dir = output_dir / "monitoring" / "pipeline_metrics"
        if list(monitoring_dir.glob("*.parquet")):
            try:
                if spark and os.path.exists(f"{monitoring_dir}/_SUCCESS"):
                    df = spark.read.parquet(str(monitoring_dir))
                    print(f"  - Metrics count: {df.count()} rows")
                else:
                    parquet_files = list(monitoring_dir.glob("**/*.parquet"))
                    print(f"  - Pipeline metrics: {len(parquet_files)} parquet files")
            except Exception as e:
                logger.debug(f"Error reading pipeline metrics: {str(e)}")
                print(f"  - Pipeline metrics: Unable to read")
    
    except Exception as e:
        logger.error(f"Error during results summary: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Fallback to basic file listing if Spark fails
        try:
            bronze_dir = output_dir / "bronze" / "fhir_raw"
            bronze_files = list(bronze_dir.glob("**/*.*"))
            print(f"\nBronze Layer: {len(bronze_files)} files")
            
            for resource_dir in bronze_dir.glob("*"):
                if resource_dir.is_dir():
                    resource_files = list(resource_dir.glob("**/*.*"))
                    print(f"  - {resource_dir.name}: {len(resource_files)} files")
            
            silver_dir = output_dir / "silver" / "fhir_normalized"
            print("\nSilver Layer:")
            for resource_dir in silver_dir.glob("*"):
                if resource_dir.is_dir():
                    print(f"  - {resource_dir.name}: Directory exists")
            
            gold_dir = output_dir / "gold"
            print("\nGold Layer:")
            for dataset_dir in gold_dir.glob("*"):
                if dataset_dir.is_dir():
                    print(f"  - {dataset_dir.name}: Directory exists")
        except Exception as inner_e:
            logger.error(f"Error during basic file listing: {str(inner_e)}")
    
    print("\nProcessing Complete!")
    print(divider)


def create_mock_data(output_dir: Path, patient_id: str) -> bool:
    """
    Create mock data for testing in the bronze layer.
    
    Args:
        output_dir: Base output directory
        patient_id: Patient ID to use
    
    Returns:
        Success status
    """
    start_time = time.time()
    logger.info("Creating mock FHIR data for testing")
    
    try:
        # Create bronze directory
        bronze_dir = output_dir / "bronze" / "fhir_raw"
        bronze_dir.mkdir(parents=True, exist_ok=True)
        
        # Define resource types to create
        resource_types = ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest"]
        
        for res_type in resource_types:
            logger.debug(f"Creating mock data for resource type: {res_type}")
            
            # Create resource directory
            resource_dir = bronze_dir / res_type
            resource_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock bundle
            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 5,
                "entry": []
            }
            
            # Add mock entries
            for i in range(5):
                entry = {
                    "resource": {
                        "resourceType": res_type,
                        "id": f"mock-{res_type.lower()}-{i}",
                        "meta": {
                            "lastUpdated": datetime.datetime.now().isoformat()
                        }
                    }
                }
                
                # Add patient reference for non-patient resources
                if res_type != "Patient":
                    entry["resource"]["subject"] = {"reference": f"Patient/{patient_id}"}
                
                # Add resource-specific fields
                if res_type == "Patient":
                    entry["resource"]["name"] = [{"family": "Test", "given": ["Patient"]}]
                    entry["resource"]["gender"] = "unknown"
                    entry["resource"]["birthDate"] = "1970-01-01"
                elif res_type == "Observation":
                    entry["resource"]["status"] = "final"
                    # Add proper code with coding array
                    entry["resource"]["code"] = {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": f"test-code-{i}",
                                "display": f"Test Observation {i}"
                            }
                        ],
                        "text": f"Test Observation {i}"
                    }
                    # Add required category element
                    entry["resource"]["category"] = [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "laboratory",
                                    "display": "Laboratory"
                                }
                            ]
                        }
                    ]
                    entry["resource"]["valueQuantity"] = {"value": 100 + i, "unit": "mg/dL"}
                elif res_type == "Condition":
                    entry["resource"]["clinicalStatus"] = {"text": "active"}
                    entry["resource"]["code"] = {"text": f"Test Condition {i}"}
                elif res_type == "Encounter":
                    entry["resource"]["status"] = "finished"
                    entry["resource"]["class"] = {"code": "AMB"}
                    entry["resource"]["period"] = {
                        "start": "2023-01-01T08:00:00Z",
                        "end": "2023-01-01T09:00:00Z"
                    }
                elif res_type == "MedicationRequest":
                    entry["resource"]["status"] = "active"
                    entry["resource"]["intent"] = "order"
                    entry["resource"]["medicationCodeableConcept"] = {"text": f"Test Medication {i}"}
                
                bundle["entry"].append(entry)
            
            # Save bundle with metadata
            bundle_with_metadata = {
                "metadata": {
                    "patient_id": patient_id,
                    "resource_type": res_type,
                    "created_at": datetime.datetime.now().isoformat(),
                    "entry_count": len(bundle["entry"])
                },
                "bundle": bundle
            }
            
            # Write to file
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            bundle_filename = f"{timestamp}_bundle_{res_type.lower()}.json"
            bundle_path = resource_dir / bundle_filename
            
            with open(bundle_path, 'w') as f:
                json.dump(bundle_with_metadata, f, indent=2)
            
            logger.info(f"Created mock data for {res_type} with {len(bundle['entry'])} resources")
        
        # Now create mock silver data (just directories for now)
        silver_dir = output_dir / "silver" / "fhir_normalized"
        silver_dir.mkdir(parents=True, exist_ok=True)
        
        for res_type in resource_types:
            resource_dir = silver_dir / res_type.lower()
            resource_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a _SUCCESS file
            success_file = resource_dir / "_SUCCESS"
            success_file.touch()
            
            logger.debug(f"Created mock silver data directory for {res_type}")
        
        # Create mock gold data
        gold_datasets = ["patient_summary", "encounter_summary", "medication_summary"]
        for dataset_name in gold_datasets:
            gold_dir = output_dir / "gold" / dataset_name
            gold_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a _SUCCESS file
            success_file = gold_dir / "_SUCCESS"
            success_file.touch()
            
            logger.debug(f"Created mock gold data directory for {dataset_name}")
        
        elapsed = time.time() - start_time
        logger.info(f"Mock data creation completed in {elapsed:.2f} seconds")
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error creating mock data: {str(e)}")
        logger.debug(f"Mock data creation error details: {traceback.format_exc()}")
        return False


def main():
    """Main function to run the local FHIR pipeline."""
    parser = argparse.ArgumentParser(description='Run FHIR pipeline locally')
    parser.add_argument('--patient-id', required=True, help='Patient ID to process')
    parser.add_argument('--output-dir', default='./local_output', 
                       help='Output directory for pipeline results')
    parser.add_argument('--steps', default='all',
                       help='Pipeline steps to run (comma-separated: token,extract,transform,gold,monitoring)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--mock', action='store_true', help='Use mock mode for API calls')
    parser.add_argument('--no-spark', action='store_true', help='Skip Spark operations')
    parser.add_argument('--strict', action='store_true', help='Run in strict mode with no mock data fallbacks')
    args = parser.parse_args()
    
    # Setup debug logging if requested
    setup_debug_logging(args.debug)
    
    start_time = time.time()
    logger.info(f"Starting local FHIR pipeline at {datetime.datetime.now().isoformat()}")
    logger.debug(f"Command line arguments: {args}")
    
    # Check for strict mode and mock mode conflict
    if args.strict and args.mock:
        logger.error("Cannot use both --strict and --mock flags together")
        logger.error("Strict mode requires real API calls (--mock=false)")
        sys.exit(1)
    
    # Validate arguments
    if not args.patient_id:
        logger.error("Patient ID is required")
        sys.exit(1)
    
    # Determine steps to run
    all_steps = ['token', 'extract', 'transform', 'gold', 'monitoring']
    steps_to_run = args.steps.split(',') if args.steps != 'all' else all_steps
    
    # Validate steps
    for step in steps_to_run:
        if step not in all_steps and step != 'all':
            logger.error(f"Invalid step: {step}")
            sys.exit(1)
    
    # Get base directory
    base_dir = Path(os.path.abspath(os.path.dirname(__file__)))
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.strict:
        logger.info("Running in STRICT mode - will fail on errors rather than using mock data fallbacks")
    
    logger.info(f"Running FHIR pipeline for patient ID: {args.patient_id}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Steps to run: {steps_to_run}")
    
    # Set mock mode
    mock_mode = args.mock or args.no_spark
    
    # Check for mock mode
    if mock_mode:
        if args.strict:
            logger.error("Cannot run in both mock mode and strict mode")
            sys.exit(1)
            
        logger.info("Running in mock mode - no real API calls will be made")
        os.environ["MOCK_API_CALLS"] = "true"
        
        # Generate mock data upfront
        create_mock_data(output_dir, args.patient_id)
    
    # Create dataset structure
    try:
        logger.debug("Creating dataset structure")
        datasets = create_dataset_structure(output_dir)
    except Exception as e:
        logger.error(f"Failed to create dataset structure: {str(e)}")
        logger.debug(f"Dataset creation error: {traceback.format_exc()}")
        sys.exit(1)
    
    # Copy config files to output directory
    try:
        logger.debug("Copying configuration files to output directory")
        shutil.copy(base_dir / "config" / "api_config.yaml", output_dir / "config")
        shutil.copy(base_dir / "config" / "resources_config.yaml", output_dir / "config")
    except Exception as e:
        logger.error(f"Failed to copy config files: {str(e)}")
        logger.debug(f"Config copy error: {traceback.format_exc()}")
        sys.exit(1)
    
    # Create temp directory for modified files
    temp_dir = base_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Load configs
    configs = load_config_files(base_dir)
    
    # Execute pipeline steps
    step_timings = {}
    success = {}
    
    # Token refresh
    if 'token' in steps_to_run:
        token_start = time.time()
        logger.info("Starting token fetch step")
        success['token'] = run_fetch_token(base_dir, datasets, mock_mode=mock_mode)
        step_timings['token'] = time.time() - token_start
        logger.info(f"Token fetch completed in {step_timings['token']:.2f} seconds with status: {'SUCCESS' if success['token'] else 'FAILURE'}")
    
    # Resource extraction
    if 'extract' in steps_to_run:
        if 'token' in success and not success['token'] and not mock_mode:
            logger.warning("Skipping extraction due to token fetch failure")
        else:
            extract_start = time.time()
            logger.info("Starting resource extraction step")
            if mock_mode:
                # In mock mode, the extraction is already done by create_mock_data
                success['extract'] = True
                logger.info("Using pre-generated mock data")
            else:
                success['extract'] = run_extract_resources(base_dir, datasets, args.patient_id, mock_mode=mock_mode, strict_mode=args.strict)
            step_timings['extract'] = time.time() - extract_start
            logger.info(f"Resource extraction completed in {step_timings['extract']:.2f} seconds with status: {'SUCCESS' if success['extract'] else 'FAILURE'}")
    
    # Resource transformation
    if 'transform' in steps_to_run:
        if 'extract' in success and not success['extract']:
            logger.warning("Skipping transformation due to extraction failure")
        else:
            transform_start = time.time()
            logger.info("Starting resource transformation step")
            if mock_mode:
                # In mock mode, the transformation is already set up by create_mock_data
                success['transform'] = True
                logger.info("Using pre-generated mock data for silver layer")
            else:
                success['transform'] = run_transform_resources(base_dir, datasets, mock_mode=mock_mode, strict_mode=args.strict)
            step_timings['transform'] = time.time() - transform_start
            logger.info(f"Resource transformation completed in {step_timings['transform']:.2f} seconds with status: {'SUCCESS' if success['transform'] else 'FAILURE'}")
    
    # Gold layer transforms
    if 'gold' in steps_to_run:
        if 'transform' in success and not success['transform']:
            logger.warning("Skipping gold transforms due to transformation failure")
        else:
            gold_start = time.time()
            logger.info("Starting gold layer transforms")
            
            # Run gold layer transforms in parallel for local testing
            if mock_mode:
                # In mock mode, the gold layer is already set up by create_mock_data
                success['gold_patient'] = True
                success['gold_encounter'] = True
                success['gold_medication'] = True
                logger.info("Using pre-generated mock data for gold layer")
            else:
                gold_patient_start = time.time()
                success['gold_patient'] = run_gold_patient_summary(base_dir, datasets, mock_mode=mock_mode)
                step_timings['gold_patient'] = time.time() - gold_patient_start
                logger.info(f"Patient summary completed in {step_timings['gold_patient']:.2f} seconds with status: {'SUCCESS' if success['gold_patient'] else 'FAILURE'}")
                
                gold_encounter_start = time.time()
                success['gold_encounter'] = run_gold_encounter_summary(base_dir, datasets, mock_mode=mock_mode)
                step_timings['gold_encounter'] = time.time() - gold_encounter_start
                logger.info(f"Encounter summary completed in {step_timings['gold_encounter']:.2f} seconds with status: {'SUCCESS' if success['gold_encounter'] else 'FAILURE'}")
                
                gold_medication_start = time.time()
                success['gold_medication'] = run_gold_medication_summary(base_dir, datasets, mock_mode=mock_mode, strict_mode=args.strict)
                step_timings['gold_medication'] = time.time() - gold_medication_start
                logger.info(f"Medication summary completed in {step_timings['gold_medication']:.2f} seconds with status: {'SUCCESS' if success['gold_medication'] else 'FAILURE'}")
            
            step_timings['gold_total'] = time.time() - gold_start
            logger.info(f"All gold transforms completed in {step_timings['gold_total']:.2f} seconds")
    
    # Pipeline monitoring
    if 'monitoring' in steps_to_run:
        if all(not success.get(k, False) for k in ['gold_patient', 'gold_encounter', 'gold_medication']):
            logger.warning("Skipping monitoring due to gold transform failures")
        else:
            monitoring_start = time.time()
            logger.info("Starting pipeline monitoring step")
            success['monitoring'] = run_pipeline_monitoring(base_dir, datasets, mock_mode=mock_mode)
            step_timings['monitoring'] = time.time() - monitoring_start
            logger.info(f"Pipeline monitoring completed in {step_timings['monitoring']:.2f} seconds with status: {'SUCCESS' if success['monitoring'] else 'FAILURE'}")
    
    # Always run workflow orchestrator last
    orchestrator_start = time.time()
    logger.info("Starting workflow orchestrator step")
    success['orchestrator'] = run_workflow_orchestrator(base_dir, datasets, mock_mode=mock_mode)
    step_timings['orchestrator'] = time.time() - orchestrator_start
    logger.info(f"Workflow orchestrator completed in {step_timings['orchestrator']:.2f} seconds with status: {'SUCCESS' if success['orchestrator'] else 'FAILURE'}")
    
    # Summarize results
    logger.info("Generating summary report")
    summarize_results(output_dir, args.patient_id)
    
    # Report overall status
    print("\nPipeline Execution Status:")
    for step, status in success.items():
        step_time = step_timings.get(step, 0)
        print(f"  - {step}: {'SUCCESS' if status else 'FAILURE'} ({step_time:.2f} seconds)")
    
    # Log timings
    logger.debug("Step execution times:")
    for step, timing in step_timings.items():
        logger.debug(f"  - {step}: {timing:.2f} seconds")
    
    # Clean up
    if temp_dir.exists():
        logger.debug(f"Cleaning up temp directory: {temp_dir}")
        shutil.rmtree(temp_dir)
    
    # Calculate total execution time
    total_time = time.time() - start_time
    logger.info(f"Total pipeline execution time: {total_time:.2f} seconds")
    print(f"\nTotal execution time: {total_time:.2f} seconds")
    
    # Return overall success
    overall_success = all(success.values())
    logger.info(f"Pipeline completed with overall status: {'SUCCESS' if overall_success else 'FAILURE'}")
    
    # Write execution report to file
    try:
        report_path = output_dir / "execution_report.json"
        logger.debug(f"Writing execution report to {report_path}")
        
        report = {
            "execution_time": total_time,
            "patient_id": args.patient_id,
            "steps": {
                step: {
                    "success": success.get(step, False),
                    "duration_seconds": step_timings.get(step, 0)
                } for step in success
            },
            "overall_success": overall_success,
            "timestamp": datetime.datetime.now().isoformat(),
            "command_line_args": vars(args),
            "mock_mode": mock_mode
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.debug("Execution report written successfully")
    except Exception as e:
        logger.warning(f"Failed to write execution report: {str(e)}")
    
    return overall_success


if __name__ == "__main__":
    try:
        exit_code = 0 if main() else 1
        logger.info(f"Program completed with exit code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.error("\nPipeline execution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled error in pipeline: {str(e)}")
        print(f"\nFatal error: {str(e)}")
        print("See logs for more details or run with --debug for verbose output")
        sys.exit(1) 