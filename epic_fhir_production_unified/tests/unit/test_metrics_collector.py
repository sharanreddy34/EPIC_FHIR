#!/usr/bin/env python3
"""
Unit Tests for Metrics Collector

This module contains tests for the metrics collector functionality,
testing different value types, concurrent recording, and persistence.
"""

import os
import json
import time
import tempfile
import threading
import unittest
import subprocess
from pathlib import Path
from unittest import mock

import pandas as pd

from epic_fhir_integration.metrics.collector import (
    MetricsCollector,
    get_collector_instance,
    record_metric,
    flush_metrics,
    track_resource_usage
)


class TestMetricsCollector(unittest.TestCase):
    """Test cases for the MetricsCollector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a new collector for each test
        self.collector = MetricsCollector()
        
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Clear the collector
        self.collector.clear()
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
        
    def test_record_string_value(self):
        """Test recording a string metric value."""
        self.collector.record("test", "string_metric", "test_value")
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["step"], "test")
        self.assertEqual(metrics[0]["name"], "string_metric")
        self.assertEqual(metrics[0]["value"], "test_value")
        self.assertEqual(metrics[0]["metric_type"], "RUNTIME")
        
    def test_record_numeric_values(self):
        """Test recording numeric metric values (int and float)."""
        # Test integer
        self.collector.record("test", "int_metric", 42)
        
        # Test float
        self.collector.record("test", "float_metric", 3.14159)
        
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0]["value"], 42)
        self.assertEqual(metrics[1]["value"], 3.14159)
        
    def test_record_dict_value(self):
        """Test recording a dictionary metric value."""
        test_dict = {"key1": "value1", "key2": 42, "nested": {"inner": "value"}}
        self.collector.record("test", "dict_metric", test_dict)
        
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["value"], test_dict)
        
    def test_record_list_value(self):
        """Test recording a list metric value."""
        test_list = ["item1", 42, 3.14, {"key": "value"}]
        self.collector.record("test", "list_metric", test_list)
        
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["value"], test_list)
        
    def test_record_with_details(self):
        """Test recording a metric with details."""
        details = {"source": "test", "duration_ms": 150, "success": True}
        self.collector.record("test", "detailed_metric", 42, details=details)
        
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(json.loads(metrics[0]["details"]), details)
        
    def test_flush_to_file(self):
        """Test flushing metrics to a file."""
        # Record some metrics
        self.collector.record("test", "metric1", 1)
        self.collector.record("test", "metric2", 2)
        
        # Flush to file
        output_path = self.collector.flush(self.output_dir)
        
        # Verify file was created
        self.assertIsNotNone(output_path)
        output_file = Path(output_path)
        self.assertTrue(output_file.exists())
        
        # Verify file contains the metrics
        df = pd.read_parquet(output_file)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["name"], "metric1")
        self.assertEqual(df.iloc[1]["name"], "metric2")
        
    def test_concurrent_recording(self):
        """Test recording metrics concurrently from multiple threads."""
        # Use a shared collector for this test
        collector = get_collector_instance()
        collector.clear()  # Ensure it's clean
        
        # Function to record metrics in a thread
        def record_metrics(thread_id, num_metrics):
            for i in range(num_metrics):
                record_metric(
                    f"thread_{thread_id}", 
                    f"metric_{i}", 
                    i * thread_id
                )
                
        # Create and start threads
        threads = []
        num_threads = 5
        metrics_per_thread = 20
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=record_metrics, 
                args=(i, metrics_per_thread)
            )
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Check that all metrics were recorded
        metrics = collector.get_metrics()
        self.assertEqual(len(metrics), num_threads * metrics_per_thread)
        
        # Cleanup
        collector.clear()
        
    def test_atexit_handler(self):
        """Test that metrics are flushed on exit."""
        with mock.patch.object(self.collector, 'flush') as mock_flush:
            # Call the atexit handler directly
            self.collector.record("test", "exit_metric", 42)
            self.collector._atexit_handler()
            
            # Check that flush was called
            mock_flush.assert_called_once()
            
    def test_metric_persistence_across_restarts(self):
        """Test that metrics persist across process restarts."""
        # Create a script that will record metrics and exit
        script_content = """
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.abspath('.'))

from epic_fhir_integration.metrics.collector import record_metric, flush_metrics

# Record a metric
record_metric("persistence_test", "restart_metric", 123)

# Flush to the specified directory
output_dir = Path(sys.argv[1])
flush_metrics(output_dir)
"""
        
        script_file = self.output_dir / "test_script.py"
        with open(script_file, "w") as f:
            f.write(script_content)
            
        # Run the script to record metrics
        result = subprocess.run(
            [sys.executable, str(script_file), str(self.output_dir)],
            capture_output=True,
            text=True
        )
        
        # Check the script ran successfully
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")
        
        # Check that metrics file exists
        metrics_file = self.output_dir / "performance_metrics.parquet"
        self.assertTrue(metrics_file.exists())
        
        # Read the metrics
        df = pd.read_parquet(metrics_file)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["step"], "persistence_test")
        self.assertEqual(df.iloc[0]["name"], "restart_metric")
        self.assertEqual(df.iloc[0]["value"], 123)
        
        # Run a second script to append more metrics
        script_content = """
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.abspath('.'))

from epic_fhir_integration.metrics.collector import record_metric, flush_metrics

# Record another metric
record_metric("persistence_test", "second_metric", 456)

# Flush to the same directory
output_dir = Path(sys.argv[1])
flush_metrics(output_dir)
"""
        
        with open(script_file, "w") as f:
            f.write(script_content)
            
        # Run the second script
        result = subprocess.run(
            [sys.executable, str(script_file), str(self.output_dir)],
            capture_output=True,
            text=True
        )
        
        # Check the script ran successfully
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")
        
        # Read the metrics again
        df = pd.read_parquet(metrics_file)
        
        # Check that both metrics are present
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["name"], "restart_metric")
        self.assertEqual(df.iloc[1]["name"], "second_metric")


class TestMetricsHelper(unittest.TestCase):
    """Test cases for the metric helper functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        
        # Clear the singleton collector instance
        collector = get_collector_instance()
        collector.clear()
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Clear the singleton collector instance
        collector = get_collector_instance()
        collector.clear()
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
        
    def test_record_metric_helper(self):
        """Test the record_metric helper function."""
        record_metric("helper_test", "helper_metric", 42)
        
        # Get metrics from singleton instance
        collector = get_collector_instance()
        metrics = collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["step"], "helper_test")
        self.assertEqual(metrics[0]["name"], "helper_metric")
        self.assertEqual(metrics[0]["value"], 42)
        
    def test_flush_metrics_helper(self):
        """Test the flush_metrics helper function."""
        # Record a metric
        record_metric("helper_test", "flush_metric", 42)
        
        # Flush metrics
        output_path = flush_metrics(self.output_dir)
        
        # Verify file was created
        self.assertIsNotNone(output_path)
        output_file = Path(output_path)
        self.assertTrue(output_file.exists())
        
        # Verify file contains the metric
        df = pd.read_parquet(output_file)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["step"], "helper_test")
        self.assertEqual(df.iloc[0]["name"], "flush_metric")
        
    def test_track_resource_usage(self):
        """Test the track_resource_usage helper function."""
        # Start tracking with a short interval
        stop_tracking = track_resource_usage(interval=0.1, output_dir=self.output_dir)
        
        # Wait for a few intervals
        time.sleep(0.5)
        
        # Stop tracking
        stopped = stop_tracking()
        self.assertTrue(stopped)
        
        # Check that metrics were recorded
        metrics_file = self.output_dir / "performance_metrics.parquet"
        self.assertTrue(metrics_file.exists())
        
        # Read the metrics
        df = pd.read_parquet(metrics_file)
        
        # Verify resource metrics were recorded
        self.assertGreater(len(df), 0)
        self.assertEqual(df.iloc[0]["step"], "system")
        self.assertIn(df.iloc[0]["name"], [
            "memory_percent", "memory_mb", "cpu_percent", 
            "thread_count", "open_files"
        ])


if __name__ == "__main__":
    unittest.main() 