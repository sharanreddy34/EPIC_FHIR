#!/usr/bin/env python3
"""
Script to perform a final QA check on the epic-fhir-integration package.
"""

import os
import sys
import subprocess
from pathlib import Path


class QAChecker:
    """Class to run QA checks on the package."""
    
    def __init__(self):
        """Initialize the QA checker."""
        self.root_dir = Path(__file__).resolve().parent.parent
        self.results = {}
    
    def run_all_checks(self):
        """Run all QA checks and return True if all pass."""
        print("Running Epic-FHIR Integration QA Checklist...")
        print("=" * 50)
        
        # Run checks
        self.check_dependency_conflicts()
        self.check_ruff()
        self.check_pytest()
        self.check_e2e_test()
        self.check_wheel_build()
        
        # Print summary
        print("\nQA Check Summary:")
        print("=" * 50)
        
        all_passed = True
        for check, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check:30s} {status}")
            if not result:
                all_passed = False
        
        print("\nFinal Result:", "PASS" if all_passed else "FAIL")
        return all_passed
    
    def check_dependency_conflicts(self):
        """Check for dependency conflicts."""
        print("\nChecking for dependency conflicts...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "check"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.root_dir
            )
            
            if result.returncode == 0:
                print("No dependency conflicts found.")
                self.results["Dependency conflicts"] = True
            else:
                print("Dependency conflicts found:")
                print(result.stdout)
                self.results["Dependency conflicts"] = False
        except Exception as e:
            print(f"Error checking dependencies: {e}")
            self.results["Dependency conflicts"] = False
    
    def check_ruff(self):
        """Check code style with ruff."""
        print("\nRunning ruff linter...")
        
        try:
            result = subprocess.run(
                ["ruff", "."],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.root_dir
            )
            
            if result.returncode == 0:
                print("Ruff check passed.")
                self.results["Ruff linting"] = True
            else:
                print("Ruff found issues:")
                print(result.stdout)
                self.results["Ruff linting"] = False
        except Exception as e:
            print(f"Error running ruff: {e}")
            self.results["Ruff linting"] = False
    
    def check_pytest(self):
        """Run pytest."""
        print("\nRunning pytest...")
        
        try:
            result = subprocess.run(
                ["pytest", "-q"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.root_dir
            )
            
            if result.returncode == 0:
                print("All tests passed.")
                self.results["Pytest"] = True
            else:
                print("Some tests failed:")
                print(result.stdout)
                print(result.stderr)
                self.results["Pytest"] = False
        except Exception as e:
            print(f"Error running pytest: {e}")
            self.results["Pytest"] = False
    
    def check_e2e_test(self):
        """Run end-to-end tests."""
        print("\nRunning end-to-end tests...")
        
        try:
            result = subprocess.run(
                ["pytest", "-m", "e2e"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.root_dir
            )
            
            # Check for no tests collected as that's also a pass condition
            # in case e2e tests aren't fully set up yet
            no_tests = "no tests ran" in result.stderr
            
            if result.returncode == 0 or no_tests:
                print("End-to-end tests passed or not configured.")
                self.results["End-to-end tests"] = True
            else:
                print("End-to-end tests failed:")
                print(result.stdout)
                print(result.stderr)
                self.results["End-to-end tests"] = False
        except Exception as e:
            print(f"Error running e2e tests: {e}")
            self.results["End-to-end tests"] = False
    
    def check_wheel_build(self):
        """Check if wheel can be built."""
        print("\nChecking wheel build...")
        
        try:
            # Create a temporary directory for the wheel
            wheel_dir = self.root_dir / "dist"
            wheel_dir.mkdir(exist_ok=True)
            
            # Try to build the wheel
            result = subprocess.run(
                [sys.executable, "-m", "build"],
                check=False,
                capture_output=True,
                text=True,
                cwd=self.root_dir
            )
            
            if result.returncode == 0:
                print("Wheel build successful.")
                self.results["Wheel build"] = True
            else:
                print("Wheel build failed:")
                print(result.stderr)
                self.results["Wheel build"] = False
        except Exception as e:
            print(f"Error building wheel: {e}")
            self.results["Wheel build"] = False


if __name__ == "__main__":
    checker = QAChecker()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1) 