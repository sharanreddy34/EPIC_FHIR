"""
Test that all modules can be imported without errors.

This is a simple test that tries to import all modules in the epic_fhir_integration
package to catch import errors, missing dependencies, etc.
"""

import os
import importlib
import pytest
from pathlib import Path


def get_all_python_modules(package_dir, base_package):
    """Get all Python modules in a package directory.
    
    Args:
        package_dir: Path to the package directory
        base_package: Base package name
        
    Returns:
        List of module names (dot-separated)
    """
    modules = []
    
    for root, dirs, files in os.walk(package_dir):
        # Skip __pycache__ and _stubs directories
        if "__pycache__" in root or "_stubs" in root:
            continue
            
        # Calculate the package path
        rel_path = os.path.relpath(root, os.path.dirname(package_dir))
        if rel_path == ".":
            package_path = base_package
        else:
            package_path = f"{base_package}.{rel_path.replace(os.sep, '.')}"
            
        # Add __init__.py modules
        if "__init__.py" in files:
            modules.append(package_path)
            
        # Add other Python modules
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                module_name = f"{package_path}.{file[:-3]}"
                modules.append(module_name)
                
    return modules


def test_import_all_modules():
    """Test that all modules can be imported without errors."""
    # Path to the epic_fhir_integration package
    package_dir = Path(__file__).parent.parent / "transforms-python" / "src" / "epic_fhir_integration"
    
    # Get all modules
    modules = get_all_python_modules(package_dir, "epic_fhir_integration")
    
    # Try to import each module
    import_errors = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            import_errors.append((module_name, str(e)))
            
    # Report errors
    if import_errors:
        error_messages = "\n".join([f"{module}: {error}" for module, error in import_errors])
        pytest.fail(f"Failed to import {len(import_errors)} modules:\n{error_messages}")
        
    # Success
    print(f"Successfully imported {len(modules)} modules") 