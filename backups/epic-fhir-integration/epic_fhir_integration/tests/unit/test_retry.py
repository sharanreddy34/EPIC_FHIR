#!/usr/bin/env python3
"""
Unit Tests for Retry Utilities

This module contains tests for the retry utilities, including
retry decorators and backoff functions.
"""

import time
import unittest
from unittest import mock

from epic_fhir_integration.utils.retry import (
    exponential_backoff,
    retry_on_exceptions,
    retry_with_timeout,
    is_transient_error,
    retry_api_call
)


class TestBackoffFunctions(unittest.TestCase):
    """Test cases for backoff functions."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        # Test with default parameters
        self.assertAlmostEqual(exponential_backoff(0), 1.0, delta=0.2)
        self.assertAlmostEqual(exponential_backoff(1), 2.0, delta=0.4)
        self.assertAlmostEqual(exponential_backoff(2), 4.0, delta=0.8)
        
        # Test with custom parameters
        self.assertAlmostEqual(exponential_backoff(0, base_delay=0.5), 0.5, delta=0.1)
        self.assertAlmostEqual(exponential_backoff(1, base_delay=0.5, backoff_factor=3), 1.5, delta=0.3)
        
        # Test with max_delay
        self.assertLessEqual(exponential_backoff(10, max_delay=10), 10)
        
        # Test with no jitter
        self.assertEqual(exponential_backoff(1, base_delay=1, backoff_factor=2, jitter=0), 2)


class TestRetryDecorators(unittest.TestCase):
    """Test cases for retry decorators."""
    
    def test_retry_on_exceptions_success(self):
        """Test retry_on_exceptions when function succeeds."""
        mock_func = mock.Mock(return_value="success")
        
        # Decorate the mock function
        decorated_func = retry_on_exceptions(max_retries=3)(mock_func)
        
        # Call the decorated function
        result = decorated_func()
        
        # Function should be called once and return success
        self.assertEqual(mock_func.call_count, 1)
        self.assertEqual(result, "success")
    
    def test_retry_on_exceptions_retry_and_succeed(self):
        """Test retry_on_exceptions when function fails and then succeeds."""
        # Mock function that fails twice then succeeds
        side_effects = [ValueError("Attempt 1"), ValueError("Attempt 2"), "success"]
        mock_func = mock.Mock(side_effect=side_effects)
        
        # Decorate the mock function with fast retry
        @retry_on_exceptions(max_retries=3, backoff_func=lambda _: 0.01)
        def test_func():
            return mock_func()
        
        # Call the decorated function
        result = test_func()
        
        # Function should be called three times and return success
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(result, "success")
    
    def test_retry_on_exceptions_max_retries(self):
        """Test retry_on_exceptions when max retries is reached."""
        # Mock function that always fails
        mock_func = mock.Mock(side_effect=ValueError("Always fails"))
        
        # Decorate the mock function with fast retry
        @retry_on_exceptions(max_retries=2, backoff_func=lambda _: 0.01)
        def test_func():
            return mock_func()
        
        # Call the decorated function and expect exception
        with self.assertRaises(ValueError):
            test_func()
        
        # Function should be called three times (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)
    
    def test_retry_on_exceptions_with_specific_exceptions(self):
        """Test retry_on_exceptions with specific exception types."""
        # Mock function that raises different exceptions
        side_effects = [ValueError("Retry this"), TypeError("Don't retry this")]
        mock_func = mock.Mock(side_effect=side_effects)
        
        # Decorate the mock function to only retry on ValueError
        @retry_on_exceptions(max_retries=3, exceptions=ValueError, backoff_func=lambda _: 0.01)
        def test_func():
            return mock_func()
        
        # Call the decorated function and expect TypeError
        with self.assertRaises(TypeError):
            test_func()
        
        # Function should be called twice (ValueError is retried, TypeError is not)
        self.assertEqual(mock_func.call_count, 2)
    
    def test_retry_on_exceptions_with_should_retry_func(self):
        """Test retry_on_exceptions with should_retry_func."""
        # Mock function that raises different value errors
        side_effects = [
            ValueError("Error 1"),  # Should retry
            ValueError("Error 2"),  # Should not retry
            ValueError("Error 3")   # Should not be reached
        ]
        mock_func = mock.Mock(side_effect=side_effects)
        
        # Only retry if error message contains "1"
        def should_retry(e):
            return "1" in str(e)
        
        # Decorate the mock function
        @retry_on_exceptions(
            max_retries=3, 
            exceptions=ValueError, 
            should_retry_func=should_retry,
            backoff_func=lambda _: 0.01
        )
        def test_func():
            return mock_func()
        
        # Call the decorated function and expect ValueError with "Error 2"
        with self.assertRaises(ValueError) as cm:
            test_func()
        
        self.assertEqual(str(cm.exception), "Error 2")
        
        # Function should be called twice (Error 1 is retried, Error 2 is not)
        self.assertEqual(mock_func.call_count, 2)
    
    def test_retry_on_exceptions_with_on_retry_callback(self):
        """Test retry_on_exceptions with on_retry callback."""
        # Mock function that fails twice then succeeds
        side_effects = [ValueError("Attempt 1"), ValueError("Attempt 2"), "success"]
        mock_func = mock.Mock(side_effect=side_effects)
        
        # Mock callback
        on_retry_mock = mock.Mock()
        
        # Decorate the mock function
        @retry_on_exceptions(
            max_retries=3, 
            exceptions=ValueError, 
            backoff_func=lambda _: 0.01,
            on_retry=on_retry_mock
        )
        def test_func():
            return mock_func()
        
        # Call the decorated function
        result = test_func()
        
        # Function should be called three times and return success
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(result, "success")
        
        # Callback should be called twice (once per retry)
        self.assertEqual(on_retry_mock.call_count, 2)
    
    def test_retry_with_timeout(self):
        """Test retry_with_timeout decorator."""
        # Mock function that fails repeatedly
        mock_func = mock.Mock(side_effect=ValueError("Always fails"))
        
        # Mock time.time to control elapsed time
        with mock.patch('time.time') as mock_time, \
             mock.patch('time.sleep') as mock_sleep:
            
            # Simulate time progression
            mock_time.side_effect = [0, 0.5, 1.0, 10.0]  # Start, after attempt 1, after attempt 2, would exceed timeout
            
            # Decorate the mock function
            @retry_with_timeout(max_retries=5, timeout=5.0, backoff_func=lambda _: 1.0)
            def test_func():
                return mock_func()
            
            # Call the decorated function and expect exception
            with self.assertRaises(ValueError):
                test_func()
            
            # Function should be called twice (initial + 1 retry)
            # The third attempt would exceed timeout and is not made
            self.assertEqual(mock_func.call_count, 2)


class TestTransientErrorDetection(unittest.TestCase):
    """Test cases for transient error detection."""
    
    def test_is_transient_error_requests(self):
        """Test is_transient_error with requests exceptions."""
        import requests
        
        # Transient network errors
        self.assertTrue(is_transient_error(requests.exceptions.ConnectionError()))
        self.assertTrue(is_transient_error(requests.exceptions.Timeout()))
        
        # Create an HTTPError with a mock response
        response = mock.Mock()
        response.status_code = 500
        http_error = requests.exceptions.HTTPError(response=response)
        self.assertTrue(is_transient_error(http_error))
        
        # Non-transient HTTP error
        response.status_code = 400
        http_error = requests.exceptions.HTTPError(response=response)
        self.assertFalse(is_transient_error(http_error))
    
    def test_is_transient_error_generic(self):
        """Test is_transient_error with generic errors."""
        # Errors with transient indicators in message
        self.assertTrue(is_transient_error(Exception("Connection timeout")))
        self.assertTrue(is_transient_error(Exception("Temporarily unavailable")))
        self.assertTrue(is_transient_error(Exception("Rate limit exceeded")))
        
        # Non-transient errors
        self.assertFalse(is_transient_error(Exception("Invalid parameter")))
        self.assertFalse(is_transient_error(Exception("Not found")))
        self.assertFalse(is_transient_error(ValueError("Bad value")))


class TestRetryApiCall(unittest.TestCase):
    """Test cases for retry_api_call utility function."""
    
    def test_retry_api_call_success(self):
        """Test retry_api_call when API call succeeds."""
        # Mock API function that succeeds
        mock_api_func = mock.Mock(return_value={"status": "success"})
        
        # Call API with retry
        result = retry_api_call(mock_api_func, "arg1", "arg2", kwarg1="value1")
        
        # API should be called once and return success
        mock_api_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        self.assertEqual(result, {"status": "success"})
    
    def test_retry_api_call_with_retry(self):
        """Test retry_api_call when API fails and then succeeds."""
        # Mock API function that fails then succeeds
        side_effects = [
            requests.exceptions.ConnectionError("Network error"),
            {"status": "success"}
        ]
        mock_api_func = mock.Mock(side_effect=side_effects)
        
        # Patch sleep to avoid waiting
        with mock.patch('time.sleep'):
            # Call API with retry
            result = retry_api_call(mock_api_func, max_retries=2)
            
            # API should be called twice and return success
            self.assertEqual(mock_api_func.call_count, 2)
            self.assertEqual(result, {"status": "success"})


if __name__ == "__main__":
    # Import requests here to avoid issues if it's not installed
    import requests
    unittest.main() 