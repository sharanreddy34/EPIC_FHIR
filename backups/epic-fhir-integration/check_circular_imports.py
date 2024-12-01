#!/usr/bin/env python3
"""
Script to detect circular imports in the fhir_pipeline package.
"""

import sys
import importlib
import inspect
import os
from typing import Set, List, Dict, Any

def check_module(module_name: str, visited: Set[str] = None, stack: List[str] = None) -> bool:
    """
    Check if a module has circular imports.
    
    Args:
        module_name: Name of the module to check
        visited: Set of already visited modules
        stack: Current import stack
        
    Returns:
        True if circular imports were found, False otherwise
    """
    if visited is None:
        visited = set()
    if stack is None:
        stack = []
    
    if module_name in stack:
        print(f"Circular import detected: {' -> '.join(stack)} -> {module_name}")
        return True
    
    if module_name in visited:
        return False
    
    visited.add(module_name)
    stack.append(module_name)
    
    try:
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module):
            if inspect.ismodule(obj):
                sub_module_name = obj.__name__
                if sub_module_name.startswith('fhir_pipeline'):
                    check_module(sub_module_name, visited, stack.copy())
    except ImportError as e:
        print(f"Import error with {module_name}: {e}")
    except Exception as e:
        print(f"Error checking {module_name}: {e}")
    
    return False

def main():
    """Check the fhir_pipeline package for circular imports."""
    has_circular = check_module('fhir_pipeline')
    if not has_circular:
        print("No circular imports detected.")
    return 0 if not has_circular else 1

if __name__ == "__main__":
    sys.exit(main()) 