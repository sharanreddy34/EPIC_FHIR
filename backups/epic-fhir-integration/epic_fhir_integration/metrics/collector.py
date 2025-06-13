"""
Metrics Collector for EPIC FHIR Integration

This module provides a facade for collecting metrics throughout the FHIR pipeline.
It stores metrics in memory and can flush them to disk in Parquet format
for analysis and reporting.
"""

import os
import sys
import time
import json
import atexit
import logging
import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Any, Optional, Union, Callable, Iterable

import pandas as pd

try:
    from pyspark.sql import SparkSession
    HAS_SPARK = True
except ImportError:
    HAS_SPARK = False

logger = logging.getLogger(__name__)

# Singleton instance for the metrics collector
_COLLECTOR_INSTANCE = None

class MetricsCollector:
    """
    Metrics collector for the EPIC FHIR pipeline.
    
    This class provides methods for recording metrics and flushing them to disk.
    It is implemented as a singleton to ensure all metrics are collected in one place.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.metrics = []
        self.lock = Lock()
        self.registered_for_atexit = False
        
    def record(self, 
              step: str, 
              name: str, 
              value: Any, 
              metric_type: str = "RUNTIME", 
              resource_type: Optional[str] = None,
              details: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a metric.
        
        Args:
            step: Pipeline step (e.g., "extract", "transform", "load")
            name: Metric name
            value: Metric value
            metric_type: Type of metric (RUNTIME, SCHEMA, QUALITY, etc.)
            resource_type: FHIR resource type (optional)
            details: Additional details (optional)
        """
        timestamp = datetime.datetime.now()
        
        metric = {
            "step": step,
            "name": name,
            "value": value,
            "metric_type": metric_type,
            "timestamp": timestamp.isoformat(),
            "resource_type": resource_type or "",
            "details": json.dumps(details or {})
        }
        
        with self.lock:
            self.metrics.append(metric)
            
        # Register atexit handler if not already registered
        if not self.registered_for_atexit:
            atexit.register(self._atexit_handler)
            self.registered_for_atexit = True
            
    def record_batch(self,
                    metrics: List[Dict[str, Any]]) -> None:
        """
        Record multiple metrics in a batch for better performance.
        
        Args:
            metrics: List of metric dictionaries, each containing:
                     - step: Pipeline step
                     - name: Metric name
                     - value: Metric value
                     - metric_type: Type of metric (optional, default="RUNTIME")
                     - resource_type: FHIR resource type (optional)
                     - details: Additional details (optional)
        """
        timestamp = datetime.datetime.now()
        
        formatted_metrics = []
        for metric in metrics:
            # Ensure required fields
            if 'step' not in metric or 'name' not in metric or 'value' not in metric:
                logger.warning(f"Skipping invalid metric: {metric}")
                continue
                
            formatted_metric = {
                "step": metric["step"],
                "name": metric["name"],
                "value": metric["value"],
                "metric_type": metric.get("metric_type", "RUNTIME"),
                "timestamp": timestamp.isoformat(),
                "resource_type": metric.get("resource_type", ""),
                "details": json.dumps(metric.get("details", {}))
            }
            formatted_metrics.append(formatted_metric)
        
        # Add all metrics at once with single lock acquisition
        if formatted_metrics:
            with self.lock:
                self.metrics.extend(formatted_metrics)
            
        # Register atexit handler if not already registered
        if not self.registered_for_atexit:
            atexit.register(self._atexit_handler)
            self.registered_for_atexit = True
            
    def _atexit_handler(self) -> None:
        """Handle process exit by flushing metrics."""
        logger.info("Process exiting, flushing metrics")
        try:
            # Get the output directory from environment variable or use current directory
            output_dir = os.environ.get("FHIR_OUTPUT_DIR", ".")
            self.flush(Path(output_dir) / "metrics")
        except Exception as e:
            logger.error(f"Error flushing metrics on exit: {e}")
            
    def flush(self, output_dir: Union[str, Path]) -> Optional[str]:
        """
        Flush metrics to disk.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Path to the metrics file if successful, None otherwise
        """
        if not self.metrics:
            logger.info("No metrics to flush")
            return None
            
        try:
            # Ensure output directory exists
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metrics dataframe
            metrics_df = pd.DataFrame(self.metrics)
            
            # Add metric_version column
            metrics_df["metric_version"] = "1.0"
            
            # Determine output path
            output_path = output_dir / "performance_metrics.parquet"
            
            # Write using appropriate method
            self._write_metrics(metrics_df, output_path)
            
            # Clear metrics
            with self.lock:
                self.metrics = []
                
            logger.info(f"Flushed {len(metrics_df)} metrics to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            return None
            
    def _write_metrics(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Write metrics using the appropriate method (Spark or Pandas).
        
        Args:
            df: Metrics dataframe
            output_path: Output path
        """
        # Check if a Spark session is available
        spark = self._get_spark_session()
        
        if spark and HAS_SPARK:
            # Use Spark to write the metrics
            try:
                logger.debug("Using Spark to write metrics")
                spark_df = spark.createDataFrame(df)
                spark_df.write.mode("append").parquet(str(output_path))
                return
            except Exception as e:
                logger.warning(f"Failed to write metrics using Spark: {e}, falling back to Pandas")
        
        # Fall back to using Pandas
        logger.debug("Using Pandas to write metrics")
        
        # If file exists, read it and append
        if output_path.exists():
            try:
                existing_df = pd.read_parquet(output_path)
                df = pd.concat([existing_df, df], ignore_index=True)
            except Exception as e:
                logger.warning(f"Failed to read existing metrics: {e}, will overwrite")
        
        # Write to parquet
        df.to_parquet(output_path, index=False)
        
    def _get_spark_session(self) -> Optional[Any]:
        """Get the current Spark session if available."""
        if not HAS_SPARK:
            return None
            
        try:
            from pyspark.sql import SparkSession
            return SparkSession.getActiveSession()
        except Exception:
            return None
            
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get all collected metrics."""
        with self.lock:
            return self.metrics.copy()
            
    def clear(self) -> None:
        """Clear all metrics."""
        with self.lock:
            self.metrics = []
            
    def get_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage metrics.
        
        Returns:
            Dictionary of resource usage metrics
        """
        import psutil
        
        process = psutil.Process(os.getpid())
        usage = {
            "memory_percent": process.memory_percent(),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "thread_count": process.num_threads(),
            "open_files": len(process.open_files()),
        }
        
        return usage


def get_collector_instance() -> MetricsCollector:
    """
    Get the singleton metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _COLLECTOR_INSTANCE
    if _COLLECTOR_INSTANCE is None:
        _COLLECTOR_INSTANCE = MetricsCollector()
    return _COLLECTOR_INSTANCE


def record_metric(
    step: str, 
    name: str, 
    value: Any, 
    metric_type: str = "RUNTIME", 
    resource_type: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Record a metric using the singleton collector.
    
    Args:
        step: Pipeline step (e.g., "extract", "transform", "load")
        name: Metric name
        value: Metric value
        metric_type: Type of metric (RUNTIME, SCHEMA, QUALITY, etc.)
        resource_type: FHIR resource type (optional)
        details: Additional details (optional)
    """
    collector = get_collector_instance()
    collector.record(step, name, value, metric_type, resource_type, details)


def record_metrics_batch(metrics: List[Dict[str, Any]]) -> None:
    """
    Record multiple metrics in a batch for better performance.
    
    Args:
        metrics: List of metric dictionaries, each containing:
                 - step: Pipeline step
                 - name: Metric name
                 - value: Metric value
                 - metric_type: Type of metric (optional, default="RUNTIME")
                 - resource_type: FHIR resource type (optional)
                 - details: Additional details (optional)
    """
    collector = get_collector_instance()
    collector.record_batch(metrics)


def flush_metrics(output_dir: Union[str, Path]) -> Optional[str]:
    """
    Flush metrics to disk using the singleton collector.
    
    Args:
        output_dir: Output directory
        
    Returns:
        Path to the metrics file if successful, None otherwise
    """
    collector = get_collector_instance()
    return collector.flush(output_dir)


def track_resource_usage(interval: float = 60.0, output_dir: Optional[Union[str, Path]] = None) -> Callable:
    """
    Start tracking resource usage at regular intervals.
    
    Args:
        interval: Interval between measurements in seconds
        output_dir: Directory to flush metrics to (if None, won't flush automatically)
        
    Returns:
        Function to stop tracking
    """
    import threading
    import time
    
    stop_event = threading.Event()
    
    def _track_usage():
        collector = get_collector_instance()
        
        while not stop_event.is_set():
            try:
                # Get resource usage
                usage = collector.get_resource_usage()
                
                # Record metrics
                metrics_batch = []
                for key, value in usage.items():
                    metrics_batch.append({
                        "step": "system",
                        "name": key,
                        "value": value,
                        "metric_type": "RESOURCE"
                    })
                
                # Use batch recording for efficiency
                if metrics_batch:
                    record_metrics_batch(metrics_batch)
                
                # Flush if output_dir is specified
                if output_dir:
                    flush_metrics(output_dir)
                    
            except Exception as e:
                logger.error(f"Error tracking resource usage: {e}")
                
            # Wait for the next interval or until stopped
            stop_event.wait(interval)
    
    # Start tracking thread
    thread = threading.Thread(target=_track_usage, daemon=True)
    thread.start()
    
    # Return function to stop tracking
    def stop_tracking():
        stop_event.set()
        thread.join(timeout=5.0)
        return not thread.is_alive()
        
    return stop_tracking 