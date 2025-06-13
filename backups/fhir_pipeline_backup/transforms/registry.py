import os
import importlib
import logging
import yaml
from typing import Dict, Any, Optional, Type

import pyspark.sql
from pyspark.sql import SparkSession

from fhir_pipeline.transforms.base import BaseTransformer

logger = logging.getLogger(__name__)

# Generic transformer implementation
class GenericTransformer(BaseTransformer):
    """
    Generic transformer that applies YAML mapping without custom logic.
    Used as fallback when no resource-specific transformer is found.
    """
    pass  # All functionality inherited from BaseTransformer

def _load_mapping_spec(resource_type: str) -> Dict[str, Any]:
    """
    Load the YAML mapping specification for a given resource type.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        Dictionary containing the mapping specification
        
    Raises:
        FileNotFoundError: If no mapping file exists for the resource type
    """
    # Determine base path - works in both development and Foundry
    base_dir = os.environ.get(
        "FHIR_CONFIG_DIR", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    )
    
    mapping_path = os.path.join(base_dir, "generic_mappings", f"{resource_type}.yaml")
    
    if not os.path.exists(mapping_path):
        raise FileNotFoundError(f"No mapping file found for resource type {resource_type}")
        
    with open(mapping_path, 'r') as f:
        spec = yaml.safe_load(f)
        
    # Validate basic structure
    if not spec:
        raise ValueError(f"Empty or invalid mapping spec for {resource_type}")
        
    if spec.get('resourceType') != resource_type:
        logger.warning(
            f"Mismatch between file name ({resource_type}) and resourceType in spec "
            f"({spec.get('resourceType')})"
        )
        
    return spec

def _try_import_custom_transformer(resource_type: str) -> Optional[Type[BaseTransformer]]:
    """
    Attempt to import a custom transformer class for a specific resource type.
    
    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        Transformer class if found, None otherwise
    """
    module_name = f"fhir_pipeline.transforms.custom.{resource_type.lower()}"
    class_name = "Transformer"
    
    try:
        module = importlib.import_module(module_name)
        transformer_class = getattr(module, class_name)
        
        # Verify it's a BaseTransformer subclass
        if not issubclass(transformer_class, BaseTransformer):
            logger.warning(
                f"Found {module_name}.{class_name}, but it's not a BaseTransformer subclass"
            )
            return None
            
        logger.info(f"Found custom transformer for {resource_type}")
        return transformer_class
        
    except (ImportError, AttributeError):
        # No custom transformer found, that's expected
        return None
    except Exception as e:
        logger.exception(f"Error importing custom transformer for {resource_type}: {e}")
        return None

def get_transformer(spark: SparkSession, resource_type: str) -> BaseTransformer:
    """
    Get the appropriate transformer for a given FHIR resource type.
    
    Args:
        spark: Active SparkSession
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        
    Returns:
        Instantiated transformer for the resource type
        
    Raises:
        ValueError: If resource_type is not supported (no YAML mapping exists)
    """
    logger.info(f"Getting transformer for resource type: {resource_type}")
    
    # Load the mapping specification
    try:
        mapping_spec = _load_mapping_spec(resource_type)
    except FileNotFoundError:
        raise ValueError(f"Unsupported resource type: {resource_type}. No mapping available.")
    
    # Try to find a custom transformer first
    transformer_class = _try_import_custom_transformer(resource_type)
    
    # Fall back to generic transformer if no custom one found
    if transformer_class is None:
        logger.info(f"Using generic transformer for {resource_type}")
        transformer_class = GenericTransformer
    
    # Instantiate and return the transformer
    return transformer_class(spark, resource_type, mapping_spec) 