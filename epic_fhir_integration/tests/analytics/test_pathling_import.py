"""
Tests for Pathling import functionality.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from epic_fhir_integration.analytics.pathling_service import PathlingService

class TestPathlingImport(unittest.TestCase):
    """Test the Pathling import functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment with Docker running."""
        # Check if docker-compose is available
        try:
            result = subprocess.run(
                ["docker-compose", "version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                cls.skip_docker_tests = True
                print("Skipping Docker tests: docker-compose not available")
                return
                
            cls.skip_docker_tests = False
            
            # Create a temp directory for test data
            cls.temp_dir = tempfile.mkdtemp()
            
            # Create docker-compose in test dir
            with open(os.path.join(cls.temp_dir, "docker-compose.yml"), "w") as f:
                f.write("""version: '3'
services:
  pathling:
    image: ghcr.io/aehrc/pathling:6.3.0
    ports:
      - "8080:8080"
    environment:
      - ENABLE_IMPORT=true
""")
            
            # Start Pathling with docker-compose
            subprocess.run(
                ["docker-compose", "-f", os.path.join(cls.temp_dir, "docker-compose.yml"), "up", "-d"],
                check=True
            )
            
            # Wait for Pathling to be ready
            max_retries = 10
            for i in range(max_retries):
                try:
                    health_check = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8080/fhir/metadata"],
                        capture_output=True,
                        text=True
                    )
                    if health_check.stdout.strip() == "200":
                        break
                except subprocess.SubprocessError:
                    pass
                    
                subprocess.run(["sleep", "2"], capture_output=True)
                
        except (subprocess.SubprocessError, FileNotFoundError):
            cls.skip_docker_tests = True
            print("Skipping Docker tests: docker-compose or docker not available")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up the test environment."""
        if not hasattr(cls, 'skip_docker_tests') or not cls.skip_docker_tests:
            # Stop Pathling with docker-compose
            subprocess.run(
                ["docker-compose", "-f", os.path.join(cls.temp_dir, "docker-compose.yml"), "down"],
                check=True
            )
            
            # Remove temp directory
            shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up each test."""
        if hasattr(self.__class__, 'skip_docker_tests') and self.__class__.skip_docker_tests:
            self.skipTest("Docker tests are skipped")
            
        # Create a test data directory
        self.test_data_dir = os.path.join(self.__class__.temp_dir, "test_data")
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Create a test Patient resource
        self.patient = {
            "resourceType": "Patient",
            "id": "test-patient",
            "gender": "male",
            "birthDate": "1970-01-01"
        }
        
        # Create a Bundle with Patient resources
        self.bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": self.patient
                },
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "test-patient-2",
                        "gender": "female",
                        "birthDate": "1980-01-01"
                    }
                }
            ]
        }
        
        # Write the bundle to a file
        with open(os.path.join(self.test_data_dir, "patient.json"), "w") as f:
            json.dump(self.bundle, f)
            
        # Initialize PathlingService
        self.pathling = PathlingService(base_url="http://localhost:8080/fhir")
    
    def test_import_data(self):
        """Test importing data into Pathling."""
        # Import test data
        result = self.pathling.import_data(self.test_data_dir)
        self.assertTrue(result, "Import should succeed")
        
        # Verify import by querying
        command = [
            "curl", "-s", "http://localhost:8080/fhir/Patient?_count=100",
            "-H", "Accept: application/json"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "Query should succeed")
        
        # Parse response
        response = json.loads(result.stdout)
        
        # Verify that we have entries
        self.assertIn("entry", response, "Response should have entries")
        self.assertGreaterEqual(len(response["entry"]), 1, "Should have at least one Patient")
        
    def test_synthetic_loader(self):
        """Test the synthetic loader."""
        # Create a test NDJSON directory
        ndjson_dir = Path(self.test_data_dir) / "ndjson" / "patient"
        ndjson_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test NDJSON file
        with open(ndjson_dir / "test.ndjson", "w") as f:
            f.write(json.dumps(self.patient) + "\n")
            
        # Test the synthetic loader
        self.pathling._synthetic_load(ndjson_dir)
        
        # No assertion - we're just testing that it doesn't crash

if __name__ == "__main__":
    unittest.main() 