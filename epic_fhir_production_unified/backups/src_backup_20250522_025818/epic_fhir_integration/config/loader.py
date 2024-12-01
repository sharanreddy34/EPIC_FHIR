"""
Configuration loader module for Epic FHIR integration.

This module provides functions to load configuration from various sources
in the following order of precedence:
1. CLI flags
2. Environment variable $EPIC_FHIR_CFG
3. Local config file at ~/.config/epic_fhir/api_config.yaml
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _load_config_from_file(config_path: Path) -> Dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dictionary containing the configuration.
    """
    if not config_path.exists():
        return {}
    
    with open(config_path, "r") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return {}


def get_config(section: str = None, cli_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get configuration from multiple sources with priority.

    Args:
        section: Optional section name to retrieve from the config.
        cli_config: Optional configuration passed via CLI flags.

    Returns:
        Dictionary containing the merged configuration.
    """
    # Default empty configs
    config = {}
    
    # 3. Load from default config file
    default_config_path = Path.home() / ".config" / "epic_fhir" / "api_config.yaml"
    default_config = _load_config_from_file(default_config_path)
    config.update(default_config)
    
    # 2. Load from environment variable if set
    env_config_path = os.environ.get("EPIC_FHIR_CFG")
    if env_config_path:
        env_config = _load_config_from_file(Path(env_config_path))
        config.update(env_config)
    
    # 1. Override with CLI config if provided
    if cli_config:
        config.update(cli_config)
    
    # Return specific section if requested
    if section and section in config:
        return config[section]
    
    return config 