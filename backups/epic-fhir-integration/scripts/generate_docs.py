#!/usr/bin/env python3
"""
Script to generate API documentation for the epic_fhir_integration package using pdoc.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def generate_docs():
    """Generate API documentation for the epic_fhir_integration package."""
    # Get the path to the root directory
    root_dir = Path(__file__).resolve().parent.parent
    
    # Create the output directory if it doesn't exist
    docs_dir = root_dir / "site"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(exist_ok=True)
    
    print(f"Generating documentation in {docs_dir}...")
    
    # Run pdoc to generate the documentation
    try:
        subprocess.run(
            [
                "pdoc",
                "--html",
                "--output-dir", str(docs_dir),
                "--config", "show_source_code=True",
                "--config", "show_type_annotations=True",
                "--config", "show_submodules=True",
                "epic_fhir_integration"
            ],
            check=True,
            cwd=root_dir
        )
        print(f"Documentation generated successfully in {docs_dir}")
        
        # Create an index.html that redirects to the package documentation
        index_path = docs_dir / "index.html"
        with open(index_path, "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Epic FHIR Integration Documentation</title>
    <meta http-equiv="refresh" content="0; url=./epic_fhir_integration.html">
</head>
<body>
    <p>Redirecting to <a href="./epic_fhir_integration.html">package documentation</a>...</p>
</body>
</html>
            """)
        
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error generating documentation: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Make sure pdoc is installed
    try:
        import pdoc
    except ImportError:
        print("pdoc is not installed. Installing it now...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "pdoc3"], check=True)
    
    sys.exit(generate_docs()) 