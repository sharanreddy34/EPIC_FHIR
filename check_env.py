#!/usr/bin/env python
"""
Environment checker for Epic FHIR Integration in Foundry.
"""

import os
import sys
import platform

def main():
    """Print environment information to verify setup."""
    print("Python Environment Check")
    print("=" * 30)
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print(f"Working directory: {os.getcwd()}")
    
    print("\nEnvironment Variables:")
    for key, value in sorted(os.environ.items()):
        if key.startswith(('PYTHONPATH', 'FOUNDRY', 'EPIC')):
            print(f"  {key}={value}")
    
    print("\nDirectory Contents:")
    for item in sorted(os.listdir('.')):
        if os.path.isdir(item):
            print(f"  📁 {item}/")
        else:
            print(f"  📄 {item}")

if __name__ == "__main__":
    main() 