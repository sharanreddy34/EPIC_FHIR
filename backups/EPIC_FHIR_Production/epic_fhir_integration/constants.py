"""Shared constants and helpers for locating datasets inside
Palantir Foundry as well as local dev runs.

Foundry mounts a writable scratch dataset at /foundry/objects by default.
When the image runs outside Foundry (e.g. in local Docker or during unit
tests) we fall back to the current working directory.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

__all__ = [
    "DATA_ROOT",
    "BRONZE",
    "SILVER",
    "GOLD",
]

# Determine the base directory where all datasets should be written.
_DATA_ROOT_ENV = os.getenv("DATA_ROOT")
if _DATA_ROOT_ENV:
    DATA_ROOT = Path(_DATA_ROOT_ENV)
else:
    # Local default: write next to the repo so that unit tests clean up easily.
    DATA_ROOT = Path.cwd() / "foundry_objects"

# Standard bronze/silver/gold sub-directories
BRONZE = DATA_ROOT / "bronze"
SILVER = DATA_ROOT / "silver"
GOLD = DATA_ROOT / "gold"

# Create the directories locally if running outside Foundry
if not _DATA_ROOT_ENV:  # Only create directories if not in Foundry
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    BRONZE.mkdir(parents=True, exist_ok=True)
    SILVER.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True) 