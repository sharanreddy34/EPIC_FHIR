"""
Unit tests for the config loader module.
"""

import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from epic_fhir_integration.config.loader import get_config, _load_config_from_file


class TestConfigLoader:
    """Test suite for config loader module."""

    def test_load_config_from_file_non_existent(self):
        """Test loading config from a non-existent file."""
        # Create a path to a non-existent file
        config_path = Path("/path/to/nonexistent/config.yaml")
        
        # Load config from non-existent file
        config = _load_config_from_file(config_path)
        
        # Verify that an empty dict is returned
        assert config == {}

    def test_load_config_from_file_invalid_yaml(self):
        """Test loading config from a file with invalid YAML."""
        # Mock open to return invalid YAML
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError):
                config = _load_config_from_file(Path("config.yaml"))
                
                # Verify that an empty dict is returned
                assert config == {}

    def test_load_config_from_file_empty_yaml(self):
        """Test loading config from a file with empty YAML."""
        # Mock open to return empty content
        with patch("builtins.open", mock_open(read_data="")):
            config = _load_config_from_file(Path("config.yaml"))
            
            # Verify that an empty dict is returned
            assert config == {}

    def test_load_config_from_file_valid_yaml(self):
        """Test loading config from a file with valid YAML."""
        yaml_content = """
        auth:
          client_id: test-client
          jwt_issuer: test-issuer
          epic_base_url: https://example.org/epic
        fhir:
          base_url: https://example.org/epic/fhir
        """
        
        expected_config = {
            "auth": {
                "client_id": "test-client",
                "jwt_issuer": "test-issuer",
                "epic_base_url": "https://example.org/epic"
            },
            "fhir": {
                "base_url": "https://example.org/epic/fhir"
            }
        }
        
        # Mock open to return valid YAML
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            config = _load_config_from_file(Path("config.yaml"))
            
            # Verify that the correct config is returned
            assert config == expected_config

    def test_get_config_default_path(self):
        """Test getting config from the default path."""
        # Mock Path.exists to return True for home config
        # Mock _load_config_from_file to return a test config
        test_config = {"auth": {"client_id": "default-client"}}
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("epic_fhir_integration.config.loader._load_config_from_file", return_value=test_config):
                config = get_config()
                
                # Verify that the default config is returned
                assert config == test_config

    def test_get_config_env_path(self):
        """Test getting config from the environment variable path."""
        # Mock os.environ to include EPIC_FHIR_CFG
        # Mock Path.exists to return True for env config
        # Mock _load_config_from_file to return different configs for default and env
        default_config = {"auth": {"client_id": "default-client"}}
        env_config = {"auth": {"client_id": "env-client"}}
        
        with patch.dict("os.environ", {"EPIC_FHIR_CFG": "/path/to/env/config.yaml"}):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("epic_fhir_integration.config.loader._load_config_from_file", side_effect=[default_config, env_config]):
                    config = get_config()
                    
                    # Verify that the env config overrides the default
                    assert config == env_config

    def test_get_config_cli_override(self):
        """Test that CLI config overrides other configs."""
        # Mock Path.exists to return True
        # Mock _load_config_from_file to return test configs
        default_config = {"auth": {"client_id": "default-client"}}
        env_config = {"auth": {"client_id": "env-client"}}
        cli_config = {"auth": {"client_id": "cli-client"}}
        
        with patch.dict("os.environ", {"EPIC_FHIR_CFG": "/path/to/env/config.yaml"}):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("epic_fhir_integration.config.loader._load_config_from_file", side_effect=[default_config, env_config]):
                    config = get_config(cli_config=cli_config)
                    
                    # Verify that the CLI config overrides others
                    assert config == cli_config

    def test_get_config_section(self):
        """Test getting a specific section of the config."""
        # Mock Path.exists to return True
        # Mock _load_config_from_file to return a test config with sections
        test_config = {
            "auth": {"client_id": "test-client"},
            "fhir": {"base_url": "https://example.org/fhir"}
        }
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("epic_fhir_integration.config.loader._load_config_from_file", return_value=test_config):
                # Get the auth section
                auth_config = get_config(section="auth")
                
                # Verify that only the auth section is returned
                assert auth_config == {"client_id": "test-client"}

    def test_get_config_nonexistent_section(self):
        """Test getting a non-existent section returns the full config."""
        # Mock Path.exists to return True
        # Mock _load_config_from_file to return a test config
        test_config = {"auth": {"client_id": "test-client"}}
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("epic_fhir_integration.config.loader._load_config_from_file", return_value=test_config):
                # Try to get a non-existent section
                config = get_config(section="nonexistent")
                
                # Verify that the full config is returned
                assert config == test_config

    def test_get_config_real_file(self):
        """Test getting config from a real temporary file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            yaml_content = """
            auth:
              client_id: temp-client
              jwt_issuer: temp-issuer
            """
            temp_file.write(yaml_content)
            temp_path = temp_file.name
        
        try:
            # Mock environment to point to our temp file
            with patch.dict("os.environ", {"EPIC_FHIR_CFG": temp_path}):
                config = get_config()
                
                # Verify that the config from the temp file is returned
                assert "auth" in config
                assert config["auth"]["client_id"] == "temp-client"
                assert config["auth"]["jwt_issuer"] == "temp-issuer"
        finally:
            # Clean up temp file
            os.unlink(temp_path) 