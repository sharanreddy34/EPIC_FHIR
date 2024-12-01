"""
Disk Space Monitoring Utilities

This module provides utilities for monitoring disk space and ensuring
sufficient space is available for pipeline operations.
"""

import os
import time
import shutil
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Union, Tuple

# Configure logger
logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_MIN_FREE_SPACE_GB = 10.0
DEFAULT_MIN_FREE_SPACE_PERCENT = 10.0
DEFAULT_WARNING_THRESHOLD_GB = 20.0
DEFAULT_WARNING_THRESHOLD_PERCENT = 20.0
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes


def get_disk_space(path: Union[str, Path]) -> Dict[str, float]:
    """
    Get disk space information for a given path.
    
    Args:
        path: Path to check
        
    Returns:
        Dictionary with disk space information:
            - total_gb: Total disk space in GB
            - used_gb: Used disk space in GB
            - free_gb: Free disk space in GB
            - free_percent: Free disk space as a percentage
    """
    path = Path(path).resolve()
    
    # Get disk usage
    disk_usage = shutil.disk_usage(path)
    
    # Convert to GB
    bytes_per_gb = 1024 ** 3
    total_gb = disk_usage.total / bytes_per_gb
    free_gb = disk_usage.free / bytes_per_gb
    used_gb = disk_usage.used / bytes_per_gb
    
    # Calculate free percentage
    free_percent = (disk_usage.free / disk_usage.total) * 100
    
    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "free_percent": free_percent,
        "path": str(path)
    }


def check_disk_space(
    path: Union[str, Path],
    min_free_gb: float = DEFAULT_MIN_FREE_SPACE_GB,
    min_free_percent: float = DEFAULT_MIN_FREE_SPACE_PERCENT
) -> Tuple[bool, Dict[str, float]]:
    """
    Check if there is sufficient disk space available.
    
    Args:
        path: Path to check
        min_free_gb: Minimum free space in GB
        min_free_percent: Minimum free space as a percentage
        
    Returns:
        Tuple with check result (True if sufficient space, False otherwise) and
        disk space information
    """
    disk_space = get_disk_space(path)
    
    # Check if sufficient space is available
    has_sufficient_space = (
        disk_space["free_gb"] >= min_free_gb and
        disk_space["free_percent"] >= min_free_percent
    )
    
    if not has_sufficient_space:
        logger.warning(
            f"Insufficient disk space for {path}: "
            f"{disk_space['free_gb']:.2f} GB ({disk_space['free_percent']:.2f}%) free, "
            f"minimum required: {min_free_gb:.2f} GB or {min_free_percent:.2f}%"
        )
    else:
        logger.debug(
            f"Sufficient disk space for {path}: "
            f"{disk_space['free_gb']:.2f} GB ({disk_space['free_percent']:.2f}%) free"
        )
    
    return has_sufficient_space, disk_space


def find_cleanable_files(
    path: Union[str, Path],
    pattern: str = "TEST_*",
    keep_latest: int = 5
) -> List[Path]:
    """
    Find files/directories that can be safely cleaned up to free space.
    
    Args:
        path: Base path to search
        pattern: Glob pattern to match
        keep_latest: Number of latest files/directories to keep
        
    Returns:
        List of paths that can be safely cleaned up
    """
    path = Path(path)
    
    # Find files/directories matching pattern
    matches = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Keep the latest N files/directories
    to_clean = matches[keep_latest:] if len(matches) > keep_latest else []
    
    if to_clean:
        total_size_bytes = sum(get_dir_size(p) for p in to_clean)
        total_size_gb = total_size_bytes / (1024 ** 3)
        logger.info(
            f"Found {len(to_clean)} items that can be cleaned up in {path}, "
            f"totaling {total_size_gb:.2f} GB"
        )
    
    return to_clean


def get_dir_size(path: Path) -> int:
    """
    Get the total size of a directory.
    
    Args:
        path: Path to directory
        
    Returns:
        Total size in bytes
    """
    if path.is_file():
        return path.stat().st_size
    
    total_size = 0
    for item in path.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size
    
    return total_size


def cleanup_space(
    path: Union[str, Path],
    pattern: str = "TEST_*",
    keep_latest: int = 5,
    min_free_gb: float = DEFAULT_MIN_FREE_SPACE_GB
) -> bool:
    """
    Cleanup space to ensure minimum free space is available.
    
    Args:
        path: Base path to search for cleanable files
        pattern: Glob pattern to match
        keep_latest: Number of latest files/directories to keep
        min_free_gb: Minimum free space in GB to maintain
        
    Returns:
        True if sufficient space is available after cleanup, False otherwise
    """
    path = Path(path)
    
    # Check current disk space
    has_sufficient_space, disk_space = check_disk_space(path, min_free_gb, 0)
    
    if has_sufficient_space:
        logger.info(f"Sufficient disk space available: {disk_space['free_gb']:.2f} GB")
        return True
    
    # Find files/directories that can be cleaned up
    to_clean = find_cleanable_files(path, pattern, keep_latest)
    
    if not to_clean:
        logger.warning(
            f"No files/directories found to clean up in {path}, "
            f"insufficient space remains: {disk_space['free_gb']:.2f} GB"
        )
        return False
    
    # Clean up files/directories
    cleaned_count = 0
    cleaned_size = 0
    
    for item in to_clean:
        try:
            # Get item size before removal
            item_size = get_dir_size(item)
            
            # Remove item
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
                
            cleaned_count += 1
            cleaned_size += item_size
            
            logger.info(f"Cleaned up {item} ({item_size / (1024**3):.2f} GB)")
            
            # Check if sufficient space is now available
            has_sufficient_space, disk_space = check_disk_space(path, min_free_gb, 0)
            if has_sufficient_space:
                break
        except Exception as e:
            logger.warning(f"Error cleaning up {item}: {e}")
    
    # Log results
    cleaned_size_gb = cleaned_size / (1024 ** 3)
    logger.info(
        f"Cleaned up {cleaned_count} items, totaling {cleaned_size_gb:.2f} GB. "
        f"Free space now: {disk_space['free_gb']:.2f} GB"
    )
    
    return has_sufficient_space


class DiskSpaceMonitor:
    """
    Monitor disk space and perform cleanup when necessary.
    
    This class provides a background thread that periodically checks
    disk space and performs cleanup operations when necessary.
    """
    
    def __init__(
        self,
        path: Union[str, Path],
        min_free_gb: float = DEFAULT_MIN_FREE_SPACE_GB,
        min_free_percent: float = DEFAULT_MIN_FREE_SPACE_PERCENT,
        warning_threshold_gb: float = DEFAULT_WARNING_THRESHOLD_GB,
        warning_threshold_percent: float = DEFAULT_WARNING_THRESHOLD_PERCENT,
        check_interval: float = DEFAULT_CHECK_INTERVAL,
        cleanup_pattern: str = "TEST_*",
        keep_latest: int = 5,
        on_warning: Optional[Callable[[Dict[str, float]], None]] = None,
        on_critical: Optional[Callable[[Dict[str, float]], None]] = None,
        auto_cleanup: bool = True
    ):
        """
        Initialize disk space monitor.
        
        Args:
            path: Path to monitor
            min_free_gb: Minimum free space in GB
            min_free_percent: Minimum free space as a percentage
            warning_threshold_gb: Warning threshold in GB
            warning_threshold_percent: Warning threshold as a percentage
            check_interval: Check interval in seconds
            cleanup_pattern: Glob pattern for files/directories to clean up
            keep_latest: Number of latest files/directories to keep
            on_warning: Callback function for warning condition
            on_critical: Callback function for critical condition
            auto_cleanup: Whether to automatically clean up space
        """
        self.path = Path(path)
        self.min_free_gb = min_free_gb
        self.min_free_percent = min_free_percent
        self.warning_threshold_gb = warning_threshold_gb
        self.warning_threshold_percent = warning_threshold_percent
        self.check_interval = check_interval
        self.cleanup_pattern = cleanup_pattern
        self.keep_latest = keep_latest
        self.on_warning = on_warning
        self.on_critical = on_critical
        self.auto_cleanup = auto_cleanup
        
        self._stop_event = threading.Event()
        self._thread = None
        self._running = False
    
    def start(self):
        """Start monitoring disk space."""
        if self._running:
            logger.warning("Disk space monitor is already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self._running = True
        
        logger.info(
            f"Started disk space monitor for {self.path} "
            f"(min: {self.min_free_gb:.2f} GB, "
            f"warning: {self.warning_threshold_gb:.2f} GB, "
            f"check interval: {self.check_interval}s)"
        )
    
    def stop(self):
        """Stop monitoring disk space."""
        if not self._running:
            logger.warning("Disk space monitor is not running")
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._running = False
        
        logger.info("Stopped disk space monitor")
    
    def is_running(self):
        """Check if monitor is running."""
        return self._running
    
    def check_now(self) -> Dict[str, float]:
        """
        Perform an immediate disk space check.
        
        Returns:
            Dictionary with disk space information
        """
        _, disk_space = self._check_disk_space()
        return disk_space
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Check disk space
                status, disk_space = self._check_disk_space()
                
                # Handle disk space status
                if status == "critical":
                    # Critical disk space situation
                    if self.auto_cleanup:
                        # Attempt cleanup
                        cleanup_success = cleanup_space(
                            self.path,
                            self.cleanup_pattern,
                            self.keep_latest,
                            self.min_free_gb
                        )
                        
                        if not cleanup_success:
                            logger.critical(
                                f"Critical disk space situation for {self.path}: "
                                f"{disk_space['free_gb']:.2f} GB free, cleanup failed"
                            )
                    else:
                        logger.critical(
                            f"Critical disk space situation for {self.path}: "
                            f"{disk_space['free_gb']:.2f} GB free"
                        )
                    
                    # Call critical callback
                    if self.on_critical:
                        try:
                            self.on_critical(disk_space)
                        except Exception as e:
                            logger.warning(f"Error in on_critical callback: {e}")
                            
                elif status == "warning":
                    # Warning disk space situation
                    logger.warning(
                        f"Low disk space for {self.path}: "
                        f"{disk_space['free_gb']:.2f} GB free"
                    )
                    
                    # Call warning callback
                    if self.on_warning:
                        try:
                            self.on_warning(disk_space)
                        except Exception as e:
                            logger.warning(f"Error in on_warning callback: {e}")
            except Exception as e:
                logger.error(f"Error in disk space monitor: {e}")
            
            # Wait for next check
            self._stop_event.wait(self.check_interval)
    
    def _check_disk_space(self) -> Tuple[str, Dict[str, float]]:
        """
        Check disk space and determine status.
        
        Returns:
            Tuple with status ("ok", "warning", or "critical") and
            disk space information
        """
        disk_space = get_disk_space(self.path)
        
        # Check if critical
        if (disk_space["free_gb"] < self.min_free_gb or
            disk_space["free_percent"] < self.min_free_percent):
            return "critical", disk_space
        
        # Check if warning
        if (disk_space["free_gb"] < self.warning_threshold_gb or
            disk_space["free_percent"] < self.warning_threshold_percent):
            return "warning", disk_space
        
        # Otherwise, ok
        return "ok", disk_space


# Global disk space monitor instance
_MONITOR_INSTANCE = None

def start_disk_monitoring(
    path: Union[str, Path],
    min_free_gb: float = DEFAULT_MIN_FREE_SPACE_GB,
    warning_threshold_gb: float = DEFAULT_WARNING_THRESHOLD_GB,
    check_interval: float = DEFAULT_CHECK_INTERVAL,
    auto_cleanup: bool = True
) -> DiskSpaceMonitor:
    """
    Start disk space monitoring.
    
    This function starts a global disk space monitor instance.
    
    Args:
        path: Path to monitor
        min_free_gb: Minimum free space in GB
        warning_threshold_gb: Warning threshold in GB
        check_interval: Check interval in seconds
        auto_cleanup: Whether to automatically clean up space
        
    Returns:
        Disk space monitor instance
    """
    global _MONITOR_INSTANCE
    
    if _MONITOR_INSTANCE is not None:
        if _MONITOR_INSTANCE.is_running():
            logger.info("Stopping existing disk space monitor")
            _MONITOR_INSTANCE.stop()
    
    # Create new monitor instance
    _MONITOR_INSTANCE = DiskSpaceMonitor(
        path=path,
        min_free_gb=min_free_gb,
        warning_threshold_gb=warning_threshold_gb,
        check_interval=check_interval,
        auto_cleanup=auto_cleanup
    )
    
    # Start monitoring
    _MONITOR_INSTANCE.start()
    
    return _MONITOR_INSTANCE

def stop_disk_monitoring():
    """Stop disk space monitoring."""
    global _MONITOR_INSTANCE
    
    if _MONITOR_INSTANCE is not None and _MONITOR_INSTANCE.is_running():
        _MONITOR_INSTANCE.stop()
        _MONITOR_INSTANCE = None
        
def get_disk_monitor() -> Optional[DiskSpaceMonitor]:
    """Get the global disk space monitor instance."""
    return _MONITOR_INSTANCE 