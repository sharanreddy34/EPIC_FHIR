"""
Log Shipper Pipeline

This pipeline reads transformation metrics and monitoring information,
then forwards it to external monitoring systems and alerting channels.
"""
import os
import json
import logging
import datetime
import requests
from typing import Dict, Any, List, Optional, Union

# Foundry imports
try:
    from transforms.api import Input, Output, transform, configure
    IN_FOUNDRY = True
except ImportError:
    IN_FOUNDRY = False

from fhir_pipeline.utils.logging import get_logger
from fhir_pipeline.utils.retry import retry_with_backoff, RetryableError

# Set up logging
logger = get_logger(__name__, level="INFO")

class MetricsShipper:
    """
    Responsible for shipping metrics to external monitoring systems.
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        alert_on_error: bool = True,
        alert_on_data_loss: bool = True,
        data_loss_threshold: float = 5.0,
    ):
        """
        Initialize the metrics shipper.
        
        Args:
            webhook_url: URL for the webhook endpoint (Slack, Teams, etc.)
            alert_on_error: Whether to send alerts for errors
            alert_on_data_loss: Whether to send alerts for data loss
            data_loss_threshold: Threshold percentage for data loss alerts
        """
        self.webhook_url = webhook_url or os.environ.get("ALERT_WEBHOOK_URL")
        self.alert_on_error = alert_on_error
        self.alert_on_data_loss = alert_on_data_loss
        self.data_loss_threshold = data_loss_threshold
    
    def format_summary(self, metrics: List[Dict[str, Any]]) -> str:
        """
        Format metrics into a human-readable summary.
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            Formatted summary text
        """
        if not metrics:
            return "No metrics available."
        
        # Count records by status
        status_counts = {}
        for m in metrics:
            status = m.get("transform_status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate totals
        total_input = sum(m.get("input_record_count", 0) for m in metrics)
        total_output = sum(m.get("output_record_count", 0) for m in metrics)
        total_time = sum(m.get("transform_time_seconds", 0) for m in metrics)
        
        # Format status summary
        status_summary = ", ".join(f"{status}: {count}" for status, count in status_counts.items())
        
        # Calculate overall loss percentage
        if total_input > 0:
            loss_pct = (total_input - total_output) / total_input * 100
        else:
            loss_pct = 0
        
        # Compile the summary
        summary = [
            f"FHIR Transform Summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            f"Resources processed: {len(metrics)} ({status_summary})",
            f"Total records: input={total_input:,}, output={total_output:,}, loss={loss_pct:.2f}%",
            f"Total processing time: {total_time:.2f} seconds"
        ]
        
        # Add error details if present
        errors = [m for m in metrics if m.get("transform_status") == "ERROR"]
        if errors:
            summary.append("\nErrors:")
            for e in errors:
                error_msg = json.loads(e.get("details", "{}")). \
                    get("error", "Unknown error")
                summary.append(f"- {e.get('resource_type')}: {error_msg}")
        
        return "\n".join(summary)
    
    def should_alert(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Determine if an alert should be sent based on metrics.
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            True if an alert should be sent, False otherwise
        """
        if not metrics:
            return False
        
        # Check for errors
        if self.alert_on_error:
            errors = [m for m in metrics if m.get("transform_status") == "ERROR"]
            if errors:
                return True
        
        # Check for data loss exceeding threshold
        if self.alert_on_data_loss:
            for m in metrics:
                loss_str = json.loads(m.get("details", "{}")).get("loss_pct", "0")
                try:
                    loss_pct = float(loss_str)
                    if loss_pct > self.data_loss_threshold:
                        return True
                except (ValueError, TypeError):
                    pass
        
        return False
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def send_slack_notification(self, message: str, is_alert: bool = False) -> bool:
        """
        Send a notification to Slack.
        
        Args:
            message: Message to send
            is_alert: Whether this is an alert notification
            
        Returns:
            True if the message was sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("No webhook URL configured, skipping Slack notification")
            return False
        
        try:
            # Construct the payload
            payload = {
                "text": message,
                "attachments": [
                    {
                        "color": "danger" if is_alert else "good",
                        "fields": [
                            {
                                "title": "Environment",
                                "value": os.environ.get("ENVIRONMENT", "development"),
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": "ALERT" if is_alert else "INFO",
                                "short": True
                            }
                        ],
                        "footer": "FHIR Pipeline Monitor",
                        "ts": int(datetime.datetime.now().timestamp())
                    }
                ]
            }
            
            # Send the notification
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                raise RetryableError(f"Failed to send Slack notification: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            raise RetryableError(f"Failed to send Slack notification: {str(e)}")
    
    def send_metrics_to_monitoring(
        self, 
        metrics: List[Dict[str, Any]],
        system: str = "prometheus"
    ) -> bool:
        """
        Send metrics to a monitoring system like Prometheus.
        
        Args:
            metrics: List of metric dictionaries
            system: Monitoring system to send to
            
        Returns:
            True if metrics were sent successfully, False otherwise
        """
        if system != "prometheus":
            logger.warning(f"Monitoring system {system} not supported")
            return False
        
        # This would typically push metrics to a Prometheus pushgateway
        # For now, just log that we would send metrics
        logger.info(f"Would send {len(metrics)} metrics to {system}")
        
        # In a real implementation, you would send the metrics to the monitoring system
        # For example:
        # from prometheus_client import push_to_gateway, Counter, Gauge, Summary
        # try:
        #     for m in metrics:
        #         # Set up metrics
        #         g = Gauge(f'fhir_records_processed', 'Records processed', ['resource_type', 'status'])
        #         g.labels(resource_type=m.get('resource_type'), status=m.get('transform_status')).set(m.get('output_record_count', 0))
        #     push_to_gateway('localhost:9091', job='fhir_pipeline', registry=registry)
        #     return True
        # except Exception as e:
        #     logger.error(f"Error sending metrics to {system}: {str(e)}")
        #     return False
        
        return True
    
    def process_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process metrics and send notifications/alerts as needed.
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            Dictionary with processing results
        """
        result = {
            "success": True,
            "error": None,
            "notifications_sent": 0,
            "alerts_sent": 0
        }
        
        try:
            # Format the summary
            summary = self.format_summary(metrics)
            
            # Determine if we should alert
            is_alert = self.should_alert(metrics)
            
            # Send to Slack
            if self.webhook_url:
                if self.send_slack_notification(summary, is_alert):
                    if is_alert:
                        result["alerts_sent"] += 1
                    else:
                        result["notifications_sent"] += 1
            
            # Send to monitoring systems
            self.send_metrics_to_monitoring(metrics)
            
        except Exception as e:
            logger.error(f"Error processing metrics: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
        
        return result


# Foundry Transform
if IN_FOUNDRY:
    @configure(profile=["MONITORING"])
    @transform(
        transform_metrics=Input("/metrics/transform_metrics"),
        shipping_output=Output("/metrics/log_shipping_results")
    )
    def ship_logs_and_metrics(
        spark,
        transform_metrics: Input,
        shipping_output: Output
    ) -> None:
        """
        Ship logs and metrics to monitoring and alerting systems.
        
        Args:
            spark: SparkSession
            transform_metrics: Input metrics dataset
            shipping_output: Output for shipping results
        """
        # Get metrics data
        metrics_df = transform_metrics.dataframe()
        
        # Convert to list of dictionaries
        metrics = [row.asDict() for row in metrics_df.collect()]
        
        # Initialize the metrics shipper
        shipper = MetricsShipper(
            webhook_url=os.environ.get("ALERT_WEBHOOK_URL"),
            alert_on_error=True,
            alert_on_data_loss=True,
            data_loss_threshold=float(os.environ.get("DATA_LOSS_THRESHOLD", "5.0"))
        )
        
        # Process metrics
        result = shipper.process_metrics(metrics)
        
        # Create result DataFrame
        result_df = spark.createDataFrame([{
            "timestamp": datetime.datetime.now().isoformat(),
            "success": result["success"],
            "error": result["error"],
            "notifications_sent": result["notifications_sent"],
            "alerts_sent": result["alerts_sent"],
            "metrics_count": len(metrics)
        }])
        
        # Write result
        shipping_output.write_dataframe(result_df)


# Command-line interface for local usage
def main():
    """Run the log shipper as a command-line tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Log and metrics shipper")
    parser.add_argument("--metrics-file", required=True, help="JSON file with metrics data")
    parser.add_argument("--webhook-url", help="Webhook URL for notifications")
    parser.add_argument("--alert-threshold", type=float, default=5.0, help="Data loss threshold")
    args = parser.parse_args()
    
    # Read metrics from file
    with open(args.metrics_file, 'r') as f:
        metrics = json.load(f)
    
    # Initialize the metrics shipper
    shipper = MetricsShipper(
        webhook_url=args.webhook_url or os.environ.get("ALERT_WEBHOOK_URL"),
        data_loss_threshold=args.alert_threshold
    )
    
    # Process metrics
    result = shipper.process_metrics(metrics)
    
    # Print result
    print(f"Log shipping result: {'SUCCESS' if result['success'] else 'FAILURE'}")
    print(f"Notifications sent: {result['notifications_sent']}")
    print(f"Alerts sent: {result['alerts_sent']}")
    if result["error"]:
        print(f"Error: {result['error']}")
    
    # Exit with appropriate status code
    import sys
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main() 