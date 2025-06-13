"""
Configuration management for Epic FHIR Integration.

This module provides a centralized, hierarchical configuration system using Pydantic
for schema validation and type safety.
"""

import os
import json
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

try:
    from transforms.api import get_config
    FOUNDRY_AVAILABLE = True
except ImportError:
    FOUNDRY_AVAILABLE = False

from pydantic import BaseModel, Field, validator, root_validator

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceType(str, Enum):
    """Supported FHIR resource types."""
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    CONDITION = "Condition"
    MEDICATION_REQUEST = "MedicationRequest"


class BronzeConfig(BaseModel):
    """Configuration for Bronze layer extractors."""
    resource_type: ResourceType
    max_pages: int = Field(default=100, description="Maximum number of pages to extract")
    batch_size: int = Field(default=200, description="Number of resources per batch")
    incremental: bool = Field(default=True, description="Whether to use incremental extraction")
    default_watermark: str = Field(
        default="1900-01-01T00:00:00Z", 
        description="Default watermark if none exists"
    )
    api_retry_attempts: int = Field(default=3, description="Number of retry attempts for API calls")
    api_retry_backoff_factor: float = Field(default=2.0, description="Exponential backoff factor for retries")


class SilverConfig(BaseModel):
    """Configuration for Silver layer transformers."""
    resource_type: ResourceType
    flatten_arrays: bool = Field(default=True, description="Whether to flatten array fields")
    max_array_size: int = Field(default=10, description="Maximum size for flattened arrays")
    validate_schema: bool = Field(default=True, description="Whether to validate against schema")
    enforce_data_types: bool = Field(default=True, description="Whether to enforce data types")
    handle_missing_fields: bool = Field(default=True, description="Whether to handle missing fields")


class GoldConfig(BaseModel):
    """Configuration for Gold layer analytics."""
    include_resources: List[ResourceType] = Field(
        default_factory=lambda: [rt for rt in ResourceType], 
        description="Resource types to include in analytics"
    )
    pathling_enabled: bool = Field(default=True, description="Whether to use Pathling for analytics")
    time_window_days: int = Field(default=365, description="Time window for analytics in days")
    partition_by_year: bool = Field(default=True, description="Whether to partition data by year")


class ValidationConfig(BaseModel):
    """Configuration for data validation."""
    resource_type: ResourceType
    schema_validation: bool = Field(default=True, description="Whether to validate against schema")
    content_validation: bool = Field(default=True, description="Whether to validate content")
    reference_validation: bool = Field(default=False, description="Whether to validate references")
    fail_on_error: bool = Field(default=False, description="Whether to fail on validation errors")
    error_threshold: float = Field(default=0.05, description="Error threshold before failing")


class ApiConfig(BaseModel):
    """Configuration for API clients."""
    base_url: str = Field(default="", description="API base URL")
    client_id: str = Field(default="", description="API client ID")
    token_endpoint: str = Field(default="/oauth2/token", description="OAuth token endpoint")
    timeout_seconds: int = Field(default=30, description="API timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_backoff_factor: float = Field(default=2.0, description="Retry backoff factor")


class AppConfig(BaseModel):
    """Global application configuration."""
    bronze: Dict[str, BronzeConfig] = Field(default_factory=dict)
    silver: Dict[str, SilverConfig] = Field(default_factory=dict)
    gold: Dict[str, GoldConfig] = Field(default_factory=dict)
    validation: Dict[str, ValidationConfig] = Field(default_factory=dict)
    api: ApiConfig = Field(default_factory=ApiConfig)
    
    # Settings that should be available across all components
    environment: str = Field(default="dev", description="Environment (dev, test, prod)")
    log_level: str = Field(default="INFO", description="Default log level")
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment."""
        allowed = ["dev", "test", "prod"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v.lower()
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()


# Global configuration instance
_config = None


def load_config_from_environment() -> dict:
    """Load configuration from environment variables."""
    config = {}
    
    # API configuration from environment
    if os.environ.get("EPIC_BASE_URL"):
        config["api"] = {
            "base_url": os.environ.get("EPIC_BASE_URL", ""),
            "client_id": os.environ.get("EPIC_CLIENT_ID", ""),
        }
    
    # Environment and logging
    if os.environ.get("ENVIRONMENT"):
        config["environment"] = os.environ.get("ENVIRONMENT")
    
    if os.environ.get("LOG_LEVEL"):
        config["log_level"] = os.environ.get("LOG_LEVEL")
    
    return config


def load_config_from_file(file_path: Union[str, Path]) -> dict:
    """Load configuration from a file."""
    file_path = Path(file_path)
    if not file_path.exists():
        logger.warning(f"Config file not found: {file_path}")
        return {}
    
    with open(file_path, "r") as f:
        try:
            if file_path.suffix == ".json":
                return json.load(f)
            elif file_path.suffix in [".yaml", ".yml"]:
                import yaml
                return yaml.safe_load(f)
            else:
                logger.warning(f"Unsupported config file format: {file_path.suffix}")
                return {}
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return {}


def load_config_from_foundry(transform_context=None) -> dict:
    """Load configuration from Foundry transform context."""
    if not FOUNDRY_AVAILABLE:
        return {}
    
    try:
        # If context is provided, use it
        if transform_context is not None:
            config = {}
            # Load all config parameters from the transform context
            for param in dir(transform_context):
                if not param.startswith("_") and not callable(getattr(transform_context, param)):
                    value = getattr(transform_context, param)
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        config[param] = value
            return config
        
        # Otherwise try to use global config
        try:
            # This will only work inside a Foundry transform
            from transforms.api import get_config
            
            # Try to get all available config parameters
            # This might not be comprehensive, as it depends on how get_config is implemented
            config = {}
            known_params = [
                "resource_type", "max_pages", "batch_size", "incremental", 
                "flatten_arrays", "validate_schema", "include_resources"
            ]
            
            for param in known_params:
                try:
                    value = get_config(param)
                    if value is not None:
                        config[param] = value
                except:
                    pass
                    
            return config
            
        except ImportError:
            return {}
    except Exception as e:
        logger.warning(f"Error loading config from Foundry: {e}")
        return {}


def get_config(transform_context=None) -> AppConfig:
    """Get the global configuration instance."""
    global _config
    
    if _config is None:
        # Load configuration from various sources
        config_dict = {}
        
        # Load from default config file
        default_config_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
        default_config = load_config_from_file(default_config_path)
        config_dict.update(default_config)
        
        # Load from environment-specific config file
        env = os.environ.get("ENVIRONMENT", "dev")
        env_config_path = Path(__file__).parent.parent / "config" / f"{env}_config.yaml"
        env_config = load_config_from_file(env_config_path)
        config_dict.update(env_config)
        
        # Load from environment variables
        env_config = load_config_from_environment()
        config_dict.update(env_config)
        
        # Load from Foundry transform context
        if transform_context is not None:
            foundry_config = load_config_from_foundry(transform_context)
            
            # Map Foundry transform-specific configs to our structure
            if "resource_type" in foundry_config:
                resource_type = foundry_config["resource_type"]
                
                # For Bronze layer
                if "max_pages" in foundry_config or "batch_size" in foundry_config:
                    if "bronze" not in config_dict:
                        config_dict["bronze"] = {}
                    
                    if resource_type not in config_dict["bronze"]:
                        config_dict["bronze"][resource_type] = {}
                    
                    if "max_pages" in foundry_config:
                        config_dict["bronze"][resource_type]["max_pages"] = foundry_config["max_pages"]
                    
                    if "batch_size" in foundry_config:
                        config_dict["bronze"][resource_type]["batch_size"] = foundry_config["batch_size"]
                
                # For Silver layer
                if "flatten_arrays" in foundry_config or "validate_schema" in foundry_config:
                    if "silver" not in config_dict:
                        config_dict["silver"] = {}
                    
                    if resource_type not in config_dict["silver"]:
                        config_dict["silver"][resource_type] = {}
                    
                    if "flatten_arrays" in foundry_config:
                        config_dict["silver"][resource_type]["flatten_arrays"] = foundry_config["flatten_arrays"]
                    
                    if "validate_schema" in foundry_config:
                        config_dict["silver"][resource_type]["validate_schema"] = foundry_config["validate_schema"]
        
        # Create the AppConfig instance
        try:
            _config = AppConfig(**config_dict)
            logger.info(f"Configuration loaded successfully for environment: {_config.environment}")
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            # Fallback to empty config
            _config = AppConfig()
    
    return _config


def get_bronze_config(resource_type: Union[str, ResourceType], transform_context=None) -> BronzeConfig:
    """Get configuration for a Bronze layer extractor."""
    app_config = get_config(transform_context)
    
    # Normalize resource type
    if isinstance(resource_type, str):
        resource_type = ResourceType(resource_type)
    
    # Return resource-specific config if available, otherwise create a new one
    if resource_type.value in app_config.bronze:
        return app_config.bronze[resource_type.value]
    else:
        return BronzeConfig(resource_type=resource_type)


def get_silver_config(resource_type: Union[str, ResourceType], transform_context=None) -> SilverConfig:
    """Get configuration for a Silver layer transformer."""
    app_config = get_config(transform_context)
    
    # Normalize resource type
    if isinstance(resource_type, str):
        resource_type = ResourceType(resource_type)
    
    # Return resource-specific config if available, otherwise create a new one
    if resource_type.value in app_config.silver:
        return app_config.silver[resource_type.value]
    else:
        return SilverConfig(resource_type=resource_type)


def get_gold_config(transform_context=None) -> GoldConfig:
    """Get configuration for a Gold layer analytics."""
    app_config = get_config(transform_context)
    
    # Currently only one gold config
    if "default" in app_config.gold:
        return app_config.gold["default"]
    else:
        return GoldConfig()


def get_validation_config(resource_type: Union[str, ResourceType], transform_context=None) -> ValidationConfig:
    """Get configuration for data validation."""
    app_config = get_config(transform_context)
    
    # Normalize resource type
    if isinstance(resource_type, str):
        resource_type = ResourceType(resource_type)
    
    # Return resource-specific config if available, otherwise create a new one
    if resource_type.value in app_config.validation:
        return app_config.validation[resource_type.value]
    else:
        return ValidationConfig(resource_type=resource_type)


def get_api_config(transform_context=None) -> ApiConfig:
    """Get configuration for API clients."""
    return get_config(transform_context).api 