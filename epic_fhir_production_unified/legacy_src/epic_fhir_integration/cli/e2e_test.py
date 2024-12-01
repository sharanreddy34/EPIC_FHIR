#!/usr/bin/env python
"""
Epic FHIR End-to-End Test CLI.

This module provides a command-line interface for running end-to-end tests
of the FHIR pipeline.
"""

import argparse
import logging
import sys
import os
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_test.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Run FHIR pipeline end-to-end tests")
    parser.add_argument(
        "--test-dir",
        help="Directory for test output",
        default="e2e_test_output",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of calling the API",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test directory after tests",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )
    
    return parser.parse_args()


def setup_test_env(test_dir: str) -> Path:
    """Set up the test environment.
    
    Args:
        test_dir: Directory for test output.
        
    Returns:
        Path to the test directory.
    """
    test_dir_path = Path(test_dir).resolve()
    
    # Create test directory if it doesn't exist
    test_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for each layer
    (test_dir_path / "bronze").mkdir(exist_ok=True)
    (test_dir_path / "silver").mkdir(exist_ok=True)
    (test_dir_path / "gold").mkdir(exist_ok=True)
    
    logger.info(f"Set up test environment in {test_dir_path}")
    return test_dir_path


def cleanup_test_env(test_dir: Path) -> None:
    """Clean up the test environment.
    
    Args:
        test_dir: Path to the test directory.
    """
    if test_dir.exists():
        shutil.rmtree(test_dir)
        logger.info(f"Cleaned up test directory: {test_dir}")


def run_tests(args: argparse.Namespace) -> bool:
    """Run the end-to-end tests.
    
    Args:
        args: Command-line arguments.
        
    Returns:
        True if all tests passed, False otherwise.
    """
    # Set up test environment
    test_dir = setup_test_env(args.test_dir)
    
    try:
        # Set environment variables for the tests
        os.environ["EPIC_FHIR_TEST_DIR"] = str(test_dir)
        os.environ["EPIC_FHIR_MOCK"] = "1" if args.mock else "0"
        
        # Build pytest arguments
        pytest_args = [
            "-m", "e2e",            # Run e2e tests only
            "--verbose" * args.verbose,  # Set verbosity
            "--log-cli-level=INFO",  # Show logs in console output
        ]
        
        # Run the tests
        logger.info("Running end-to-end tests...")
        result = pytest.main(pytest_args)
        
        if result == 0:
            logger.info("All end-to-end tests passed")
            return True
        else:
            logger.error("Some end-to-end tests failed")
            return False
        
    finally:
        # Clean up if requested
        if args.cleanup:
            cleanup_test_env(test_dir)


def main() -> None:
    """Main entry point for the end-to-end test CLI."""
    try:
        args = parse_args()
        success = run_tests(args)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Error running end-to-end tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 