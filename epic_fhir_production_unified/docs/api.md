# Epic FHIR Integration API Reference

This document provides a reference for the API components in the Epic FHIR Integration package.

## Table of Contents

- [API Clients](#api-clients)
- [Bronze Layer](#bronze-layer)
- [Silver Layer](#silver-layer)
- [Gold Layer](#gold-layer)
- [Validation](#validation)
- [Utilities](#utilities)

## API Clients

The `epic_fhir_integration.api_clients` package provides tools for authenticating with Epic's FHIR API and making requests.

### JWT Authentication

```python
from epic_fhir_integration.api_clients.jwt_auth import get_or_refresh_token

# Get a token (will create or refresh as needed)
token = get_or_refresh_token()
```

### FHIR Client

```python
from epic_fhir_integration.api_clients.fhir_client import create_fhir_client

# Create a client with automatic token handling
client = create_fhir_client()

# Get patient resources
patients = client.get_all_resources("Patient", params={"_count": 100})
```

## Bronze Layer

TO BE EXPANDED

## Silver Layer

TO BE EXPANDED

## Gold Layer

TO BE EXPANDED

## Validation

TO BE EXPANDED

## Utilities

TO BE EXPANDED 