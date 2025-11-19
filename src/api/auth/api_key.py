"""
API key generation and validation utilities.
"""

import secrets
import hashlib
from typing import Optional
from datetime import datetime

from src.core.config import get_config


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        API key string (64 characters)
    """
    return secrets.token_urlsafe(48)  # Generates ~64 character string


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256 with salt.
    
    Args:
        api_key: Plain API key
        
    Returns:
        Hashed API key
    """
    config = get_config()
    salt = config.auth.api_key_salt.encode()
    key_bytes = api_key.encode()
    
    # Combine salt and key, then hash
    salted_key = salt + key_bytes
    hashed = hashlib.sha256(salted_key).hexdigest()
    
    return hashed


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        plain_key: Plain API key to verify
        hashed_key: Hashed API key to compare against
        
    Returns:
        True if key matches, False otherwise
    """
    return hash_api_key(plain_key) == hashed_key


class APIKeyValidator:
    """API key validation helper."""
    
    def __init__(self):
        """Initialize validator."""
        self.config = get_config()
    
    def validate_key_format(self, api_key: str) -> bool:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if format is valid
        """
        # Check length and characters
        if not api_key or len(api_key) < 32:
            return False
        
        # Check for valid URL-safe base64 characters
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        return all(c in valid_chars for c in api_key)
    
    def is_expired(self, expires_at: Optional[datetime]) -> bool:
        """
        Check if API key is expired.
        
        Args:
            expires_at: Expiration timestamp
            
        Returns:
            True if expired
        """
        if expires_at is None:
            return False
        
        return datetime.utcnow() > expires_at
