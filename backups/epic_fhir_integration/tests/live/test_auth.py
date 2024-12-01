import pytest
import os
import json
import time
import logging
from epic_fhir_integration.auth.jwt_auth import EpicJWTAuth
from epic_fhir_integration.config.loader import load_config
from epic_fhir_integration.extract.fhir_client import EpicFHIRClient

logger = logging.getLogger(__name__)

@pytest.fixture
def config():
    """Load configuration for testing."""
    config_path = os.environ.get("EPIC_CONFIG_PATH", "config/live_epic_auth.json")
    return load_config(config_path)

@pytest.fixture
def auth_manager(config):
    """Initialize JWT auth manager."""
    return EpicJWTAuth(config)

@pytest.fixture
def client(config):
    """Initialize FHIR client with test configuration."""
    return EpicFHIRClient(config)

def test_generate_jwt_token(auth_manager):
    """Test generating a JWT token."""
    token = auth_manager.generate_jwt_token()
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    
    # JWT tokens have 3 parts separated by dots
    parts = token.split('.')
    assert len(parts) == 3

def test_get_access_token(auth_manager):
    """Test obtaining an access token from Epic."""
    access_token_response = auth_manager.get_access_token()
    assert access_token_response is not None
    assert "access_token" in access_token_response
    assert "expires_in" in access_token_response
    assert "token_type" in access_token_response
    assert access_token_response["token_type"] == "Bearer"
    
    # Save token for later tests
    token_path = "temp/test_access_token.json"
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    with open(token_path, "w") as f:
        json.dump(access_token_response, f)

def test_token_refresh(auth_manager):
    """Test token refresh mechanism."""
    # Get initial token
    token1 = auth_manager.get_access_token()
    assert token1 is not None
    
    # Force expire the token (this is a mock for testing)
    auth_manager._token_expiry = time.time() - 10
    
    # Get a new token, should refresh
    token2 = auth_manager.get_access_token()
    assert token2 is not None
    
    # Tokens should be different after refresh
    assert token1["access_token"] != token2["access_token"]

def test_token_caching(auth_manager):
    """Test token caching mechanism."""
    # Get a token
    token1 = auth_manager.get_access_token()
    
    # Get another token immediately, should be the same (cached)
    token2 = auth_manager.get_access_token()
    
    # Tokens should be identical if caching works
    assert token1["access_token"] == token2["access_token"]

def test_auth_error_handling(config):
    """Test handling of authentication errors."""
    # Create a config with invalid credentials
    invalid_config = config.copy()
    invalid_config["client_id"] = "invalid_client_id"
    
    # Initialize with invalid config
    invalid_auth = EpicJWTAuth(invalid_config)
    
    # Attempt to get token should raise an exception
    with pytest.raises(Exception) as excinfo:
        invalid_auth.get_access_token()
    
    # Verify the error message contains relevant information
    assert "authentication failed" in str(excinfo.value).lower() or "unauthorized" in str(excinfo.value).lower()

def test_api_call_with_auth(client):
    """Test making an authenticated API call."""
    # Make a simple metadata request that requires authentication
    response = client.get_metadata()
    
    # Verify we got a valid response
    assert response is not None
    assert response.get("resourceType") == "CapabilityStatement"
    
    # Check for SMART capabilities
    rest = response.get("rest", [{}])[0]
    security = rest.get("security", {})
    extensions = security.get("extension", [])
    
    # Find SMART extension
    smart_extensions = [ext for ext in extensions 
                      if ext.get("url") == "http://fhir-registry.smarthealthit.org/StructureDefinition/capabilities"]
    
    assert len(smart_extensions) > 0 