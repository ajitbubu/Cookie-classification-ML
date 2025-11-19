"""
Configuration management system with environment variable loading and validation.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, PostgresDsn, RedisDsn
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    model_config = SettingsConfigDict(env_prefix='DATABASE_', extra='ignore')
    
    url: str = Field(..., validation_alias='DATABASE_URL')
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_pre_ping: bool = Field(default=True)
    echo: bool = Field(default=False)


class RedisConfig(BaseSettings):
    """Redis configuration."""
    model_config = SettingsConfigDict(env_prefix='REDIS_', extra='ignore')
    
    url: str = Field(default='redis://localhost:6379/0')
    max_connections: int = Field(default=50, ge=1, le=1000)
    socket_timeout: int = Field(default=5, ge=1, le=60)
    socket_connect_timeout: int = Field(default=5, ge=1, le=60)
    decode_responses: bool = Field(default=True)


class APIConfig(BaseSettings):
    """API server configuration."""
    model_config = SettingsConfigDict(env_prefix='API_', extra='ignore')

    host: str = Field(default='0.0.0.0')
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=4, ge=1, le=32)
    reload: bool = Field(default=False)
    cors_origins: List[str] = Field(default_factory=list)
    request_timeout: int = Field(default=300, ge=1, le=3600)

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        if isinstance(v, list):
            return v
        return []


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    model_config = SettingsConfigDict(env_prefix='', extra='ignore')
    
    jwt_secret_key: str = Field(..., validation_alias='JWT_SECRET_KEY')
    jwt_algorithm: str = Field(default='HS256')
    jwt_expiration_hours: int = Field(default=1, ge=1, le=168)
    api_key_salt: str = Field(..., validation_alias='API_KEY_SALT')
    password_min_length: int = Field(default=8, ge=8, le=128)


class ScanConfig(BaseSettings):
    """Scanning configuration."""
    model_config = SettingsConfigDict(env_prefix='SCAN_', extra='ignore')
    
    max_concurrent_scans: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=300, ge=60, le=3600)
    browser_pool_size: int = Field(default=5, ge=1, le=20)
    max_depth_default: int = Field(default=5, ge=0, le=10)
    max_retry_default: int = Field(default=3, ge=0, le=5)
    default_button_selector: str = Field(default='button[data-role="accept"]')


class NotificationConfig(BaseSettings):
    """Notification configuration."""
    model_config = SettingsConfigDict(env_prefix='', extra='ignore')
    
    smtp_host: Optional[str] = Field(None)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None)
    smtp_password: Optional[str] = Field(None)
    smtp_from_email: Optional[str] = Field(None)
    smtp_use_tls: bool = Field(default=True)
    slack_webhook_url: Optional[str] = Field(None)
    webhook_timeout: int = Field(default=10, ge=1, le=60)
    notification_max_retries: int = Field(default=3, ge=0, le=5)


class CacheConfig(BaseSettings):
    """Cache configuration."""
    model_config = SettingsConfigDict(env_prefix='CACHE_', extra='ignore')
    
    ttl_scan_result: int = Field(default=300, ge=0)
    ttl_analytics_metrics: int = Field(default=3600, ge=0)
    ttl_analytics_trends: int = Field(default=3600, ge=0)
    ttl_user_preferences: int = Field(default=1800, ge=0)
    enabled: bool = Field(default=True)


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""
    model_config = SettingsConfigDict(env_prefix='', extra='ignore')
    
    prometheus_port: int = Field(default=9090, ge=1, le=65535)
    log_level: str = Field(default='INFO')
    log_format: str = Field(default='json')
    sentry_dsn: Optional[str] = Field(None)
    enable_metrics: bool = Field(default=True)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class Config(BaseSettings):
    """Main configuration class."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Environment
    environment: str = Field(default='development')
    debug: bool = Field(default=False)
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Legacy config support (for backward compatibility)
    api_url: Optional[str] = Field(None)
    result_api_url: Optional[str] = Field(None)
    fetch_cookie_categorization_api_url: Optional[str] = Field(None)
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = {'development', 'staging', 'production', 'test'}
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v.lower()
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.
        
        Returns:
            List of validation messages
        """
        messages = []
        
        # Check required fields for production
        if self.environment == 'production':
            if self.debug:
                messages.append("WARNING: Debug mode enabled in production")
            
            if not self.auth.jwt_secret_key or len(self.auth.jwt_secret_key) < 32:
                messages.append("ERROR: JWT secret key must be at least 32 characters in production")
            
            if not self.auth.api_key_salt or len(self.auth.api_key_salt) < 16:
                messages.append("ERROR: API key salt must be at least 16 characters in production")
        
        # Check notification config
        if self.notification.smtp_host:
            if not self.notification.smtp_user or not self.notification.smtp_password:
                messages.append("WARNING: SMTP host configured but credentials missing")
        
        # Check database pool settings
        if self.database.pool_size > self.database.max_overflow:
            messages.append("WARNING: Database pool_size should be <= max_overflow")
        
        return messages


class YAMLConfigLoader:
    """Load configuration from YAML files."""
    
    @staticmethod
    def load_yaml_config(config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Configuration dictionary
        """
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config or {}
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}
    
    @staticmethod
    def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries (override takes precedence).
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = YAMLConfigLoader.merge_configs(result[key], value)
            else:
                result[key] = value
        return result


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call init_config() first.")
    return _config


def init_config(
    env_file: Optional[str] = None,
    yaml_config_path: Optional[Path] = None
) -> Config:
    """
    Initialize the global configuration instance.
    
    Args:
        env_file: Path to .env file (optional)
        yaml_config_path: Path to YAML config file (optional)
        
    Returns:
        Initialized Config instance
    """
    global _config
    
    # Load YAML config if provided
    yaml_config = {}
    if yaml_config_path:
        yaml_config = YAMLConfigLoader.load_yaml_config(yaml_config_path)
    
    # Initialize config (environment variables take precedence)
    if env_file:
        _config = Config(_env_file=env_file)
    else:
        _config = Config()
    
    # Validate configuration
    validation_messages = _config.validate_config()
    for msg in validation_messages:
        if msg.startswith('ERROR'):
            logger.error(msg)
            raise ValueError(msg)
        else:
            logger.warning(msg)
    
    logger.info(f"Configuration initialized for environment: {_config.environment}")
    return _config


def reload_config():
    """Reload configuration (for hot reload support)."""
    global _config
    _config = None
    return init_config()
