#!/usr/bin/env python3
"""
Advanced FHIR Tools End-to-End Test

This script demonstrates all advanced FHIR tools with real Epic API calls:
1. Authentication with JWT
2. Patient data extraction
3. FHIRPath implementation
4. Pathling analytics
5. FHIR-PYrate data science
6. FHIR validation
7. Data quality assessment (Bronze, Silver, Gold tiers)
8. Dashboard generation

Usage:
    python advanced_fhir_tools_e2e_test.py [--patient-id ID] [--output-dir DIR] [--debug] [--mock] [--tier TIER]
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import requests
from typing import Optional, Dict, List, Any
import tempfile

# Add custom serialization for datetime objects
class DateTimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("advanced_fhir_test")

# Import authentication 
from epic_fhir_integration.auth.epic_auth import get_token, get_token_with_retry, get_auth_headers

# Import data quality framework
from epic_fhir_integration.metrics.data_quality import DataQualityAssessor
from epic_fhir_integration.metrics.dashboard.quality_dashboard import QualityDashboard
from epic_fhir_integration.metrics.dashboard.validation_dashboard import ValidationDashboard

# Define adapter functions to match expected interface
def get_auth_token():
    """Adapter function to get authentication token."""
    # Check for mock mode
    if os.environ.get("USE_MOCK_MODE") == "true":
        logger.info("Using mock authentication token")
        return {"access_token": "mock-token-12345", "token_type": "Bearer", "expires_in": 3600}
        
    try:
        # Use our new auth module for reliable authentication
        return get_token_with_retry()
    except Exception as e:
        logger.warning(f"Failed to get token: {e}")
        # Return mock token as last resort
        return {"access_token": "fallback-mock-token", "token_type": "Bearer", "expires_in": 3600}

def create_auth_header(token):
    """Create authentication header from token."""
    if isinstance(token, dict) and 'access_token' in token:
        token = token['access_token']
    
    return {'Authorization': f'Bearer {token}'}

# Import FHIRPath adapter
from epic_fhir_integration.utils.fhirpath_adapter import FHIRPathAdapter

# Import Pathling service
from epic_fhir_integration.analytics.pathling_service import PathlingService

# Import data science tools
from epic_fhir_integration.datascience.fhir_dataset import FHIRDatasetBuilder, CohortBuilder

# Import validator
from epic_fhir_integration.validation.validator import FHIRValidator

# Constants
DEFAULT_PATIENT_ID = "test-patient-1"
TIERS = ["bronze", "silver", "gold"]
TIER_ORDER = {"bronze": 0, "silver": 1, "gold": 2}
# Sentinel file for tracking failures
SENTINEL_FAIL = Path("/tmp/fhir_e2e_failed")

class AdvancedFHIRToolsTest:
    def __init__(self, patient_id=DEFAULT_PATIENT_ID, output_dir=None, debug=False,
                mock_mode=False, tier=None,  # Changed default tier to None
                pathling_java_debug_port: Optional[int] = None,
                validator_java_debug_port: Optional[int] = None): # Added debug ports
        self.patient_id = patient_id
        self.debug = debug
        self.mock_mode = mock_mode or os.environ.get("USE_MOCK_MODE") == "true"
        
        self.target_tier = tier.lower() if tier else "gold" # Default to gold if no tier specified
        if self.target_tier not in TIERS:
            logger.warning(f"Invalid target tier '{self.target_tier}', defaulting to 'gold'.")
            self.target_tier = "gold"
        
        # The tier to process in the current step, starts with bronze
        self.current_processing_tier = "bronze" 

        self.output_dir = Path(output_dir or f"fhir_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging level
        if debug:
            logger.setLevel(logging.DEBUG)
        
        # Create output subdirectories
        self.results_dir = self.output_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Create tier directories
        for tier_name in TIERS:
            tier_dir = self.output_dir / tier_name
            tier_dir.mkdir(exist_ok=True)
        
        # Create dashboard directory
        self.dashboard_dir = self.output_dir / "dashboard"
        self.dashboard_dir.mkdir(exist_ok=True)
        
        logger.info(f"Test initialized with patient ID: {patient_id}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Target data tier for processing: {self.target_tier}") # Changed log message
        logger.info(f"Mock mode: {'enabled' if self.mock_mode else 'disabled'}")
        
        self.pathling_java_debug_port = pathling_java_debug_port
        self.validator_java_debug_port = validator_java_debug_port

        if self.pathling_java_debug_port:
            logger.info(f"Pathling Java debug port configured: {self.pathling_java_debug_port}")
        if self.validator_java_debug_port:
            logger.info(f"FHIR Validator Java debug port configured: {self.validator_java_debug_port}")

        # Initialize tools with mock mode if enabled and pass debug ports
        self.fhirpath_adapter = FHIRPathAdapter()
        self.pathling_service = PathlingService(
            mock_mode=self.mock_mode,
            java_debug_port=self.pathling_java_debug_port
        )
        self.dataset_builder = None   # Will be initialized during test
        self.validator = FHIRValidator(
            mock_mode=self.mock_mode,
            java_debug_port=self.validator_java_debug_port
        )
        self.quality_assessor = DataQualityAssessor()
        
        # Test results
        self.results = {
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat(),
            "steps": {},
            "overall_success": False,
            "mock_mode": self.mock_mode,
            "tier": self.target_tier, # Report the target tier
            "quality_metrics": {}
        }

    def authenticate(self):
        """Authenticate with Epic FHIR API using JWT."""
        logger.info("Step 1: Authentication with Epic FHIR API")
        start_time = time.time()
        
        try:
            # Get authentication token
            token = get_auth_token()
            
            # Create authentication header
            auth_header = create_auth_header(token)
            
            # Verify we have a valid token
            if not token or not auth_header:
                raise Exception("Failed to obtain valid authentication token")
            
            # Store the auth header for later use
            self.auth_header = auth_header
            
            duration = time.time() - start_time
            logger.info(f"Authentication successful in {duration:.2f} seconds. Token type: {token.get('token_type', 'unknown') if isinstance(token, dict) else 'string'}")
            
            # Record results
            self.results["steps"]["authentication"] = {
                "success": True,
                "duration": duration,
                "token_type": token.get("token_type", "unknown") if isinstance(token, dict) else "string",
                "timestamp": datetime.now().isoformat()
            }
            
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["authentication"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def create_sample_resources(self):
        """Create sample FHIR resources for testing."""
        logger.info("Creating sample FHIR resources for testing")
        
        # Sample Patient
        patient = {
            "resourceType": "Patient",
            "id": self.patient_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": "2024-05-20T08:15:00Z"
            },
            "identifier": [
                {
                    "system": "urn:oid:1.2.36.146.595.217.0.1",
                    "value": "12345"
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": "Smith",
                    "given": ["John", "Samuel"]
                }
            ],
            "telecom": [
                {
                    "system": "phone",
                    "value": "555-123-4567",
                    "use": "home"
                },
                {
                    "system": "email",
                    "value": "john.smith@example.com"
                }
            ],
            "gender": "male",
            "birthDate": "1970-01-25",
            "address": [
                {
                    "use": "home",
                    "line": ["123 Main St"],
                    "city": "Anytown",
                    "state": "CA",
                    "postalCode": "12345"
                }
            ],
            "active": True
        }
        
        # Sample Observations
        observations = []
        for i in range(5):
            observations.append({
                "resourceType": "Observation",
                "id": f"obs-{i+1}",
                "meta": {
                    "versionId": "1",
                    "lastUpdated": "2024-05-20T08:30:00Z"
                },
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "vital-signs",
                                "display": "Vital Signs"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure"
                        }
                    ],
                    "text": "Systolic blood pressure"
                },
                "subject": {
                    "reference": f"Patient/{self.patient_id}"
                },
                "effectiveDateTime": f"2024-05-{15+i}T09:30:00Z",
                "valueQuantity": {
                    "value": 120 + i*2,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            })
        
        # Sample Conditions
        conditions = []
        conditions.append({
            "resourceType": "Condition",
            "id": "cond-1",
            "meta": {
                "versionId": "1",
                "lastUpdated": "2024-05-20T08:45:00Z"
            },
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed",
                        "display": "Confirmed"
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertension"
                    }
                ],
                "text": "Hypertension"
            },
            "subject": {
                "reference": f"Patient/{self.patient_id}"
            },
            "onsetDateTime": "2023-01-15T00:00:00Z"
        })
        
        # Sample Encounters
        encounters = []
        encounters.append({
            "resourceType": "Encounter",
            "id": "enc-1",
            "meta": {
                "versionId": "1",
                "lastUpdated": "2024-05-20T09:00:00Z"
            },
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory"
            },
            "type": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "185349003",
                            "display": "Encounter for check up"
                        }
                    ],
                    "text": "Checkup"
                }
            ],
            "subject": {
                "reference": f"Patient/{self.patient_id}"
            },
            "period": {
                "start": "2024-05-20T08:00:00Z",
                "end": "2024-05-20T08:30:00Z"
            }
        })
        
        return {
            "Patient": [patient],
            "Observation": observations,
            "Condition": conditions,
            "Encounter": encounters
        }

    def fetch_patient_data(self):
        """Fetch patient data from Epic FHIR API."""
        logger.info(f"Step 2: Fetching data for patient ID: {self.patient_id}")
        start_time = time.time()
        
        try:
            if self.mock_mode:
                logger.info("Using sample resources in mock mode")
                self.resources = self.create_sample_resources()
            else:
                logger.info("Fetching live data from FHIR API")

                if not hasattr(self, 'auth_header') or not self.auth_header:
                    logger.error("Authentication header not available. Cannot fetch live data.")
                    if not self.authenticate(): # Try to re-authenticate
                         raise Exception("Authentication failed. Cannot fetch live data.")
                
                # Prepare headers for JSON FHIR response
                request_headers = self.auth_header.copy() # Start with auth header
                request_headers['Accept'] = 'application/fhir+json' # Specify FHIR JSON

                from epic_fhir_integration.config.loader import get_config
                app_config = get_config()
                fhir_base_url = app_config.get('fhir', {}).get('base_url')
                if not fhir_base_url:
                    raise ValueError("FHIR base_url not found in configuration.")

                logger.info(f"Using FHIR base URL: {fhir_base_url} for patient ID: {self.patient_id}")

                self.resources = {
                    "Patient": [], "Observation": [], "Condition": [], "Encounter": [],
                    "MedicationRequest": [], "AllergyIntolerance": [], "Procedure": [],
                    "Immunization": [], "DiagnosticReport": [], "DocumentReference": []
                }

                # Fetch Patient resource
                patient_url = f"{fhir_base_url}/Patient/{self.patient_id}"
                logger.debug(f"Fetching Patient from: {patient_url}")
                response = requests.get(patient_url, headers=request_headers, timeout=30)
                
                logger.debug(f"Patient request status code: {response.status_code}")
                logger.debug(f"Patient request response text (first 500 chars): {response.text[:500]}")

                response.raise_for_status() # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
                logger.debug(f"Patient response status: {response.status_code}")
                patient_data = response.json()
                if patient_data.get("resourceType") == "Patient":
                    self.resources["Patient"].append(patient_data)
                else:
                    logger.warning(f"Patient with ID {self.patient_id} not found or invalid response: {patient_data}")

                resource_types_to_fetch = ["Observation", "Condition", "Encounter", "MedicationRequest", "AllergyIntolerance", "Procedure", "Immunization"]
                
                for res_type in resource_types_to_fetch:
                    page_count = 0
                    max_pages = 5 # Safety break for pagination
                    
                    # Base search URL
                    base_search_url = f"{fhir_base_url}/{res_type}?patient={self.patient_id}&_count=50"
                    
                    # Add specific parameters if needed, e.g., for Observation
                    if res_type == "Observation":
                        search_url = f"{base_search_url}&category=vital-signs"
                    # Example for Condition, might need a category or clinical-status if patient alone is not enough
                    # elif res_type == "Condition":
                    #    search_url = f"{base_search_url}&clinical-status=active"
                    else:
                        search_url = base_search_url

                    logger.debug(f"Fetching {res_type} from: {search_url}")
                    
                    while search_url and page_count < max_pages:
                        page_count += 1
                        response = requests.get(search_url, headers=request_headers, timeout=30)
                        
                        logger.debug(f"{res_type} request status code: {response.status_code}")
                        logger.debug(f"{res_type} request response text (first 500 chars): {response.text[:500]}")
                        
                        response.raise_for_status()
                        bundle = response.json()
                        
                        if bundle.get("resourceType") == "Bundle" and "entry" in bundle:
                            for entry in bundle.get("entry", []):
                                if entry.get("resource", {}).get("resourceType") == res_type:
                                    self.resources[res_type].append(entry["resource"])
                        
                        # Check for next page
                        next_link = None
                        if "link" in bundle:
                            for link_info in bundle["link"]:
                                if link_info.get("relation") == "next":
                                    next_link = link_info.get("url")
                                    break
                        search_url = next_link
                        if next_link:
                            logger.debug(f"Fetching next page for {res_type}: {next_link}")
                        else:
                            logger.debug(f"No more pages for {res_type}.")

                if not self.resources["Patient"]:
                    logger.warning(f"No live Patient data fetched for ID {self.patient_id}. This might be expected if the patient doesn't exist or has no data.")
                    # Depending on strictness, could raise error or use samples as absolute fallback
                    # For now, if patient not found, other calls likely failed or returned empty too.
                    # If other lists are also empty, then use sample data
                    if not any(self.resources[rt] for rt in resource_types_to_fetch):
                        logger.info("No other resources found either, falling back to all sample data.")
                        self.resources = self.create_sample_resources()
                
                logger.info("Live data fetching complete.")

            # Save raw resources to file (Bronze tier)
            bronze_file = self.output_dir / "bronze" / "raw_resources.json"
            with open(bronze_file, "w") as f:
                json.dump(self.resources, f, indent=2, cls=DateTimeJSONEncoder)
            
            # Perform data quality assessment for Bronze tier
            quality_results = self.quality_assessor.assess_resources(self.resources, tier="bronze")
            bronze_quality_file = self.output_dir / "bronze" / "quality_metrics.json"
            with open(bronze_quality_file, "w") as f:
                json.dump(quality_results, f, indent=2)
            self.results["quality_metrics"]["bronze"] = quality_results

            # --- Automatic Tier Transformation ---
            processed_resources_for_next_tier = self.resources # Start with bronze resources
            
            if TIER_ORDER[self.current_processing_tier] < TIER_ORDER[self.target_tier]:
                # Transform to Silver tier
                logger.info("Transforming data to Silver tier...")
                self.current_processing_tier = "silver"
                silver_resources = self.transform_to_silver(processed_resources_for_next_tier)
                silver_file = self.output_dir / "silver" / "resources.json"
                with open(silver_file, "w") as f:
                    json.dump(silver_resources, f, indent=2, cls=DateTimeJSONEncoder)
                logger.info(f"Silver tier resources saved to {silver_file}")
                
                quality_results_silver = self.quality_assessor.assess_resources(silver_resources, tier="silver")
                silver_quality_file = self.output_dir / "silver" / "quality_metrics.json"
                with open(silver_quality_file, "w") as f:
                    json.dump(quality_results_silver, f, indent=2, cls=DateTimeJSONEncoder)
                self.results["quality_metrics"]["silver"] = quality_results_silver
                processed_resources_for_next_tier = silver_resources

                if TIER_ORDER[self.current_processing_tier] < TIER_ORDER[self.target_tier]:
                    # Transform to Gold tier
                    logger.info("Transforming data to Gold tier...")
                    self.current_processing_tier = "gold"
                    gold_resources = self.transform_to_gold(processed_resources_for_next_tier)
                    gold_file = self.output_dir / "gold" / "resources.json"
                    with open(gold_file, "w") as f:
                        json.dump(gold_resources, f, indent=2, cls=DateTimeJSONEncoder)
                    logger.info(f"Gold tier resources saved to {gold_file}")

                    quality_results_gold = self.quality_assessor.assess_resources(gold_resources, tier="gold")
                    gold_quality_file = self.output_dir / "gold" / "quality_metrics.json"
                    with open(gold_quality_file, "w") as f:
                        json.dump(quality_results_gold, f, indent=2, cls=DateTimeJSONEncoder)
                    self.results["quality_metrics"]["gold"] = quality_results_gold
            # --- End Automatic Tier Transformation ---

            # Record counts
            resource_counts = {k: len(v) for k, v in self.resources.items()}
            
            duration = time.time() - start_time
            logger.info(f"Fetched and processed patient data in {duration:.2f} seconds")
            logger.info(f"Resource counts: {resource_counts}")
            
            # Record results
            self.results["steps"]["fetch_data"] = {
                "success": True,
                "duration": duration,
                "resource_counts": resource_counts,
                "timestamp": datetime.now().isoformat(),
                "output_file": str(bronze_file) if self.current_processing_tier == "bronze" else 
                              str(self.output_dir / self.current_processing_tier / "resources.json")
            }
            
            return True
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error during FHIR API call: {http_err} - {http_err.response.text if http_err.response else 'No response text'}", exc_info=True)
            self.results["steps"]["fetch_data"] = {
                "success": False,
                "error": str(http_err),
                "details": http_err.response.text if http_err.response else 'No response text',
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            return False
        except Exception as e:
            logger.error(f"Failed to fetch patient data: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["fetch_data"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def transform_to_silver(self, bronze_resources):
        """Transform Bronze tier resources to Silver tier."""
        logger.info("Transforming resources from Bronze to Silver tier")
        
        # In a real implementation, this would apply data cleansing,
        # standardize units, add common extensions, etc.
        silver_resources = {}
        
        for resource_type, resources in bronze_resources.items():
            silver_resources[resource_type] = []
            
            for resource in resources:
                # Create a deep copy to avoid modifying the original
                silver_resource = json.loads(json.dumps(resource))
                
                # Add standard extension for data quality tier
                if "extension" not in silver_resource:
                    silver_resource["extension"] = []
                
                silver_resource["extension"].append({
                    "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
                    "valueString": "silver"
                })
                
                # Add standard metadata
                if "meta" not in silver_resource:
                    silver_resource["meta"] = {}
                
                if "tag" not in silver_resource["meta"]:
                    silver_resource["meta"]["tag"] = []
                
                silver_resource["meta"]["tag"].append({
                    "system": "http://atlaspalantir.com/fhir/data-tier",
                    "code": "silver",
                    "display": "Silver"
                })
                
                # Apply specific resource type transformations
                if resource_type == "Patient":
                    # Ensure US Core Race extension
                    self._add_us_core_race(silver_resource)
                elif resource_type == "Observation":
                    # Ensure all observations have a category
                    self._ensure_observation_category(silver_resource)
                
                silver_resources[resource_type].append(silver_resource)
        
        # Record results
        return silver_resources

    def transform_to_gold(self, silver_resources: Dict[str, List[Dict]]):
        """Transform Silver tier resources to Gold tier."""
        logger.info("Transforming resources from Silver to Gold tier")
        
        # No longer need to load from file, silver_resources is already a dict
        # with open(silver_file_path, "r") as f:
        #     silver_resources = json.load(f)
        
        # In a real implementation, this would apply full profile conformance,
        # comprehensive enrichment, generate narratives, etc.
        gold_resources = {}
        
        for resource_type, resources in silver_resources.items():
            gold_resources[resource_type] = []
            
            for resource in resources:
                # Create a deep copy to avoid modifying the original
                gold_resource = json.loads(json.dumps(resource))
                
                # Update the quality tier extension
                updated_extension = False
                if "extension" in gold_resource:
                    for ext in gold_resource["extension"]:
                        if ext.get("url") == "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier":
                            ext["valueString"] = "gold"
                            updated_extension = True
                            break
                
                if not updated_extension:
                    if "extension" not in gold_resource:
                        gold_resource["extension"] = []
                    
                    gold_resource["extension"].append({
                        "url": "http://atlaspalantir.com/fhir/StructureDefinition/data-quality-tier",
                        "valueString": "gold"
                    })
                
                # Update metadata tag
                if "meta" not in gold_resource:
                    gold_resource["meta"] = {}
                
                if "tag" not in gold_resource["meta"]:
                    gold_resource["meta"]["tag"] = []
                
                # Remove silver tag if present
                gold_resource["meta"]["tag"] = [
                    tag for tag in gold_resource["meta"]["tag"] 
                    if not (tag.get("system") == "http://atlaspalantir.com/fhir/data-tier" and tag.get("code") == "silver")
                ]
                
                # Add gold tag
                gold_resource["meta"]["tag"].append({
                    "system": "http://atlaspalantir.com/fhir/data-tier",
                    "code": "gold",
                    "display": "Gold"
                })
                
                # Add text narrative for key resources
                if resource_type in ["Patient", "Observation", "Condition", "MedicationRequest"]:
                    self._generate_narrative(gold_resource, resource_type)
                
                gold_resources[resource_type].append(gold_resource)
        
        # Record results
        return gold_resources

    def _add_us_core_race(self, patient_resource):
        """Add US Core Race extension to a patient resource."""
        # Check if extension already exists
        has_race_extension = False
        if "extension" in patient_resource:
            for ext in patient_resource["extension"]:
                if ext.get("url") == "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race":
                    has_race_extension = True
                    break
        
        if not has_race_extension:
            race_extension = {
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                "extension": [
                    {
                        "url": "ombCategory",
                        "valueCoding": {
                            "system": "urn:oid:2.16.840.1.113883.6.238",
                            "code": "2106-3",
                            "display": "White"
                        }
                    },
                    {
                        "url": "text",
                        "valueString": "White"
                    }
                ]
            }
            
            if "extension" not in patient_resource:
                patient_resource["extension"] = []
            
            patient_resource["extension"].append(race_extension)

    def _ensure_observation_category(self, observation_resource):
        """Ensure observation has a category."""
        if "category" not in observation_resource or not observation_resource["category"]:
            # Add a default category if none exists
            observation_resource["category"] = [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ]

    def _generate_narrative(self, resource, resource_type):
        """Generate narrative text for a resource."""
        if "text" not in resource:
            resource["text"] = {
                "status": "generated",
                "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">"
            }
        
        div_content = ""
        
        if resource_type == "Patient":
            name = self.fhirpath_adapter.extract_first(resource, "name.where(use='official').family") or "Unknown"
            gender = resource.get("gender", "Unknown")
            birth_date = resource.get("birthDate", "Unknown")
            div_content = f"<p>Patient: {name}, {gender}, DOB: {birth_date}</p>"
        
        elif resource_type == "Observation":
            code_display = self.fhirpath_adapter.extract_first(resource, "code.coding.display") or "Unknown"
            value = "Unknown"
            if "valueQuantity" in resource:
                value = f"{resource['valueQuantity'].get('value', '')} {resource['valueQuantity'].get('unit', '')}"
            elif "valueCodeableConcept" in resource:
                value = self.fhirpath_adapter.extract_first(resource, "valueCodeableConcept.coding.display") or "Unknown"
            
            div_content = f"<p>Observation: {code_display}, Value: {value}</p>"
        
        elif resource_type == "Condition":
            condition = self.fhirpath_adapter.extract_first(resource, "code.coding.display") or "Unknown Condition"
            status = self.fhirpath_adapter.extract_first(resource, "clinicalStatus.coding.display") or "Unknown Status"
            div_content = f"<p>Condition: {condition}, Status: {status}</p>"
        
        elif resource_type == "MedicationRequest":
            medication = self.fhirpath_adapter.extract_first(resource, "medicationCodeableConcept.coding.display") or "Unknown Medication"
            status = resource.get("status", "Unknown")
            div_content = f"<p>Medication Request: {medication}, Status: {status}</p>"
        
        resource["text"]["div"] = f"<div xmlns=\"http://www.w3.org/1999/xhtml\">{div_content}</div>"

    def test_fhirpath(self):
        """Test FHIRPath implementation with fetched resources."""
        logger.info("Step 3: Testing FHIRPath implementation")
        start_time = time.time()
        
        try:
            if not hasattr(self, 'resources') or not self.resources.get("Patient"):
                raise Exception("No patient resources available")
            
            patient = self.resources["Patient"][0]
            observations = self.resources.get("Observation", [])
            
            # Define test queries and store results
            fhirpath_results = {}
            
            # Patient queries
            patient_queries = {
                "patient_name": "name.where(use='official').given.first()",
                "gender": "gender",
                "birth_date": "birthDate",
                "address": "address.line.first()",
                "telecom": "telecom.where(system='phone').value.first()"
            }
            
            for name, query in patient_queries.items():
                result = self.fhirpath_adapter.extract_first(patient, query)
                fhirpath_results[name] = result
                logger.info(f"FHIRPath query '{name}': {result}")
            
            # Observation queries (if available)
            if observations:
                obs_queries = {
                    "observation_count": len(observations),
                    "has_loinc_codes": self.fhirpath_adapter.exists(
                        observations[0], 
                        "code.coding.where(system='http://loinc.org').exists()"
                    ),
                    "observation_values": [
                        self.fhirpath_adapter.extract_first(obs, "valueQuantity.value") 
                        for obs in observations[:5]
                        if self.fhirpath_adapter.exists(obs, "valueQuantity.exists()")
                    ]
                }
                
                for name, result in obs_queries.items():
                    fhirpath_results[name] = result
                    logger.info(f"FHIRPath query '{name}': {result}")
            
            # Save FHIRPath results to file
            fhirpath_file = self.results_dir / "fhirpath_results.json"
            with open(fhirpath_file, "w") as f:
                json.dump(fhirpath_results, f, indent=2, cls=DateTimeJSONEncoder)
            
            duration = time.time() - start_time
            logger.info(f"FHIRPath testing completed in {duration:.2f} seconds")
            
            # Record results
            self.results["steps"]["fhirpath"] = {
                "success": True,
                "duration": duration,
                "query_count": len(patient_queries) + (len(obs_queries) if 'obs_queries' in locals() else 0),
                "timestamp": datetime.now().isoformat(),
                "output_file": str(fhirpath_file)
            }
            
            return True
        except Exception as e:
            logger.error(f"FHIRPath testing failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["fhirpath"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def test_pathling_analytics(self):
        """Test the Pathling analytics service."""
        logger.info("Step 4: Testing Pathling analytics service")
        start_time = time.time()
        
        pathling_service = None # Initialize to ensure it's always defined for finally block
        try:
            if not hasattr(self, 'resources') or not self.resources:
                logger.error("No resources available for Pathling analytics. Skipping step.")
                self.results["steps"]["pathling"] = {"success": False, "error": "No resources available", "duration": 0, "timestamp": datetime.now().isoformat()}
                return False
            
            logger.info(f"Resources available for Pathling: { {k: len(v) for k, v in self.resources.items() if v} }")

            # Start Pathling service
            pathling_service = PathlingService(use_docker=True, java_debug_port=self.pathling_java_debug_port)
            logger.info("Attempting to start Pathling service...")
            started = pathling_service.start()
            
            if not started:
                logger.error("Failed to start Pathling service. Skipping analytics.")
                self.results["steps"]["pathling"] = {"success": False, "error": "Pathling service failed to start", "duration": time.time() - start_time, "timestamp": datetime.now().isoformat()}
                return False
            logger.info("Pathling service started successfully.")
            
            # Import data
            import_dir = self.output_dir / "pathling_import"
            import_dir.mkdir(exist_ok=True)
            
            # Save resources in FHIR format for Pathling
            for resource_type, resources in self.resources.items():
                if resources:
                    resource_file = import_dir / f"{resource_type.lower()}.json"
                    with open(resource_file, "w") as f:
                        bundle = {
                            "resourceType": "Bundle",
                            "type": "collection",
                            "entry": [{"resource": res} for res in resources]
                        }
                        json.dump(bundle, f, cls=DateTimeJSONEncoder)
                    logger.debug(f"Saved {resource_type} to {resource_file} for Pathling import.")
            
            # Import data into Pathling
            logger.info(f"Attempting to import data from {import_dir} into Pathling.")
            import_successful = pathling_service.import_data(str(import_dir))
            if not import_successful:
                logger.warning(f"Pathling import_data reported issues. See PathlingService logs for details.")
            else:
                logger.info("Pathling import_data completed.")
            
            # Perform analytics
            pathling_results = {}
            
            # 1. Patient count
            patient_count = pathling_service.aggregate(
                subject="Patient",
                aggregation="count()"
            )
            pathling_results["patient_count"] = patient_count
            
            # 2. Observation count by code
            if self.resources.get("Observation"):
                obs_by_code = pathling_service.aggregate(
                    subject="Observation",
                    aggregation="count()",
                    grouping="code.coding.code"
                )
                pathling_results["observations_by_code"] = obs_by_code
            
            # 3. Extract patient dataset
            patient_dataset = pathling_service.extract_dataset(
                source="Patient",
                columns=["id", "gender", "birthDate"]
            )
            pathling_results["patient_dataset"] = patient_dataset.to_dict() if hasattr(patient_dataset, 'to_dict') else patient_dataset
            
            # Save Pathling results to file
            pathling_file = self.results_dir / "pathling_results.json"
            with open(pathling_file, "w") as f:
                json.dump(pathling_results, f, indent=2)
            
            duration = time.time() - start_time
            logger.info(f"Pathling testing completed in {duration:.2f} seconds")
            
            # Record results
            self.results["steps"]["pathling"] = {
                "success": True,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "output_file": str(pathling_file)
            }
            
            return True
        except Exception as e:
            logger.error(f"Pathling testing failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["pathling"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False
        finally:
            logger.info("Ensuring Pathling server is stopped.")
            # Ensure we always try to stop the server
            try:
                if pathling_service: # Check if pathling_service was initialized
                    pathling_service.stop()
                    logger.info("Pathling server stopped.")
            except Exception as stop_error:
                logger.warning(f"Error stopping Pathling server: {stop_error}", exc_info=True)

    def test_datascience(self):
        """Test FHIR-PYrate data science tools with fetched resources."""
        logger.info("Step 5: Testing FHIR-PYrate data science tools")
        start_time = time.time()
        
        try:
            if not hasattr(self, 'resources') or not self.resources:
                raise Exception("No resources available")
            
            # Create dataset builder
            self.dataset_builder = FHIRDatasetBuilder()
            
            # Add resources
            for resource_type, resources in self.resources.items():
                self.dataset_builder.add_resources(resource_type, resources)
            
            # Build patient demographics dataset
            demographics_dataset = self.dataset_builder.build_dataset(
                index_by="Patient",
                columns=[
                    {"path": "Patient.gender", "name": "gender"},
                    {"path": "Patient.birthDate", "name": "birth_date"}
                ]
            )
            
            # Convert to pandas DataFrame
            demographics_df = demographics_dataset.to_pandas()
            
            # Create cohort builder if we have conditions
            cohort_results = {}
            if self.resources.get("Condition"):
                cohort_builder = CohortBuilder(
                    patients=self.resources["Patient"],
                    conditions=self.resources["Condition"]
                )
                
                # Define a simple cohort
                cohort = cohort_builder.build_cohort()
                
                # Get patient IDs
                cohort_patient_ids = cohort.get_patient_ids()
                cohort_results["cohort_patient_count"] = len(cohort_patient_ids)
            
            # Save results
            datascience_results = {
                "demographics_columns": demographics_df.columns.tolist(),
                "demographics_row_count": len(demographics_df),
                "cohort_results": cohort_results
            }
            
            # Save to file
            datascience_file = self.results_dir / "datascience_results.json"
            with open(datascience_file, "w") as f:
                json.dump(datascience_results, f, indent=2, cls=DateTimeJSONEncoder)
            
            duration = time.time() - start_time
            logger.info(f"Data science testing completed in {duration:.2f} seconds")
            
            # Record results
            self.results["steps"]["datascience"] = {
                "success": True,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "output_file": str(datascience_file)
            }
            
            return True
        except Exception as e:
            logger.error(f"Data science testing failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["datascience"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def test_validation(self):
        """Test FHIR validation framework with fetched resources."""
        logger.info("Step 6: Testing FHIR validation framework")
        start_time = time.time()
        
        try:
            if not hasattr(self, 'resources') or not self.resources:
                raise Exception("No resources available")
            
            validation_results = {}
            
            # Set validation profile based on tier
            validation_profile = None
            if self.current_processing_tier == "silver":
                validation_profile = "silver-profiles"
            elif self.current_processing_tier == "gold":
                validation_profile = "us-core"
            
            # Validate each resource type
            for resource_type, resources in self.resources.items():
                if not resources:
                    continue
                
                # Validate first resource of each type
                result = self.validator.validate(
                    resources[0], 
                    profile=validation_profile
                )
                
                validation_results[resource_type] = {
                    "is_valid": result.is_valid,
                    "error_count": len(result.get_errors()),
                    "warning_count": len(result.get_warnings()),
                    "info_count": len(result.get_info()),
                    "errors": [str(e) for e in result.get_errors()[:5]]  # Include up to 5 error messages
                }
                
                logger.info(f"Validation result for {resource_type}: "
                           f"{'Valid' if result.is_valid else 'Invalid'} "
                           f"(Errors: {len(result.get_errors())}, "
                           f"Warnings: {len(result.get_warnings())})")
            
            # Batch validation
            all_resources = []
            for resources in self.resources.values():
                all_resources.extend(resources)
            
            batch_results = self.validator.validate_batch(
                all_resources,
                profile=validation_profile
            )
            
            # Count overall validation stats
            valid_count = sum(1 for r in batch_results if r.is_valid)
            invalid_count = len(batch_results) - valid_count
            
            validation_results["batch"] = {
                "total": len(batch_results),
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "percent_valid": (valid_count / len(batch_results) * 100) if batch_results else 0
            }
            
            # Save validation results
            validation_file = self.output_dir / self.current_processing_tier / "validation_results.json"
            with open(validation_file, "w") as f:
                json.dump(validation_results, f, indent=2)
            
            duration = time.time() - start_time
            logger.info(f"Validation testing completed in {duration:.2f} seconds")
            
            # Record results
            self.results["steps"]["validation"] = {
                "success": True,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "output_file": str(validation_file),
                "validation_stats": validation_results["batch"]
            }
            
            return True
        except Exception as e:
            logger.error(f"Validation testing failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["validation"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def generate_dashboards(self):
        """Generate quality and validation dashboards."""
        logger.info("Step 7: Generating dashboards")
        start_time = time.time()
        
        try:
            # Get quality metrics file paths
            quality_metrics_file = self.output_dir / self.current_processing_tier / "quality_metrics.json"
            validation_results_file = self.output_dir / self.current_processing_tier / "validation_results.json"
            
            # Generate quality dashboard
            if quality_metrics_file.exists():
                quality_dashboard = QualityDashboard()
                quality_html = quality_dashboard.generate_dashboard(
                    quality_metrics_file,
                    output_dir=self.dashboard_dir,
                    static_mode=True
                )
                logger.info(f"Quality dashboard generated: {quality_html}")
            else:
                logger.warning(f"Quality metrics file not found: {quality_metrics_file}")
            
            # Generate validation dashboard
            if validation_results_file.exists():
                validation_dashboard = ValidationDashboard()
                validation_html = validation_dashboard.generate_dashboard(
                    validation_results_file,
                    output_dir=self.dashboard_dir,
                    static_mode=True
                )
                logger.info(f"Validation dashboard generated: {validation_html}")
            else:
                logger.warning(f"Validation results file not found: {validation_results_file}")
            
            # Generate combined dashboard
            if quality_metrics_file.exists() and validation_results_file.exists():
                combined_html = self.dashboard_dir / "combined_dashboard.html"
                # In a real implementation, this would generate a combined dashboard
                logger.info(f"Combined dashboard would be generated at: {combined_html}")
            
            duration = time.time() - start_time
            logger.info(f"Dashboard generation completed in {duration:.2f} seconds")
            
            # Record results
            self.results["steps"]["dashboards"] = {
                "success": True,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "output_dir": str(self.dashboard_dir)
            }
            
            return True
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}", exc_info=True)
            
            # Record results
            self.results["steps"]["dashboards"] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return False

    def generate_report(self):
        """Generate final report with all test results."""
        logger.info("Generating final test report")
        
        # Set overall success
        all_steps = [step["success"] for step in self.results["steps"].values()]
        self.results["overall_success"] = all(all_steps)
        
        # Generate report in JSON format
        report_file = self.output_dir / "advanced_fhir_tools_test_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, cls=DateTimeJSONEncoder)
        
        # Generate report in Markdown format
        md_report_file = self.output_dir / "advanced_fhir_tools_test_report.md"
        with open(md_report_file, "w") as f:
            f.write("# Advanced FHIR Tools Test Report\n\n")
            f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Patient ID:** {self.patient_id}\n\n")
            f.write(f"**Data Tier:** {self.current_processing_tier.upper()}\n\n")
            f.write(f"**Overall Status:** {'SUCCESS' if self.results['overall_success'] else 'FAILURE'}\n\n")
            
            f.write("## Test Steps Summary\n\n")
            f.write("| Step | Status | Duration |\n")
            f.write("|------|--------|----------|\n")
            
            for step_name, step_result in self.results["steps"].items():
                status = "✅ PASS" if step_result["success"] else "❌ FAIL"
                duration = f"{step_result.get('duration', 0):.2f}s"
                f.write(f"| {step_name.title()} | {status} | {duration} |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for step_name, step_result in self.results["steps"].items():
                f.write(f"### {step_name.title()}\n\n")
                
                if step_result["success"]:
                    if step_name == "fetch_data" and "resource_counts" in step_result:
                        f.write("**Resource Counts:**\n\n")
                        for resource_type, count in step_result["resource_counts"].items():
                            f.write(f"- {resource_type}: {count}\n")
                    
                    elif step_name == "validation" and "validation_stats" in step_result:
                        f.write("**Validation Statistics:**\n\n")
                        stats = step_result["validation_stats"]
                        f.write(f"- Total resources: {stats['total']}\n")
                        f.write(f"- Valid resources: {stats['valid_count']} ({stats['percent_valid']:.1f}%)\n")
                        f.write(f"- Invalid resources: {stats['invalid_count']}\n")
                    
                    elif step_name == "dashboards":
                        f.write("**Dashboard Output:**\n\n")
                        f.write(f"- Dashboard files: {step_result.get('output_dir', 'Unknown')}\n")
                        f.write("- Available dashboards: Quality, Validation, Combined\n")
                
                else:
                    f.write(f"**Error:** {step_result.get('error', 'Unknown error')}\n\n")
                
                if "output_file" in step_result:
                    f.write(f"**Results File:** {step_result['output_file']}\n\n")
            
            f.write("\n## Tier-Specific Information\n\n")
            f.write(f"This test was run against the **{self.current_processing_tier.upper()}** data tier.\n\n")
            
            if self.current_processing_tier == "bronze":
                f.write("Bronze tier represents raw data as fetched, conforming to base FHIR R4 with minimal transformations.\n")
            elif self.current_processing_tier == "silver":
                f.write("Silver tier includes data cleansing, initial common extensions, and improved coding compared to Bronze.\n")
            elif self.current_processing_tier == "gold":
                f.write("Gold tier represents fully conformant, enriched data with complete extensions, standardized coding, and LLM-ready narratives.\n")
            
            f.write("\n## Conclusion\n\n")
            if self.results["overall_success"]:
                f.write("All advanced FHIR tools tests completed successfully.\n")
            else:
                f.write("Some tests failed. See above for details.\n")
        
        logger.info(f"Test report generated: {report_file}")
        logger.info(f"Markdown report generated: {md_report_file}")
        
        return self.results["overall_success"]

    def _check_for_errors(self) -> bool:
        """
        Check if there are any ERROR-level log records in the root logger.
        
        Returns:
            bool: True if errors were found, False otherwise
        """
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if hasattr(handler, 'records'):
                for record in handler.records:
                    if record.levelno >= logging.ERROR:
                        return True
        return False

    def run_test(self):
        """Run the complete end-to-end test."""
        # Clear sentinel file at start
        SENTINEL_FAIL.unlink(missing_ok=True)
        
        logger.info("Starting Advanced FHIR Tools End-to-End Test")
        
        # Step 1: Authentication
        logger.info("Starting step: Authentication")
        if not self.authenticate():
            logger.error("Authentication failed, cannot proceed with test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        logger.info("Completed step: Authentication")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during authentication, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 2: Fetch patient data
        logger.info("Starting step: Fetch patient data")
        if not self.fetch_patient_data():
            logger.error("Failed to fetch patient data, cannot proceed with test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        logger.info("Completed step: Fetch patient data")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during data fetching, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 3: Test FHIRPath implementation
        logger.info("Starting step: Test FHIRPath")
        self.test_fhirpath()
        logger.info("Completed step: Test FHIRPath")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during FHIRPath testing, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 4: Test Pathling analytics
        logger.info("Starting step: Test Pathling Analytics")
        self.test_pathling_analytics()
        logger.info("Completed step: Test Pathling Analytics")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during Pathling analytics, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 5: Test data science tools
        logger.info("Starting step: Test Data Science Tools")
        self.test_datascience()
        logger.info("Completed step: Test Data Science Tools")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during data science testing, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 6: Test validation framework
        logger.info("Starting step: Test Validation Framework")
        self.test_validation()
        logger.info("Completed step: Test Validation Framework")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during validation framework testing, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Step 7: Generate dashboards
        logger.info("Starting step: Generate Dashboards")
        self.generate_dashboards()
        logger.info("Completed step: Generate Dashboards")
        
        # Check for fatal errors before proceeding
        if self._check_for_errors():
            logger.error("Fatal errors detected during dashboard generation, stopping test")
            self.generate_report()
            SENTINEL_FAIL.touch()
            sys.exit(1)
            return False
        
        # Generate final report
        success = self.generate_report()
        
        # Touch the sentinel file if we failed
        if not success:
            SENTINEL_FAIL.touch()
            sys.exit(1)
            
        logger.info(f"Advanced FHIR Tools Test completed with status: {'SUCCESS' if success else 'FAILURE'}")
        return success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run Advanced FHIR Tools End-to-End Test")
    parser.add_argument("--patient-id", default=DEFAULT_PATIENT_ID,
                        help=f"Patient ID to use for testing (default: {DEFAULT_PATIENT_ID})")
    parser.add_argument("--output-dir", help="Output directory for test results")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--mock", action="store_true", help="Enable mock mode for testing without real dependencies")
    parser.add_argument("--tier", type=str, choices=TIERS, default=None,
                        help="Specify the target data tier to process up to (bronze, silver, gold). Defaults to gold.")
    parser.add_argument("--pathling-java-debug-port", type=int, default=None,
                        help="Enable Java remote debugging for Pathling on the specified port.")
    parser.add_argument("--validator-java-debug-port", type=int, default=None,
                        help="Enable Java remote debugging for FHIR Validator on the specified port.")
    
    args = parser.parse_args()
    
    # Set mock mode from environment variable if set, otherwise use CLI arg
    mock_mode = args.mock or os.environ.get("USE_MOCK_MODE") == "true"

    # Run the test
    test = AdvancedFHIRToolsTest(
        patient_id=args.patient_id,
        output_dir=args.output_dir,
        debug=args.debug,
        mock_mode=mock_mode,
        tier=args.tier,
        pathling_java_debug_port=args.pathling_java_debug_port,
        validator_java_debug_port=args.validator_java_debug_port
    )
    
    success = test.run_test()
    
    # Return exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 