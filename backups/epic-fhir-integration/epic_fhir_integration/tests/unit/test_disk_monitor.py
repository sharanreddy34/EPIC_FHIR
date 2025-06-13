#!/usr/bin/env python3
"""
Unit Tests for Disk Space Monitoring Utilities

This module contains tests for the disk space monitoring functionality.
"""

import os
import time
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from epic_fhir_integration.utils.disk_monitor import (
    get_disk_space,
    check_disk_space,
    find_cleanable_files,
    get_dir_size,
    cleanup_space,
    DiskSpaceMonitor,
    start_disk_monitoring,
    stop_disk_monitoring,
    DEFAULT_MIN_FREE_SPACE_GB
)


class TestDiskSpaceUtils(unittest.TestCase):
    """Test cases for disk space utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Create some test files and directories
        self.create_test_files()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def create_test_files(self):
        """Create test files and directories."""
        # Create a series of test directories with timestamps in name
        for i in range(10):
            test_dir = self.test_dir / f"TEST_{i:04d}"
            test_dir.mkdir(exist_ok=True)
            
            # Create some files in each directory
            for j in range(3):
                test_file = test_dir / f"file_{j}.txt"
                with open(test_file, "w") as f:
                    # Write some data to each file (1KB per file)
                    f.write("X" * 1024)
            
            # Set modification time based on index
            os.utime(test_dir, (time.time() - (10 - i) * 3600, time.time() - (10 - i) * 3600))
    
    def test_get_disk_space(self):
        """Test getting disk space information."""
        disk_space = get_disk_space(self.test_dir)
        
        # Basic checks
        self.assertIn("total_gb", disk_space)
        self.assertIn("used_gb", disk_space)
        self.assertIn("free_gb", disk_space)
        self.assertIn("free_percent", disk_space)
        self.assertIn("path", disk_space)
        
        # Verify values are reasonable
        self.assertGreater(disk_space["total_gb"], 0)
        self.assertGreaterEqual(disk_space["used_gb"], 0)
        self.assertGreaterEqual(disk_space["free_gb"], 0)
        self.assertGreaterEqual(disk_space["free_percent"], 0)
        self.assertLessEqual(disk_space["free_percent"], 100)
        
        # Path should be resolved
        self.assertEqual(disk_space["path"], str(self.test_dir.resolve()))
    
    def test_check_disk_space(self):
        """Test checking if disk space is sufficient."""
        # Test with very low threshold (should pass)
        result, disk_space = check_disk_space(self.test_dir, min_free_gb=0.001, min_free_percent=0.001)
        self.assertTrue(result)
        
        # Test with impossibly high threshold (should fail)
        result, disk_space = check_disk_space(self.test_dir, min_free_gb=1000000, min_free_percent=101)
        self.assertFalse(result)
    
    def test_get_dir_size(self):
        """Test directory size calculation."""
        # Create a specific test directory with known file sizes
        test_dir = self.test_dir / "SIZE_TEST"
        test_dir.mkdir(exist_ok=True)
        
        # Create files with specific sizes
        file_sizes = [1024, 2048, 4096]
        for i, size in enumerate(file_sizes):
            test_file = test_dir / f"file_{i}.txt"
            with open(test_file, "w") as f:
                f.write("X" * size)
        
        # Get directory size
        dir_size = get_dir_size(test_dir)
        
        # Size should be approximately the sum of file sizes
        expected_size = sum(file_sizes)
        self.assertAlmostEqual(dir_size, expected_size, delta=100)  # Allow small delta for filesystem overhead
        
        # Test size of a single file
        file_size = get_dir_size(test_dir / "file_0.txt")
        self.assertAlmostEqual(file_size, 1024, delta=10)
    
    def test_find_cleanable_files(self):
        """Test finding files that can be cleaned up."""
        # Find cleanable files, keeping latest 5
        to_clean = find_cleanable_files(self.test_dir, pattern="TEST_*", keep_latest=5)
        
        # Should have 5 directories to clean (10 total - 5 to keep)
        self.assertEqual(len(to_clean), 5)
        
        # Verify we're keeping the most recent ones
        for path in to_clean:
            # Extract index from directory name
            index = int(path.name.split("_")[1])
            # Older files should be cleaned (lower indexes)
            self.assertLess(index, 5)
    
    @mock.patch("epic_fhir_integration.utils.disk_monitor.check_disk_space")
    @mock.patch("epic_fhir_integration.utils.disk_monitor.shutil.rmtree")
    def test_cleanup_space(self, mock_rmtree, mock_check_disk_space):
        """Test cleaning up space."""
        # Mock check_disk_space to first return insufficient space, then sufficient
        mock_check_disk_space.side_effect = [
            (False, {"free_gb": 5.0, "free_percent": 5.0}),  # First call: insufficient
            (True, {"free_gb": 15.0, "free_percent": 15.0})  # Second call: sufficient
        ]
        
        # Call cleanup_space
        result = cleanup_space(self.test_dir, pattern="TEST_*", keep_latest=5, min_free_gb=10.0)
        
        # Should have successfully cleaned up space
        self.assertTrue(result)
        
        # Should have called rmtree at least once
        self.assertGreater(mock_rmtree.call_count, 0)
        
        # Should have checked disk space twice
        self.assertEqual(mock_check_disk_space.call_count, 2)


class TestDiskSpaceMonitor(unittest.TestCase):
    """Test cases for DiskSpaceMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Create mock callback functions
        self.warning_callback = mock.MagicMock()
        self.critical_callback = mock.MagicMock()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop any running monitors
        stop_disk_monitoring()
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    @mock.patch("epic_fhir_integration.utils.disk_monitor.DiskSpaceMonitor._check_disk_space")
    def test_monitor_status_ok(self, mock_check_disk_space):
        """Test monitor with OK status."""
        # Mock _check_disk_space to return OK status
        mock_check_disk_space.return_value = (
            "ok", 
            {
                "total_gb": 100.0, 
                "used_gb": 50.0, 
                "free_gb": 50.0, 
                "free_percent": 50.0, 
                "path": str(self.test_dir)
            }
        )
        
        # Create monitor with fast check interval
        monitor = DiskSpaceMonitor(
            path=self.test_dir,
            check_interval=0.1,
            on_warning=self.warning_callback,
            on_critical=self.critical_callback
        )
        
        # Start monitoring
        monitor.start()
        
        # Wait for a few checks
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop()
        
        # Callbacks should not have been called
        self.warning_callback.assert_not_called()
        self.critical_callback.assert_not_called()
    
    @mock.patch("epic_fhir_integration.utils.disk_monitor.DiskSpaceMonitor._check_disk_space")
    def test_monitor_status_warning(self, mock_check_disk_space):
        """Test monitor with warning status."""
        # Mock _check_disk_space to return warning status
        mock_check_disk_space.return_value = (
            "warning", 
            {
                "total_gb": 100.0, 
                "used_gb": 85.0, 
                "free_gb": 15.0, 
                "free_percent": 15.0, 
                "path": str(self.test_dir)
            }
        )
        
        # Create monitor with fast check interval
        monitor = DiskSpaceMonitor(
            path=self.test_dir,
            check_interval=0.1,
            on_warning=self.warning_callback,
            on_critical=self.critical_callback
        )
        
        # Start monitoring
        monitor.start()
        
        # Wait for a few checks
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop()
        
        # Warning callback should have been called at least once
        self.warning_callback.assert_called()
        
        # Critical callback should not have been called
        self.critical_callback.assert_not_called()
    
    @mock.patch("epic_fhir_integration.utils.disk_monitor.DiskSpaceMonitor._check_disk_space")
    @mock.patch("epic_fhir_integration.utils.disk_monitor.cleanup_space")
    def test_monitor_status_critical(self, mock_cleanup_space, mock_check_disk_space):
        """Test monitor with critical status."""
        # Mock _check_disk_space to return critical status
        mock_check_disk_space.return_value = (
            "critical", 
            {
                "total_gb": 100.0, 
                "used_gb": 95.0, 
                "free_gb": 5.0, 
                "free_percent": 5.0, 
                "path": str(self.test_dir)
            }
        )
        
        # Mock cleanup_space to return True (successful cleanup)
        mock_cleanup_space.return_value = True
        
        # Create monitor with fast check interval
        monitor = DiskSpaceMonitor(
            path=self.test_dir,
            check_interval=0.1,
            on_warning=self.warning_callback,
            on_critical=self.critical_callback,
            auto_cleanup=True
        )
        
        # Start monitoring
        monitor.start()
        
        # Wait for a few checks
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop()
        
        # Critical callback should have been called at least once
        self.critical_callback.assert_called()
        
        # Cleanup should have been attempted
        mock_cleanup_space.assert_called()
    
    def test_start_stop_global_monitor(self):
        """Test starting and stopping the global monitor."""
        # Start monitoring
        monitor = start_disk_monitoring(
            path=self.test_dir,
            min_free_gb=DEFAULT_MIN_FREE_SPACE_GB,
            check_interval=0.1
        )
        
        # Should have a running monitor
        self.assertIsNotNone(monitor)
        self.assertTrue(monitor.is_running())
        
        # Stop monitoring
        stop_disk_monitoring()
        
        # Monitor should have stopped
        self.assertFalse(monitor.is_running())


if __name__ == "__main__":
    unittest.main() 