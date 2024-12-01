"""
Pathling Analytics Service Module.

This module provides integration with the Pathling FHIR analytics engine
for population-level analytics on FHIR data.
"""

import json
import logging
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests

logger = logging.getLogger(__name__)

class PathlingService:
    """Service for FHIR analytics using Pathling.
    
    This class provides methods for starting/stopping the Pathling server,
    importing FHIR data, performing aggregations, extracting datasets, and
    evaluating measures.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        jar_path: Optional[str] = None,
        use_docker: bool = False,
        docker_image: str = "aehrc/pathling:2.1.0",
        timeout: int = 30,
    ):
        """Initialize the Pathling service.
        
        Args:
            host: Hostname where Pathling will be available.
            port: Port where Pathling will be available.
            jar_path: Path to the Pathling server JAR file.
            use_docker: Whether to use Docker for Pathling.
            docker_image: Docker image for Pathling.
            timeout: Timeout in seconds for server operations.
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/fhir"
        self.process = None
        self.container_id = None
        self.use_docker = use_docker
        self.docker_image = docker_image
        self.timeout = timeout
        
        # Find JAR path if not specified
        if not jar_path and not use_docker:
            jar_path = self._find_jar_path()
        
        self.jar_path = jar_path
        
    def _find_jar_path(self) -> str:
        """Find the Pathling server JAR file.
        
        Returns:
            Path to the Pathling server JAR file.
            
        Raises:
            FileNotFoundError: If the JAR file cannot be found.
        """
        # Check common locations
        possible_locations = [
            "/opt/pathling/pathling-server.jar",  # Container default
            "ops/pathling/pathling-server.jar",   # Local repository
            Path.home() / "pathling/pathling-server.jar",  # User home
        ]
        
        for loc in possible_locations:
            if Path(loc).exists():
                return str(loc)
        
        # Check environment variable
        if os.environ.get("PATHLING_JAR"):
            return os.environ["PATHLING_JAR"]
            
        raise FileNotFoundError(
            "Pathling server JAR not found. Please specify the path or use Docker."
        )
    
    def start(self) -> bool:
        """Start the Pathling server.
        
        Returns:
            True if the server was started successfully, False otherwise.
        """
        if self.is_running():
            logger.info("Pathling server is already running")
            return True
            
        if self.use_docker:
            return self._start_docker()
        else:
            return self._start_jar()
    
    def _start_jar(self) -> bool:
        """Start Pathling using the JAR file.
        
        Returns:
            True if the server was started successfully, False otherwise.
        """
        try:
            logger.info(f"Starting Pathling server from JAR: {self.jar_path}")
            
            # Create temporary directory for Pathling data
            self.temp_dir = tempfile.TemporaryDirectory()
            data_dir = Path(self.temp_dir.name) / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Start the process
            self.process = subprocess.Popen(
                ["java", "-jar", self.jar_path, "serve", "--database", str(data_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            
            # Wait for server to start
            return self._wait_for_server()
            
        except Exception as e:
            logger.error(f"Error starting Pathling server: {str(e)}")
            return False
    
    def _start_docker(self) -> bool:
        """Start Pathling using Docker.
        
        Returns:
            True if the server was started successfully, False otherwise.
        """
        try:
            logger.info(f"Starting Pathling server using Docker image: {self.docker_image}")
            
            # Create temporary directory for Pathling data
            self.temp_dir = tempfile.TemporaryDirectory()
            data_dir = Path(self.temp_dir.name) / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Start the container
            result = subprocess.run(
                [
                    "docker", "run", "-d",
                    "-p", f"{self.port}:8080",
                    "-v", f"{data_dir}:/app/database",
                    self.docker_image
                ],
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                logger.error(f"Error starting Docker container: {result.stderr}")
                return False
                
            self.container_id = result.stdout.strip()
            logger.info(f"Started Pathling Docker container: {self.container_id}")
            
            # Wait for server to start
            return self._wait_for_server()
            
        except Exception as e:
            logger.error(f"Error starting Pathling Docker container: {str(e)}")
            return False
    
    def _wait_for_server(self) -> bool:
        """Wait for the server to start.
        
        Returns:
            True if the server started successfully, False otherwise.
        """
        logger.info(f"Waiting for Pathling server to start (timeout: {self.timeout}s)")
        
        for _ in range(self.timeout):
            try:
                response = requests.get(f"{self.base_url}/metadata")
                if response.status_code == 200:
                    logger.info("Pathling server started successfully")
                    return True
            except requests.RequestException:
                pass
                
            time.sleep(1)
            
        logger.error(f"Timed out waiting for Pathling server to start after {self.timeout}s")
        return False
    
    def stop(self) -> bool:
        """Stop the Pathling server.
        
        Returns:
            True if the server was stopped successfully, False otherwise.
        """
        if not self.is_running():
            logger.info("Pathling server is not running")
            return True
            
        try:
            if self.use_docker and self.container_id:
                logger.info(f"Stopping Pathling Docker container: {self.container_id}")
                result = subprocess.run(
                    ["docker", "stop", self.container_id],
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode != 0:
                    logger.error(f"Error stopping Docker container: {result.stderr}")
                    return False
                    
                self.container_id = None
                
            elif self.process:
                logger.info("Stopping Pathling server process")
                self.process.terminate()
                self.process.wait(timeout=10)
                self.process = None
            
            # Clean up temporary directory
            if hasattr(self, 'temp_dir') and self.temp_dir:
                self.temp_dir.cleanup()
                
            logger.info("Pathling server stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Pathling server: {str(e)}")
            return False
    
    def is_running(self) -> bool:
        """Check if the Pathling server is running.
        
        Returns:
            True if the server is running, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/metadata", timeout=1)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def import_data(self, input_path: str) -> bool:
        """Import FHIR data into Pathling.
        
        Args:
            input_path: Path to FHIR data file or directory.
            
        Returns:
            True if the data was imported successfully, False otherwise.
        """
        if not self.is_running():
            logger.error("Pathling server is not running")
            return False
            
        try:
            logger.info(f"Importing data from: {input_path}")
            
            # For simplicity, we're using the import endpoint directly
            # In a real implementation, you might want to use the Pathling CLI
            
            with open(input_path, "rb") as f:
                response = requests.post(
                    f"{self.base_url}/$import",
                    headers={"Content-Type": "application/fhir+ndjson"},
                    data=f,
                )
                
            if response.status_code != 200:
                logger.error(f"Error importing data: {response.text}")
                return False
                
            logger.info("Data imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error importing data: {str(e)}")
            return False
    
    def aggregate(
        self,
        subject: str,
        aggregation: str,
        grouping: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform aggregation on FHIR data.
        
        Args:
            subject: FHIR resource type to aggregate.
            aggregation: Aggregation expression.
            grouping: Grouping expression.
            filter: Filter expression.
            
        Returns:
            Aggregation results.
        """
        if not self.is_running():
            logger.error("Pathling server is not running")
            return {}
            
        try:
            params = {
                "subject": subject,
                "aggregation": aggregation,
            }
            
            if grouping:
                params["grouping"] = grouping
                
            if filter:
                params["filter"] = filter
                
            response = requests.get(
                f"{self.base_url}/{subject}/$aggregate",
                params=params,
            )
            
            if response.status_code != 200:
                logger.error(f"Error performing aggregation: {response.text}")
                return {}
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error performing aggregation: {str(e)}")
            return {}
    
    def extract_dataset(
        self,
        source: str,
        columns: List[str],
        filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """Extract a dataset from FHIR data.
        
        Args:
            source: FHIR resource type to extract from.
            columns: List of columns to extract.
            filter: Filter expression.
            
        Returns:
            Pandas DataFrame containing the extracted data.
        """
        if not self.is_running():
            logger.error("Pathling server is not running")
            return pd.DataFrame()
            
        try:
            params = {
                "source": source,
                "column": columns,
            }
            
            if filter:
                params["filter"] = filter
                
            response = requests.get(
                f"{self.base_url}/{source}/$extract",
                params=params,
            )
            
            if response.status_code != 200:
                logger.error(f"Error extracting dataset: {response.text}")
                return pd.DataFrame()
                
            # Convert the CSV response to a DataFrame
            return pd.read_csv(tempfile.StringIO(response.text))
            
        except Exception as e:
            logger.error(f"Error extracting dataset: {str(e)}")
            return pd.DataFrame()
    
    def evaluate_measure(
        self,
        numerator: str,
        denominator: str,
        subject: str = "Patient",
    ) -> Dict[str, Any]:
        """Evaluate a measure on FHIR data.
        
        Args:
            numerator: FHIRPath expression for the numerator.
            denominator: FHIRPath expression for the denominator.
            subject: FHIR resource type for the subject.
            
        Returns:
            Measure evaluation results.
        """
        if not self.is_running():
            logger.error("Pathling server is not running")
            return {}
            
        try:
            # Create a custom measure using the aggregate endpoint
            numerator_result = self.aggregate(
                subject=subject,
                aggregation=f"count().where({numerator})",
            )
            
            denominator_result = self.aggregate(
                subject=subject,
                aggregation=f"count().where({denominator})",
            )
            
            # Extract the counts
            numerator_count = numerator_result.get("extension", [{}])[0].get("valueInteger", 0)
            denominator_count = denominator_result.get("extension", [{}])[0].get("valueInteger", 0)
            
            # Calculate the ratio
            ratio = numerator_count / denominator_count if denominator_count > 0 else 0
            
            return {
                "numerator": numerator_count,
                "denominator": denominator_count,
                "ratio": ratio,
            }
            
        except Exception as e:
            logger.error(f"Error evaluating measure: {str(e)}")
            return {} 