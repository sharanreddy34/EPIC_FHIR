"""
Stub implementation of transforms.api for local testing.

This module provides mock versions of the Foundry transforms API
to allow for local testing without requiring the actual Foundry SDK.
"""

from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass
import inspect


@dataclass
class TransformContext:
    """Mock TransformContext class."""
    
    _watermarks: Dict[str, str] = None
    spark_session = None
    
    def __init__(self):
        self._watermarks = {}
    
    def get_last_watermark(self) -> Optional[str]:
        """Get the last watermark."""
        return self._watermarks.get("last", None)
    
    def set_next_watermark(self, watermark: str) -> None:
        """Set the next watermark."""
        self._watermarks["next"] = watermark


@dataclass
class Secret:
    """Mock Secret class."""
    
    name: str
    
    def get(self) -> str:
        """Get the secret value from environment variables."""
        import os
        value = os.environ.get(self.name)
        if value is None:
            raise ValueError(f"Secret {self.name} not found in environment variables")
        return value


@dataclass
class Output:
    """Mock Output class."""
    
    uri: str
    
    def __init__(self, uri: str):
        self.uri = uri


@dataclass
class Input:
    """Mock Input class."""
    
    uri: str
    
    def __init__(self, uri: str):
        self.uri = uri


@dataclass
class Config:
    """Mock Config class."""
    
    key: str
    default_value: Any
    
    def __init__(self, key: str, default_value: Any = None):
        self.key = key
        self.default_value = default_value


F = TypeVar('F', bound=Callable[..., Any])


def transform_df(*args: Any) -> Callable[[F], F]:
    """Mock transform_df decorator."""
    def decorator(func: F) -> F:
        return func
    return decorator


def incremental(snapshot_inputs: bool = False) -> Callable[[F], F]:
    """Mock incremental decorator."""
    def decorator(func: F) -> F:
        return func
    return decorator 