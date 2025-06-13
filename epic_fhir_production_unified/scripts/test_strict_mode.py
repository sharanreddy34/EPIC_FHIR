#!/usr/bin/env python3
"""
Test script to verify that strict mode is working correctly.

This script will:
1. Test that mock functions fail when strict mode is enabled
2. Test that they work when strict mode is disabled
3. Test that environment variables properly control strict mode

Usage:
    python test_strict_mode.py
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from fhir_pipeline.utils.strict_mode import (
    enable_strict_mode,
    get_strict_mode,
    strict_mode_check,
    no_mocks
)

def test_basic_strict_mode():
    """Test basic strict mode functionality."""
    logger.info("===== Testing basic strict mode functionality =====")
    
    # Test with strict mode disabled
    enable_strict_mode(False)
    assert get_strict_mode() == False, "Strict mode should be disabled"
    logger.info("Strict mode is disabled as expected")
    
    # This should not raise an exception
    try:
        strict_mode_check("test mock data")
        logger.info("No exception raised when strict mode is disabled - correct")
    except RuntimeError:
        logger.error("Exception raised when strict mode is disabled - INCORRECT")
        return False
    
    # Enable strict mode
    enable_strict_mode(True)
    assert get_strict_mode() == True, "Strict mode should be enabled"
    logger.info("Strict mode is enabled as expected")
    
    # This should raise an exception
    try:
        strict_mode_check("test mock data")
        logger.error("No exception raised when strict mode is enabled - INCORRECT")
        return False
    except RuntimeError as e:
        logger.info(f"Exception raised when strict mode is enabled - correct: {str(e)}")
    
    return True

def test_decorator():
    """Test the @no_mocks decorator."""
    logger.info("===== Testing @no_mocks decorator =====")
    
    # Define a test function with the decorator
    @no_mocks("test_function")
    def test_function(mock_mode=False):
        return "Function executed"
    
    # Test with strict mode disabled
    enable_strict_mode(False)
    try:
        result = test_function(mock_mode=True)
        logger.info(f"Function executed with mock_mode=True and strict mode disabled: {result}")
    except RuntimeError:
        logger.error("Exception raised when strict mode is disabled - INCORRECT")
        return False
    
    # Enable strict mode
    enable_strict_mode(True)
    try:
        result = test_function(mock_mode=True)
        logger.error("No exception raised when strict mode is enabled and mock_mode=True - INCORRECT")
        return False
    except RuntimeError as e:
        logger.info(f"Exception raised when strict mode is enabled - correct: {str(e)}")
    
    # Should work with mock_mode=False even in strict mode
    try:
        result = test_function(mock_mode=False)
        logger.info(f"Function executed with mock_mode=False and strict mode enabled: {result}")
    except RuntimeError:
        logger.error("Exception raised with mock_mode=False - INCORRECT")
        return False
    
    return True

def test_environment_variable():
    """Test that environment variables control strict mode."""
    logger.info("===== Testing environment variable control =====")
    
    # First clear any existing environment variable
    if "FHIR_STRICT_MODE" in os.environ:
        del os.environ["FHIR_STRICT_MODE"]
    
    # Reset global state
    enable_strict_mode(False)
    
    # Set environment variable to enable strict mode
    os.environ["FHIR_STRICT_MODE"] = "true"
    
    # Should detect strict mode from environment
    strict_from_env = get_strict_mode()
    if strict_from_env:
        logger.info("Correctly detected strict mode from environment variable")
    else:
        logger.error("Failed to detect strict mode from environment variable")
        return False
    
    # Test that strict mode works with environment variable
    try:
        strict_mode_check("test mock data")
        logger.error("No exception raised when strict mode is enabled via environment - INCORRECT")
        return False
    except RuntimeError as e:
        logger.info(f"Exception raised correctly: {str(e)}")
    
    # Remove environment variable and verify it's detected
    del os.environ["FHIR_STRICT_MODE"]
    enable_strict_mode(False)  # Reset global state
    
    strict_from_env = get_strict_mode()
    if not strict_from_env:
        logger.info("Correctly detected strict mode is disabled after removing environment variable")
    else:
        logger.error("Failed to detect strict mode is disabled after removing environment variable")
        return False
    
    return True

def main():
    """Run all tests."""
    logger.info("Starting strict mode tests")
    
    tests = [
        test_basic_strict_mode,
        test_decorator,
        test_environment_variable
    ]
    
    results = []
    for test_func in tests:
        logger.info(f"\nRunning test: {test_func.__name__}")
        try:
            result = test_func()
            results.append(result)
            logger.info(f"Test {test_func.__name__}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"Test {test_func.__name__} threw an exception: {str(e)}")
            results.append(False)
    
    # Report results
    passed = sum(1 for r in results if r)
    total = len(results)
    logger.info(f"\n===== TEST RESULTS =====")
    logger.info(f"Tests passed: {passed}/{total} ({(passed/total*100):.1f}%)")
    
    # Reset state for safety
    enable_strict_mode(False)
    if "FHIR_STRICT_MODE" in os.environ:
        del os.environ["FHIR_STRICT_MODE"]
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main()) 