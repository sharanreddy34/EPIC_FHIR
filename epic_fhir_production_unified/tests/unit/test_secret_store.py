"""
Unit tests for the secret store module.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest

from epic_fhir_integration.security.secret_store import (
    SecretValue,
    get_secret_path,
    save_secret,
    load_secret,
    delete_secret,
    list_secrets,
)


class TestSecretStore:
    """Test suite for secret store module."""

    def test_secret_value_container(self):
        """Test the SecretValue container for masking secrets."""
        # Create a SecretValue with a string
        secret = SecretValue("mysecret")
        
        # Verify the secret can be accessed with get()
        assert secret.get() == "mysecret"
        
        # Verify string representation is masked
        assert str(secret) == "***SECRET***"
        
        # Verify repr representation is masked
        assert repr(secret) == "***SECRET***"
        
        # Test with a dictionary secret
        dict_secret = SecretValue({"api_key": "mysecret"})
        assert dict_secret.get() == {"api_key": "mysecret"}
        assert str(dict_secret) == "***SECRET***"

    @patch('pathlib.Path.resolve')
    def test_get_secret_path(self, mock_resolve):
        """Test getting the path to a secret file."""
        # Setup mock path
        mock_path = MagicMock()
        mock_path.parent.parent.parent = Path("/mock/base/dir")
        mock_resolve.return_value = mock_path
        
        # Create temp directory to mimic secrets dir
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the secrets directory path
            with patch('epic_fhir_integration.security.secret_store.Path.__truediv__', 
                      return_value=Path(os.path.join(temp_dir, "mysecret.json"))):
                
                # Mock the mkdir method to do nothing (avoid error on temp dir)
                with patch('pathlib.Path.mkdir', return_value=None):
                    # Call the function
                    path = get_secret_path("mysecret.json")
                    
                    # Verify the path is correct
                    assert str(path).endswith("mysecret.json")
                    assert Path(temp_dir) in path.parents

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_save_secret_dict(self, mock_get_path):
        """Test saving a dictionary secret."""
        # Create a temp file path
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Mock get_secret_path to return our temp file path
            mock_get_path.return_value = temp_path
            
            # Call the function with a dictionary
            secret_data = {"api_key": "mysecret", "expires_in": 3600}
            save_secret("test_secret", secret_data)
            
            # Verify the file contains the correct JSON
            with open(temp_path, "r") as f:
                saved_data = json.load(f)
                assert saved_data == secret_data
                
        finally:
            # Clean up
            os.unlink(temp_path)

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_save_secret_string(self, mock_get_path):
        """Test saving a string secret."""
        # Create a temp file path
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Mock get_secret_path to return our temp file path
            mock_get_path.return_value = temp_path
            
            # Call the function with a string
            save_secret("test_secret", "mysecret")
            
            # Verify the file contains the string
            with open(temp_path, "r") as f:
                saved_data = f.read()
                assert saved_data == "mysecret"
                
        finally:
            # Clean up
            os.unlink(temp_path)

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_load_secret_nonexistent(self, mock_get_path):
        """Test loading a non-existent secret."""
        # Mock a path that doesn't exist
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path
        
        # Call the function and verify it raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_secret("nonexistent_secret")

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_load_secret_json(self, mock_get_path):
        """Test loading a JSON secret."""
        # Create a temp file with JSON content
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            json.dump({"api_key": "mysecret"}, temp_file)
            temp_path = Path(temp_file.name)
        
        try:
            # Mock get_secret_path to return our temp file path
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.__str__.return_value = str(temp_path)
            mock_get_path.return_value = mock_path
            
            # Call the function
            secret = load_secret("test_secret")
            
            # Verify the secret was loaded correctly
            assert isinstance(secret, SecretValue)
            assert secret.get() == {"api_key": "mysecret"}
                
        finally:
            # Clean up
            os.unlink(temp_path)

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_load_secret_text(self, mock_get_path):
        """Test loading a text secret."""
        # Create a temp file with text content
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write("mysecret")
            temp_path = Path(temp_file.name)
        
        try:
            # Mock get_secret_path to return our temp file path
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.__str__.return_value = str(temp_path)
            mock_get_path.return_value = mock_path
            
            # Call the function
            secret = load_secret("test_secret")
            
            # Verify the secret was loaded correctly
            assert isinstance(secret, SecretValue)
            assert secret.get() == "mysecret"
                
        finally:
            # Clean up
            os.unlink(temp_path)

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    @patch('os.remove')
    def test_delete_secret_existing(self, mock_remove, mock_get_path):
        """Test deleting an existing secret."""
        # Mock a path that exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path
        
        # Call the function
        delete_secret("test_secret")
        
        # Verify os.remove was called
        mock_remove.assert_called_once_with(mock_path)

    @patch('epic_fhir_integration.security.secret_store.get_secret_path')
    def test_delete_secret_nonexistent(self, mock_get_path):
        """Test deleting a non-existent secret."""
        # Mock a path that doesn't exist
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path
        
        # Call the function and verify it raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            delete_secret("nonexistent_secret")

    @patch('pathlib.Path.resolve')
    def test_list_secrets_empty(self, mock_resolve):
        """Test listing secrets when none exist."""
        # Setup mock path for an empty directory
        mock_path = MagicMock()
        mock_path.parent.parent.parent = Path("/mock/base/dir")
        mock_resolve.return_value = mock_path
        
        # Mock the secrets directory that doesn't exist
        with patch('pathlib.Path.__truediv__', return_value=Path("/nonexistent/dir")):
            with patch('pathlib.Path.exists', return_value=False):
                # Call the function
                secrets = list_secrets()
                
                # Verify empty list is returned
                assert secrets == []

    @patch('pathlib.Path.resolve')
    def test_list_secrets_with_files(self, mock_resolve):
        """Test listing secrets when some exist."""
        # Setup mock path
        mock_path = MagicMock()
        mock_path.parent.parent.parent = Path("/mock/base/dir")
        mock_resolve.return_value = mock_path
        
        # Create temp directory with some files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some "secret" files
            for name in ["secret1.json", "secret2.txt"]:
                with open(temp_path / name, "w") as f:
                    f.write("test content")
            
            # Create a subdirectory (should be ignored)
            os.mkdir(temp_path / "subdir")
            
            # Mock the secrets directory
            with patch('pathlib.Path.__truediv__', return_value=temp_path):
                with patch('pathlib.Path.exists', return_value=True):
                    # Call the function
                    secrets = list_secrets()
                    
                    # Verify the correct secrets are returned (sorted by default)
                    assert set(secrets) == {"secret1.json", "secret2.txt"} 