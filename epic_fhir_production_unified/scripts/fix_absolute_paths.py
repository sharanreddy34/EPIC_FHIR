#!/usr/bin/env python3
"""
Script to find and fix absolute paths in the codebase, replacing them with
Path(__file__).resolve().parent patterns.
"""

import os
import re
import sys
from pathlib import Path


def find_absolute_paths(directory):
    """Find Python files with potential absolute paths.
    
    Args:
        directory: The directory to search.
        
    Returns:
        A list of (file_path, line_number, line) tuples.
    """
    results = []
    
    # Regular expressions to look for absolute paths
    patterns = [
        r'["\']\/[a-zA-Z0-9_\/\.]+["\']',  # '/path/to/something'
        r'os\.path\.join\(["\']\/[a-zA-Z0-9_\/\.]+',  # os.path.join('/path', ...)
        r'Path\(["\']\/[a-zA-Z0-9_\/\.]+["\']',  # Path('/path/to/something')
    ]
    
    compiled_patterns = [re.compile(pattern) for pattern in patterns]
    
    # Extensions to search
    extensions = ['.py', '.yaml', '.json']
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                
                # Skip this script itself
                if file_path == __file__:
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        for pattern in compiled_patterns:
                            if pattern.search(line):
                                results.append((file_path, i + 1, line.strip()))
                                break
    
    return results


def suggest_fix(file_path, line):
    """Suggest a fix for an absolute path.
    
    Args:
        file_path: The file containing the absolute path.
        line: The line containing the absolute path.
        
    Returns:
        A suggested fixed line using Path(__file__).
    """
    # Extract the absolute path
    matches = re.findall(r'["\']\/[a-zA-Z0-9_\/\.]+["\']', line)
    if not matches:
        return line
    
    # Decide whether to use Path or os.path based on the current import style
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    use_pathlib = 'from pathlib import Path' in content or 'import pathlib' in content
    
    new_line = line
    for match in matches:
        path = match.strip('\'"')
        
        if use_pathlib:
            # Replace with Path(__file__).resolve().parent
            new_path = f'Path(__file__).resolve().parent / "{os.path.basename(path)}"'
            new_line = new_line.replace(match, new_path)
        else:
            # Replace with os.path.join(os.path.dirname(__file__), ...)
            new_path = f'os.path.join(os.path.dirname(__file__), "{os.path.basename(path)}")'
            new_line = new_line.replace(match, new_path)
    
    return new_line


def main():
    """Main function to find and suggest fixes for absolute paths."""
    # Get the path to the epic_fhir_integration directory
    root_dir = Path(__file__).resolve().parent.parent / "epic_fhir_integration"
    
    print(f"Searching for absolute paths in {root_dir}...")
    
    results = find_absolute_paths(root_dir)
    
    if not results:
        print("No absolute paths found.")
        return 0
    
    print(f"Found {len(results)} potential absolute paths:")
    print()
    
    for file_path, line_number, line in results:
        rel_path = os.path.relpath(file_path, os.path.dirname(__file__))
        print(f"File: {rel_path}")
        print(f"Line {line_number}: {line}")
        print(f"Suggested: {suggest_fix(file_path, line)}")
        print()
    
    print("To automatically fix these issues, run:")
    print(f"{sys.argv[0]} --fix")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 