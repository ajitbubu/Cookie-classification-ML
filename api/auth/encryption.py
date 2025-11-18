"""
Encryption utilities for sensitive data at rest.

This module provides encryption/decryption for sensitive fields such as:
- Notification webhook URLs
- API keys (in addition to hashing)
- Other sensitive configuration data

Uses Fernet (symmetric encryption) from the cryptography library.
"""

import logging
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from core.config import get_config

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manager for encrypting and decrypting sensitive data.
    
    Uses Fernet symmetric encryption with a key derived from the
    application's secret key.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            secret_key: Secret key for encryption (defaults to config)
        """
        if secret_key is None:
            config = get_config()
            secret_key = config.auth.jwt_secret_key
        
        # Derive a Fernet key from the secret key
        self.fernet = self._create_fernet(secret_key)
    
    def _create_fernet(self, secret_key: str) -> Fernet:
        """
        Create a Fernet instance from a secret key.
        
        Args:
            secret_key: Secret key string
            
        Returns:
            Fernet instance
        """
        # Use PBKDF2 to derive a 32-byte key suitable for Fernet
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'cookie_scanner_salt',  # Static salt for deterministic key derivation
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (base64 encoded) or None on error
        """
        if not plaintext:
            return None
        
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plaintext string or None on error
        """
        if not ciphertext:
            return None
        
        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or corrupted data")
            return None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()
        
        for field in fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_value = self.encrypt(str(encrypted_data[field]))
                if encrypted_value:
                    encrypted_data[field] = encrypted_value
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()
        
        for field in fields:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_value = self.decrypt(decrypted_data[field])
                if decrypted_value:
                    decrypted_data[field] = decrypted_value
        
        return decrypted_data


# Singleton instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_webhook_url(url: str) -> Optional[str]:
    """
    Encrypt a webhook URL.
    
    Args:
        url: Webhook URL to encrypt
        
    Returns:
        Encrypted URL or None on error
    """
    manager = get_encryption_manager()
    return manager.encrypt(url)


def decrypt_webhook_url(encrypted_url: str) -> Optional[str]:
    """
    Decrypt a webhook URL.
    
    Args:
        encrypted_url: Encrypted webhook URL
        
    Returns:
        Decrypted URL or None on error
    """
    manager = get_encryption_manager()
    return manager.decrypt(encrypted_url)


def encrypt_sensitive_config(config: dict) -> dict:
    """
    Encrypt sensitive fields in a configuration dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with sensitive fields encrypted
    """
    sensitive_fields = [
        'webhook_url',
        'smtp_password',
        'api_secret',
        'slack_webhook_url',
        'database_password'
    ]
    
    manager = get_encryption_manager()
    return manager.encrypt_dict(config, sensitive_fields)


def decrypt_sensitive_config(config: dict) -> dict:
    """
    Decrypt sensitive fields in a configuration dictionary.
    
    Args:
        config: Configuration dictionary with encrypted fields
        
    Returns:
        Configuration with sensitive fields decrypted
    """
    sensitive_fields = [
        'webhook_url',
        'smtp_password',
        'api_secret',
        'slack_webhook_url',
        'database_password'
    ]
    
    manager = get_encryption_manager()
    return manager.decrypt_dict(config, sensitive_fields)
