"""
Path Utilities for EPIC FHIR Integration

This module provides utility functions for managing paths and directories
across the FHIR pipeline.
"""

import os
import datetime
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

def get_run_root(output_dir: Union[str, Path]) -> Path:
    """
    Get the root directory for a test run.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Path to test run root directory
    """
    output_dir = Path(output_dir)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return output_dir / f"TEST_{timestamp}"

def create_dataset_structure(output_dir: Union[str, Path]) -> Dict[str, Path]:
    """
    Create a standard dataset directory structure.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Dictionary mapping directory names to paths
    """
    root_dir = get_run_root(output_dir)
    
    # Define standard directories
    directories = {
        "bronze": root_dir / "bronze",
        "silver": root_dir / "silver",
        "gold": root_dir / "gold",
        "logs": root_dir / "logs",
        "reports": root_dir / "reports",
        "metrics": root_dir / "metrics",
        "schemas": root_dir / "schemas",
        "validation": root_dir / "validation"
    }
    
    # Create directories
    for name, path in directories.items():
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {path}")
    
    # Create metadata file
    create_run_metadata(root_dir)
    
    return directories

def create_run_metadata(run_dir: Union[str, Path], **kwargs) -> Path:
    """
    Create a run metadata file with information about the run.
    
    Args:
        run_dir: Run directory
        **kwargs: Additional metadata to include
        
    Returns:
        Path to metadata file
    """
    import json
    import platform
    import sys
    
    run_dir = Path(run_dir)
    metadata_file = run_dir / "run_info.json"
    
    # Default metadata
    metadata = {
        "start_timestamp": datetime.datetime.now().isoformat(),
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "hostname": platform.node()
        },
        "params": {},
    }
    
    # Add additional metadata
    metadata.update(kwargs)
    
    # Write to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata_file

def update_run_metadata(run_dir: Union[str, Path], **kwargs) -> Path:
    """
    Update an existing run metadata file.
    
    Args:
        run_dir: Run directory
        **kwargs: Metadata to update
        
    Returns:
        Path to metadata file
    """
    import json
    
    run_dir = Path(run_dir)
    metadata_file = run_dir / "run_info.json"
    
    # Read existing metadata
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    # Update metadata
    for key, value in kwargs.items():
        if key in metadata and isinstance(metadata[key], dict) and isinstance(value, dict):
            # Update nested dictionary
            metadata[key].update(value)
        else:
            # Replace or add key
            metadata[key] = value
    
    # Add end timestamp if specified
    if 'end_run' in kwargs and kwargs['end_run']:
        metadata['end_timestamp'] = datetime.datetime.now().isoformat()
    
    # Write back to file
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata_file

def cleanup_old_test_directories(output_dir: Union[str, Path], keep_latest: int = 5) -> List[Path]:
    """
    Clean up old test directories, keeping only the specified number of latest ones.
    
    Args:
        output_dir: Base output directory
        keep_latest: Number of latest test directories to keep
        
    Returns:
        List of removed directories
    """
    output_dir = Path(output_dir)
    
    # Find all test directories
    test_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("TEST_")]
    
    # Sort by name (which includes timestamp)
    test_dirs.sort(reverse=True)
    
    # Determine which ones to remove
    dirs_to_remove = test_dirs[keep_latest:]
    
    # Remove old directories
    removed = []
    for dir_path in dirs_to_remove:
        try:
            shutil.rmtree(dir_path)
            logger.info(f"Removed old test directory: {dir_path}")
            removed.append(dir_path)
        except Exception as e:
            logger.error(f"Failed to remove directory {dir_path}: {e}")
    
    return removed

def get_latest_test_directory(output_dir: Union[str, Path]) -> Optional[Path]:
    """
    Get the latest test directory in the output directory.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Path to latest test directory, or None if no test directories exist
    """
    output_dir = Path(output_dir)
    
    # Find all test directories
    test_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("TEST_")]
    
    if not test_dirs:
        return None
    
    # Sort by name (which includes timestamp) and return latest
    test_dirs.sort(reverse=True)
    return test_dirs[0] 