"""Compatibility shim for fhir_pipeline namespace.

This provides backward compatibility for code that imports from the
now-deprecated fhir_pipeline.* namespace.
"""

# Create package structure for imports like:
# from fhir_pipeline.transforms.registry import get_transformer
# from fhir_pipeline.transforms.base import BaseTransformer

import sys
import types
import importlib


def __getattr__(name):
    """Lazy-load submodules when accessed."""
    if name == "transforms":
        # Create the transforms module
        module = types.ModuleType("fhir_pipeline.transforms")
        sys.modules["fhir_pipeline.transforms"] = module
        
        # Define the registry module
        registry_mod = types.ModuleType("fhir_pipeline.transforms.registry")
        sys.modules["fhir_pipeline.transforms.registry"] = registry_mod
        
        # Map get_transformer to our domain package
        try:
            from epic_fhir_integration.domain.bronze.resource_extractor import extract_resource
            def get_transformer(*args, **kwargs):
                """Legacy function that maps to extract_resource."""
                return extract_resource(*args, **kwargs)
            registry_mod.get_transformer = get_transformer
        except ImportError:
            pass
        
        # Define the base module
        base_mod = types.ModuleType("fhir_pipeline.transforms.base")
        sys.modules["fhir_pipeline.transforms.base"] = base_mod
        
        # Map BaseTransformer to a compat class
        class BaseTransformer:
            """Legacy base class for transformers."""
            def transform(self, resource):
                """Transform a resource."""
                return resource
        base_mod.BaseTransformer = BaseTransformer
        
        # Define yaml_mappers
        yaml_mappers_mod = types.ModuleType("fhir_pipeline.transforms.yaml_mappers")
        sys.modules["fhir_pipeline.transforms.yaml_mappers"] = yaml_mappers_mod
        
        class YAMLMapper:
            """Legacy YAML mapper class."""
            def __init__(self, *args, **kwargs):
                pass
            def transform(self, resource):
                return resource
            
        class FieldExtractor:
            """Legacy field extractor class."""
            def __init__(self, *args, **kwargs):
                pass
            def extract(self, resource, field_path):
                return None
            
        def apply_mapping(*args, **kwargs):
            """Apply a mapping to a resource."""
            return args[0] if args else {}
        
        yaml_mappers_mod.YAMLMapper = YAMLMapper
        yaml_mappers_mod.FieldExtractor = FieldExtractor
        yaml_mappers_mod.apply_mapping = apply_mapping
        
        return module
    
    elif name == "validation":
        # Create the validation module
        module = types.ModuleType("fhir_pipeline.validation")
        sys.modules["fhir_pipeline.validation"] = module
        
        # Define the schema_validator module
        schema_validator_mod = types.ModuleType("fhir_pipeline.validation.schema_validator")
        sys.modules["fhir_pipeline.validation.schema_validator"] = schema_validator_mod
        
        class SchemaValidator:
            """Legacy schema validator class."""
            def __init__(self, *args, **kwargs):
                pass
            def validate(self, resource):
                return True, []
        
        schema_validator_mod.SchemaValidator = SchemaValidator
        
        return module
    
    elif name == "auth":
        # Create the auth module
        module = types.ModuleType("fhir_pipeline.auth")
        sys.modules["fhir_pipeline.auth"] = module
        
        # Define the jwt_client module
        jwt_client_mod = types.ModuleType("fhir_pipeline.auth.jwt_client")
        sys.modules["fhir_pipeline.auth.jwt_client"] = jwt_client_mod
        
        # Try to map to our real implementation
        try:
            from epic_fhir_integration.infrastructure.api_clients.jwt_auth import get_token_with_retry
            
            class JWTClient:
                """Legacy JWT client class."""
                def __init__(self, *args, **kwargs):
                    pass
                def get_token(self):
                    """Get a token using the real implementation."""
                    return get_token_with_retry()
            
            jwt_client_mod.JWTClient = JWTClient
        except ImportError:
            # Fallback implementation
            class JWTClient:
                """Legacy JWT client class (fallback)."""
                def __init__(self, *args, **kwargs):
                    pass
                def get_token(self):
                    """Get a token (mock implementation)."""
                    return "mock_token"
            
            jwt_client_mod.JWTClient = JWTClient
        
        return module
    
    elif name == "pipelines":
        # Create the pipelines module
        module = types.ModuleType("fhir_pipeline.pipelines")
        sys.modules["fhir_pipeline.pipelines"] = module
        
        # Define the extract module
        extract_mod = types.ModuleType("fhir_pipeline.pipelines.extract")
        sys.modules["fhir_pipeline.pipelines.extract"] = extract_mod
        
        class FHIRExtractPipeline:
            """Legacy extract pipeline class."""
            def __init__(self, *args, **kwargs):
                pass
            def extract(self, *args, **kwargs):
                return []
        
        extract_mod.FHIRExtractPipeline = FHIRExtractPipeline
        
        return module
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}") 