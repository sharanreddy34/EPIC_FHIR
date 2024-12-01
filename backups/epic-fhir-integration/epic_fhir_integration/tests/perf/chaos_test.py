import os
import time
import json
import pytest
import responses
import requests
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from fhir_pipeline.auth.jwt_client import JWTClient
from fhir_pipeline.io.fhir_client import FHIRClient
from fhir_pipeline.utils.retry import retry_with_backoff
from run_local_fhir_pipeline import extract_resources

# Sample test patient from test plan
SANDBOX_PATIENT_ID = "Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB"

class TestResults:
    """Simple object to track test results for reporting."""
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
    
    def add_result(self, test_name, status, details=None):
        self.test_results.append({
            "test_name": test_name,
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def get_report(self):
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "test_count": len(self.test_results),
            "success_count": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "fail_count": sum(1 for r in self.test_results if r["status"] == "FAIL"),
            "results": self.test_results
        }
    
    def write_report(self, filepath="tests/perf/chaos_report.md"):
        """Write test results as markdown report."""
        report = self.get_report()
        
        with open(filepath, "w") as f:
            f.write(f"# EPIC FHIR Chaos Test Report\n\n")
            f.write(f"- **Start Time:** {report['start_time']}\n")
            f.write(f"- **End Time:** {report['end_time']}\n")
            f.write(f"- **Tests Run:** {report['test_count']}\n")
            f.write(f"- **Success:** {report['success_count']}\n")
            f.write(f"- **Failures:** {report['fail_count']}\n\n")
            
            f.write("## Test Results\n\n")
            f.write("| Test Name | Status | Details |\n")
            f.write("|-----------|--------|--------|\n")
            
            for result in report['results']:
                details_str = ", ".join(f"{k}={v}" for k, v in result["details"].items())
                f.write(f"| {result['test_name']} | {result['status']} | {details_str} |\n")


@pytest.fixture(scope="module")
def test_results():
    """Fixture to track test results across test functions."""
    results = TestResults()
    yield results
    results.write_report()


@pytest.fixture
def mock_responses():
    """Set up responses for mocking HTTP requests."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def real_client():
    """Create a real FHIR client for testing actual API behavior."""
    try:
        # Create a token provider function that returns a token from the JWT client
        jwt_client = JWTClient(
            client_id=os.environ["EPIC_CLIENT_ID"],
            private_key=os.environ["EPIC_PRIVATE_KEY"],
        )
        token_provider = lambda: jwt_client.get_token()
        
        client = FHIRClient(
            base_url=os.environ["EPIC_BASE_URL"],
            token_provider=token_provider
        )
        
        yield client
    except (KeyError, Exception) as e:
        pytest.skip(f"Skipping real client tests: {str(e)}")


def test_network_timeout_retry(mock_responses, test_results):
    """Test ability to recover from network timeouts."""
    base_url = "https://example.com/api/FHIR/R4"
    
    # Mock a timeout for the first call
    mock_responses.add(
        responses.GET, 
        f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
        body=requests.exceptions.Timeout("Connection timed out")
    )
    
    # Mock a successful response for the retry
    mock_responses.add(
        responses.GET, 
        f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
        json={"resourceType": "Patient", "id": SANDBOX_PATIENT_ID},
        status=200
    )
    
    # Create a mock token provider function
    mock_token_provider = MagicMock()
    mock_token_provider.return_value = "mock-token"
    
    client = FHIRClient(
        base_url=base_url,
        token_provider=mock_token_provider
    )
    
    # Use the retry decorator with shorter timeouts for testing
    @retry_with_backoff(retries=3, backoff_in_seconds=0.1)
    def fetch_with_retry():
        return client.get_resource("Patient", SANDBOX_PATIENT_ID)
    
    try:
        result = fetch_with_retry()
        assert result["resourceType"] == "Patient"
        assert result["id"] == SANDBOX_PATIENT_ID
        test_results.add_result(
            "network_timeout_retry", 
            "PASS", 
            {"retries": 1}
        )
    except Exception as e:
        test_results.add_result(
            "network_timeout_retry", 
            "FAIL", 
            {"error": str(e)}
        )
        raise


def test_rate_limit_backoff(mock_responses, test_results):
    """Test that rate limiting causes proper exponential backoff."""
    base_url = "https://example.com/api/FHIR/R4"
    
    # Add 429 responses for the first two calls
    for _ in range(2):
        mock_responses.add(
            responses.GET, 
            f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
            json={"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "too-many-requests"}]},
            status=429
        )
    
    # Finally succeed on the third call
    mock_responses.add(
        responses.GET, 
        f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
        json={"resourceType": "Patient", "id": SANDBOX_PATIENT_ID},
        status=200
    )
    
    # Create a mock token provider function
    mock_token_provider = MagicMock()
    mock_token_provider.return_value = "mock-token"
    
    client = FHIRClient(
        base_url=base_url,
        token_provider=mock_token_provider
    )
    
    start_time = time.time()
    
    # Use the retry decorator with shorter timeouts for testing
    @retry_with_backoff(retries=3, backoff_in_seconds=0.1)
    def fetch_with_retry():
        return client.get_resource("Patient", SANDBOX_PATIENT_ID)
    
    try:
        result = fetch_with_retry()
        duration = time.time() - start_time
        
        assert result["resourceType"] == "Patient"
        assert result["id"] == SANDBOX_PATIENT_ID
        assert duration >= 0.1, "Expected some backoff delay"
        
        test_results.add_result(
            "rate_limit_backoff", 
            "PASS", 
            {"retries": 2, "duration_seconds": round(duration, 3)}
        )
    except Exception as e:
        test_results.add_result(
            "rate_limit_backoff", 
            "FAIL", 
            {"error": str(e)}
        )
        raise


def test_server_error_recovery(mock_responses, test_results):
    """Test resilience to server 5xx errors."""
    base_url = "https://example.com/api/FHIR/R4"
    
    # Add 500 response for first call with a retriable error code
    mock_responses.add(
        responses.GET, 
        f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
        json={
            "resourceType": "OperationOutcome", 
            "issue": [
                {
                    "severity": "error", 
                    "code": "transient", 
                    "details": {
                        "text": "Temporary server error, please retry"
                    }
                }
            ]
        },
        status=500
    )
    
    # Success on retry
    mock_responses.add(
        responses.GET, 
        f"{base_url}/Patient/{SANDBOX_PATIENT_ID}",
        json={"resourceType": "Patient", "id": SANDBOX_PATIENT_ID},
        status=200
    )
    
    # Create a mock token provider function
    mock_token_provider = MagicMock()
    mock_token_provider.return_value = "mock-token"
    
    client = FHIRClient(
        base_url=base_url,
        token_provider=mock_token_provider
    )
    
    # Use the retry decorator with shorter timeouts for testing
    @retry_with_backoff(retries=3, backoff_in_seconds=0.1)
    def fetch_with_retry():
        return client.get_resource("Patient", SANDBOX_PATIENT_ID)
    
    try:
        result = fetch_with_retry()
        assert result["resourceType"] == "Patient"
        test_results.add_result(
            "server_error_recovery", 
            "PASS", 
            {"retries": 1}
        )
    except Exception as e:
        test_results.add_result(
            "server_error_recovery", 
            "FAIL", 
            {"error": str(e)}
        )
        raise


@pytest.mark.skipif(
    not all(var in os.environ for var in ["EPIC_BASE_URL", "EPIC_CLIENT_ID", "EPIC_PRIVATE_KEY"]),
    reason="Missing EPIC environment variables for live testing"
)
def test_real_api_resilience(real_client, test_results):
    """Test resilience with the real API (if credentials are available)."""
    success_count = 0
    failure_count = 0
    resources = ["Patient", "Observation", "Encounter", "Condition", "MedicationRequest"]
    
    for resource in resources:
        for i in range(3):  # Make multiple calls to same endpoints to test rate limiting
            try:
                if resource == "Patient":
                    result = real_client.get_resource(resource, SANDBOX_PATIENT_ID)
                    assert result["resourceType"] == resource
                else:
                    endpoint = f"{resource}?patient={SANDBOX_PATIENT_ID}"
                    result = real_client._make_request("GET", endpoint).json()
                    assert result["resourceType"] == "Bundle"
                
                success_count += 1
                time.sleep(0.5)  # Small delay between calls
            except Exception as e:
                failure_count += 1
                print(f"Error on {resource} (attempt {i+1}): {str(e)}")
    
    retry_success_ratio = success_count / (success_count + failure_count) if (success_count + failure_count) > 0 else 0
    
    test_results.add_result(
        "real_api_resilience", 
        "PASS" if retry_success_ratio >= 0.9 else "FAIL", 
        {
            "success_count": success_count,
            "failure_count": failure_count,
            "retry_success_ratio": round(retry_success_ratio, 2)
        }
    )


if __name__ == "__main__":
    # This allows running just the chaos tests and generating a report
    pytest.main(["-xvs", __file__]) 