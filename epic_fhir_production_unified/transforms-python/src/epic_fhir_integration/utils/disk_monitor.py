"""
Disk monitoring utility for FHIR data processing.

This module provides tools to monitor disk space usage during data processing,
which is critical for managing large-scale FHIR resource extraction operations.
"""

import os
import shutil
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from epic_fhir_integration.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DiskUsageInfo:
    """Information about disk usage for a path."""
    
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    
    @property
    def total_gb(self) -> float:
        """Total space in gigabytes."""
        return self.total_bytes / (1024 ** 3)
    
    @property
    def used_gb(self) -> float:
        """Used space in gigabytes."""
        return self.used_bytes / (1024 ** 3)
    
    @property
    def free_gb(self) -> float:
        """Free space in gigabytes."""
        return self.free_bytes / (1024 ** 3)
    
    @property
    def usage_percent(self) -> float:
        """Percentage of disk used."""
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100


def get_disk_usage(path: Union[str, Path]) -> DiskUsageInfo:
    """
    Get disk usage information for a path.
    
    Args:
        path: Path to check disk usage for
        
    Returns:
        DiskUsageInfo object with usage details
    """
    path_str = str(path)
    
    try:
        total, used, free = shutil.disk_usage(path_str)
        return DiskUsageInfo(
            path=path_str,
            total_bytes=total,
            used_bytes=used,
            free_bytes=free,
        )
    except Exception as e:
        logger.error(f"Failed to get disk usage for {path_str}: {e}")
        # Return default values
        return DiskUsageInfo(
            path=path_str,
            total_bytes=0,
            used_bytes=0,
            free_bytes=0,
        )


def check_disk_space(
    path: Union[str, Path], 
    min_free_gb: float = 10.0
) -> bool:
    """
    Check if there is sufficient disk space available.
    
    Args:
        path: Path to check disk space for
        min_free_gb: Minimum required free space in GB
        
    Returns:
        True if there is enough free space, False otherwise
    """
    usage = get_disk_usage(path)
    
    if usage.free_gb < min_free_gb:
        logger.warning(
            f"Low disk space on {path}: {usage.free_gb:.2f}GB free, "
            f"{usage.usage_percent:.1f}% used"
        )
        return False
    
    return True


def get_dir_size(path: Union[str, Path]) -> int:
    """
    Calculate the total size of a directory in bytes.
    
    Args:
        path: Directory path to calculate size for
        
    Returns:
        Size in bytes
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return 0
    
    if path_obj.is_file():
        return path_obj.stat().st_size
    
    total_size = 0
    for dirpath, _, filenames in os.walk(str(path_obj)):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(file_path)
            except (FileNotFoundError, PermissionError):
                # Skip files that can't be accessed
                pass
    
    return total_size


def find_largest_dirs(
    base_path: Union[str, Path], 
    max_depth: int = 2
) -> List[Dict[str, Union[str, int, float]]]:
    """
    Find the largest subdirectories under a base path.
    
    Args:
        base_path: Base directory to search
        max_depth: Maximum directory depth to recurse
        
    Returns:
        List of dictionaries containing path and size information,
        sorted by size (largest first)
    """
    base_path_obj = Path(base_path)
    if not base_path_obj.is_dir():
        return []
    
    results = []
    
    def scan_dir(path: Path, depth: int = 0):
        if depth > max_depth:
            return
        
        try:
            # Only consider directories
            subdirs = [d for d in path.iterdir() if d.is_dir()]
            
            for subdir in subdirs:
                size_bytes = get_dir_size(subdir)
                size_mb = size_bytes / (1024 ** 2)
                
                results.append({
                    "path": str(subdir),
                    "size_bytes": size_bytes,
                    "size_mb": size_mb,
                })
                
                # Recurse if not at max depth
                if depth < max_depth:
                    scan_dir(subdir, depth + 1)
        
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Could not scan {path}: {e}")
    
    scan_dir(base_path_obj)
    
    # Sort by size (largest first)
    return sorted(results, key=lambda x: x["size_bytes"], reverse=True)


def clean_temp_files(
    base_path: Union[str, Path], 
    pattern: str = "*.tmp", 
    min_age_hours: Optional[float] = None
) -> int:
    """
    Clean temporary files matching a pattern.
    
    Args:
        base_path: Directory to clean
        pattern: Glob pattern for files to delete
        min_age_hours: Only delete files older than this many hours
        
    Returns:
        Number of files deleted
    """
    import time
    import glob
    
    base_path_obj = Path(base_path)
    if not base_path_obj.is_dir():
        return 0
    
    count = 0
    current_time = time.time()
    
    for file_path in glob.glob(os.path.join(str(base_path_obj), pattern), recursive=True):
        try:
            # Check file age if specified
            if min_age_hours is not None:
                file_age_hours = (current_time - os.path.getmtime(file_path)) / 3600
                if file_age_hours < min_age_hours:
                    continue
            
            os.remove(file_path)
            count += 1
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Could not delete {file_path}: {e}")
    
    return count 