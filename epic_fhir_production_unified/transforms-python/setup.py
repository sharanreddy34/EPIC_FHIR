"""
Setup script for epic-fhir-integration package.

This setup script is used for local development and testing.
In production, the package is installed via Foundry's Conda recipe.
"""

from setuptools import setup, find_packages

setup(
    name="epic-fhir-integration",
    version="1.0.0",
    description="FHIR Pipeline for Epic integration",
    author="ATLAS Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10,<3.13",
    install_requires=[
        "pyyaml",
        "requests>=2.31.0",
        "pyjwt[crypto]>=2.4.0",
        "cryptography>=36.0.0",
        "psutil",
        "pydantic>=1.10.11,<2.0.0",
        "fhir.resources>=6.0.0",
        "fhirpathpy>=0.2.2,<0.3.0",
        "tenacity>=8.0.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "analytics": [
            "pyspark>=3.2.0",
            "pathling-client>=6.0.0",
        ],
        "science": [
            "pandas>=1.5.3,<2",
            "dask",
            "matplotlib>=3.7.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black",
            "isort",
            "pylint",
        ],
        "foundry": [
            "foundry-dev-tools>=0.8.0",
            "deltalake>=0.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "epic-fhir-get-token=epic_fhir_integration.cli.auth_token:main",
            "epic-fhir-run-pipeline=epic_fhir_integration.cli.run_pipeline:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
) 