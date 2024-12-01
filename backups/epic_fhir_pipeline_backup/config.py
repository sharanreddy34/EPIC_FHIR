"""
Configuration settings for FHIR pipeline.
Uses Pydantic to validate settings and load from environment variables.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Literal
from pydantic import validator, Field, field_validator
from pydantic_settings import BaseSettings


class FHIRAPISettings(BaseSettings):
    """FHIR API connection settings."""
    
    environment: Literal["production", "non-production"] = Field(
        "non-production",
        description="API environment to use"
    )
    
    base_url: Optional[str] = Field(
        None,
        description="Base URL for the FHIR API (overrides environment setting if provided)"
    )
    
    token_url: Optional[str] = Field(
        None,
        description="Token endpoint URL (overrides environment setting if provided)"
    )
    
    client_id: str = Field(
        ..., 
        description="FHIR client ID",
        env="EPIC_CLIENT_ID"
    )
    
    client_secret: Optional[str] = Field(
        None, 
        description="FHIR client secret",
        env="EPIC_CLIENT_SECRET"
    )
    
    timeout: int = Field(
        30,
        description="Request timeout in seconds"
    )
    
    verify_ssl: bool = Field(
        True,
        description="Whether to verify SSL certificates"
    )
    
    @field_validator('base_url', mode='after')
    def set_base_url(cls, v, info):
        """Set base URL based on environment if not explicitly provided."""
        if v is not None:
            return v
        
        env = info.data.get('environment', 'non-production')
        if env == 'production':
            return "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
        else:
            return "https://fhir-myapps.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    
    @field_validator('token_url', mode='after')
    def set_token_url(cls, v, info):
        """Set token URL based on environment if not explicitly provided."""
        if v is not None:
            return v
        
        env = info.data.get('environment', 'non-production')
        if env == 'production':
            return "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
        else:
            return "https://fhir-myapps.epic.com/interconnect-fhir-oauth/oauth2/token"
    
    @field_validator('client_secret')
    def validate_client_secret(cls, v):
        """Validate client secret is provided if not in mock mode."""
        if v is None:
            raise ValueError(
                "EPIC_CLIENT_SECRET environment variable must be set. "
                "Use --mock flag if you want to run with mock data."
            )
        return v
    
    class Config:
        env_prefix = ""
        case_sensitive = False


class PipelineSettings(BaseSettings):
    """Pipeline execution settings."""
    
    output_dir: Path = Field(
        Path("./local_output"),
        description="Output directory for local pipeline data"
    )
    patient_data_dir: Path = Field(
        Path("./patient_data"),
        description="Directory for patient data"
    )
    debug: bool = Field(
        False,
        description="Enable debug logging"
    )
    mock_mode: bool = Field(
        False,
        description="Run in mock mode without API calls"
    )
    resource_types: List[str] = Field(
        ["Patient", "Encounter", "Observation", "Condition", "MedicationRequest"],
        description="FHIR resource types to process"
    )
    
    @field_validator('output_dir', 'patient_data_dir')
    def create_directory(cls, v):
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_prefix = "FHIR_"
        case_sensitive = False


class Settings:
    """Combined settings object."""
    
    def __init__(
        self,
        api_settings: Optional[FHIRAPISettings] = None,
        pipeline_settings: Optional[PipelineSettings] = None,
        mock_mode: bool = False
    ):
        """
        Initialize settings.
        
        Args:
            api_settings: API settings
            pipeline_settings: Pipeline settings
            mock_mode: Whether to run in mock mode
        """
        self.use_mock = mock_mode
        
        # Load pipeline settings
        self.pipeline = pipeline_settings or PipelineSettings(mock_mode=mock_mode)
        
        # Load API settings if not in mock mode
        self.api = api_settings
        if not self.api and not mock_mode:
            # In real mode, we need API settings
            self.api = FHIRAPISettings()
        elif not self.api and mock_mode:
            # In mock mode, we can use defaults without validation
            self.api = FHIRAPISettings.model_construct(
                client_id="mock-client-id",
                client_secret="mock-client-secret"
            )


def load_settings(
    mock_mode: bool = False,
    debug: bool = False,
    output_dir: Optional[str] = None,
    patient_data_dir: Optional[str] = None,
    config_file: Optional[str] = None,
    environment: Optional[str] = None
) -> Settings:
    """
    Load settings from environment and arguments.
    
    Args:
        mock_mode: Whether to run in mock mode
        debug: Whether to enable debug logging
        output_dir: Output directory override
        patient_data_dir: Patient data directory override
        config_file: Path to config file
        environment: API environment (production/non-production)
        
    Returns:
        Settings object
    """
    pipeline_overrides = {
        "mock_mode": mock_mode,
        "debug": debug
    }
    
    if output_dir:
        pipeline_overrides["output_dir"] = Path(output_dir)
        
    if patient_data_dir:
        pipeline_overrides["patient_data_dir"] = Path(patient_data_dir)
    
    # Create pipeline settings with overrides
    pipeline_settings = PipelineSettings(**pipeline_overrides)
    
    # If we're in mock mode, we don't need real API credentials
    if mock_mode:
        return Settings(pipeline_settings=pipeline_settings, mock_mode=True)
    
    # Otherwise we need to load API settings
    try:
        api_overrides = {}
        if environment:
            api_overrides["environment"] = environment
            
        api_settings = FHIRAPISettings(**api_overrides)
        return Settings(
            api_settings=api_settings,
            pipeline_settings=pipeline_settings
        )
    except Exception as e:
        if "EPIC_CLIENT_SECRET" in str(e) and not mock_mode:
            # Suggest to either set the secret or use mock mode
            print("ERROR: EPIC_CLIENT_SECRET environment variable not set.")
            print("Either set this variable or use --mock flag.")
            raise
        raise 