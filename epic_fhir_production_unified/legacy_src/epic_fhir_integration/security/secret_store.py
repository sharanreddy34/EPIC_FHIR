"""
Secret store module for secure handling of sensitive information.

This module provides functions to handle sensitive information such as API tokens
and private keys without printing or logging their values.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


class SecretValue:
    """Container for secret values that prevents accidental printing."""
    
    def __init__(self, value: Any):
        self._value = value
    
    def get(self) -> Any:
        """Get the actual secret value."""
        return self._value
    
    def __repr__(self) -> str:
        """Return a masked representation of the secret."""
        return "***SECRET***"
    
    def __str__(self) -> str:
        """Return a masked string representation of the secret."""
        return "***SECRET***"


def get_secret_path(name: str) -> Path:
    """Get the path to a secret file in the secrets directory.
    
    Args:
        name: Name of the secret file.
        
    Returns:
        Path to the secret file.
    """
    # Use the module's location to determine the secrets path
    base_dir = Path(__file__).resolve().parent.parent.parent
    secrets_dir = base_dir / "secrets"
    
    # Create the secrets directory if it doesn't exist
    secrets_dir.mkdir(exist_ok=True)
    
    return secrets_dir / name


def save_secret(name: str, value: Any) -> None:
    """Save a secret to a file.
    
    Args:
        name: Name of the secret file.
        value: Secret value to save.
    """
    secret_path = get_secret_path(name)
    
    # Handle different types of secrets
    if isinstance(value, dict):
        with open(secret_path, "w") as f:
            json.dump(value, f)
    else:
        with open(secret_path, "w") as f:
            f.write(str(value))


def load_secret(name: str) -> SecretValue:
    """Load a secret from a file.
    
    Args:
        name: Name of the secret file.
        
    Returns:
        SecretValue containing the loaded secret.
        
    Raises:
        FileNotFoundError: If the secret file doesn't exist.
    """
    secret_path = get_secret_path(name)
    
    if not secret_path.exists():
        raise FileNotFoundError(f"Secret '{name}' not found")
    
    # Try to load as JSON first
    try:
        with open(secret_path, "r") as f:
            value = json.load(f)
    except json.JSONDecodeError:
        # If not JSON, load as text
        with open(secret_path, "r") as f:
            value = f.read().strip()
    
    return SecretValue(value)


def delete_secret(name: str) -> None:
    """Delete a secret file.
    
    Args:
        name: Name of the secret file.
        
    Raises:
        FileNotFoundError: If the secret file doesn't exist.
    """
    secret_path = get_secret_path(name)
    
    if not secret_path.exists():
        raise FileNotFoundError(f"Secret '{name}' not found")
    
    os.remove(secret_path)


def list_secrets() -> list:
    """List all available secrets.
    
    Returns:
        List of secret names.
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    secrets_dir = base_dir / "secrets"
    
    if not secrets_dir.exists():
        return []
    
    return [f.name for f in secrets_dir.iterdir() if f.is_file()] 