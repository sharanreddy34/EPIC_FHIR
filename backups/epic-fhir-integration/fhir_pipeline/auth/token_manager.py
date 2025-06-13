"""
Token management for authentication.
"""

import time


class TokenManager:
    """
    Manages authentication tokens.
    
    Provides a centralized way to obtain and cache authentication tokens.
    """
    
    def __init__(self, token_client):
        """
        Initialize the token manager.
        
        Args:
            token_client: Client used to obtain tokens
        """
        self.token_client = token_client
        self.token = None
        self.token_expiration = 0
    
    def get_token(self):
        """
        Get a valid authentication token.
        
        Returns:
            Valid authentication token
        """
        # Return cached token if still valid
        if self.token and time.time() < self.token_expiration:
            return self.token
        
        # Get a new token from the client
        self.token = self.token_client.get_token()
        # Set expiration (typically would come from token response)
        self.token_expiration = time.time() + 3600  # 1 hour from now
        
        return self.token 