"""
FHIR resource extraction module for the bronze layer.

This module provides classes for extracting FHIR resources from the API
and saving them to the bronze layer as raw JSON files.
"""

import datetime
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from epic_fhir_integration.io.fhir_client import FHIRClient, create_fhir_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceExtractor(ABC):
    """Base class for FHIR resource extractors."""
    
    def __init__(
        self,
        resource_type: str,
        output_dir: Union[str, Path] = None,
        client: Optional[FHIRClient] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new resource extractor.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            output_dir: Directory to save extracted resources.
            client: Optional FHIR client. If not provided, a new one will be created.
            params: Optional parameters for the resource search.
        """
        self.resource_type = resource_type
        
        # Set up output directory
        if output_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            output_dir = base_dir / "output" / "bronze" / resource_type.lower()
        elif isinstance(output_dir, str):
            output_dir = Path(output_dir)
        
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up FHIR client
        self.client = client or create_fhir_client()
        
        # Set up search parameters
        self.params = params or {}
    
    def extract(
        self, page_limit: Optional[int] = None, total_limit: Optional[int] = None
    ) -> Path:
        """Extract resources from the FHIR API and save to the bronze layer.
        
        Args:
            page_limit: Maximum number of pages to extract.
            total_limit: Maximum total number of resources to extract.
            
        Returns:
            Path to the output file.
        """
        logger.info(f"Extracting {self.resource_type} resources...")
        
        # Generate output filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{self.resource_type.lower()}_{timestamp}.json"
        
        # Extract resources and wrap in a Bundle
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "timestamp": datetime.datetime.now().isoformat(),
            "entry": []
        }
        
        resource_count = 0
        
        try:
            # Search for resources
            for resource in self.client.search_resources(
                self.resource_type, self.params, page_limit, total_limit
            ):
                # Add resource to bundle
                bundle["entry"].append({
                    "resource": resource,
                    "fullUrl": f"{self.client.base_url}/{self.resource_type}/{resource.get('id', 'unknown')}"
                })
                resource_count += 1
        
            # Save bundle to file
            with open(output_file, "w") as f:
                json.dump(bundle, f, indent=2)
            
            logger.info(f"Extracted {resource_count} {self.resource_type} resources to {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error extracting {self.resource_type} resources: {e}")
            raise
    
    @classmethod
    def create(
        cls, 
        resource_type: str, 
        output_dir: Optional[Union[str, Path]] = None,
        client: Optional[FHIRClient] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> "ResourceExtractor":
        """Factory method to create an extractor for a specific resource type.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation").
            output_dir: Directory to save extracted resources.
            client: Optional FHIR client.
            params: Optional parameters for the resource search.
            
        Returns:
            Resource extractor instance.
        """
        # Use the base ResourceExtractor for all resource types for now
        # In the future, specific extractors can be implemented for different resources
        return cls(resource_type, output_dir, client, params)


class PatientExtractor(ResourceExtractor):
    """Extractor for Patient resources."""
    
    def __init__(
        self,
        output_dir: Union[str, Path] = None,
        client: Optional[FHIRClient] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Patient extractor.
        
        Args:
            output_dir: Directory to save extracted resources.
            client: Optional FHIR client.
            params: Optional parameters for the resource search.
        """
        params = params or {}
        
        # Add default parameters for Patient extraction
        default_params = {
            "_count": "50",  # Number of results per page
            "_sort": "-_lastUpdated",  # Sort by last updated date (newest first)
        }
        # Merge default params with provided params, but don't override provided ones
        for key, value in default_params.items():
            if key not in params:
                params[key] = value
        
        super().__init__("Patient", output_dir, client, params)


class ObservationExtractor(ResourceExtractor):
    """Extractor for Observation resources."""
    
    def __init__(
        self,
        output_dir: Union[str, Path] = None,
        client: Optional[FHIRClient] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Observation extractor.
        
        Args:
            output_dir: Directory to save extracted resources.
            client: Optional FHIR client.
            params: Optional parameters for the resource search.
        """
        params = params or {}
        
        # Add default parameters for Observation extraction
        default_params = {
            "_count": "100",  # Number of results per page
            "_sort": "-date",  # Sort by observation date (newest first)
        }
        # Merge default params with provided params, but don't override provided ones
        for key, value in default_params.items():
            if key not in params:
                params[key] = value
        
        super().__init__("Observation", output_dir, client, params)


def extract_resources(
    resource_types: List[str],
    output_base_dir: Optional[Union[str, Path]] = None,
    params: Optional[Dict[str, Dict[str, Any]]] = None,
    page_limit: Optional[int] = None,
    total_limit: Optional[int] = None,
) -> Dict[str, Path]:
    """Extract multiple resource types.
    
    Args:
        resource_types: List of FHIR resource types to extract.
        output_base_dir: Base directory for output.
        params: Optional parameters for each resource type.
        page_limit: Maximum number of pages to extract per resource type.
        total_limit: Maximum total number of resources to extract per resource type.
        
    Returns:
        Dictionary mapping resource types to output file paths.
    """
    params = params or {}
    output_files = {}
    
    # Create a single FHIR client to be reused for all extractors
    client = create_fhir_client()
    
    for resource_type in resource_types:
        # Determine the output directory
        if output_base_dir is None:
            output_dir = None  # Let the extractor use the default
        else:
            base_dir = Path(output_base_dir) if isinstance(output_base_dir, str) else output_base_dir
            output_dir = base_dir / "bronze" / resource_type.lower()
        
        # Get resource-specific parameters
        resource_params = params.get(resource_type, {})
        
        # Create an extractor for this resource type
        extractor_class = ResourceExtractor
        if resource_type == "Patient":
            extractor_class = PatientExtractor
        elif resource_type == "Observation":
            extractor_class = ObservationExtractor
        
        extractor = extractor_class(
            resource_type=resource_type,
            output_dir=output_dir,
            client=client,
            params=resource_params,
        )
        
        # Extract the resources
        output_file = extractor.extract(page_limit=page_limit, total_limit=total_limit)
        output_files[resource_type] = output_file
    
    return output_files 