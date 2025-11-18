"""
Sentry error tracking configuration.

This module configures Sentry for error tracking and performance monitoring.
"""

import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: str,
    environment: str = 'development',
    release: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True
) -> None:
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (development, staging, production)
        release: Release version (e.g., '2.0.0')
        traces_sample_rate: Percentage of transactions to trace (0.0 to 1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0 to 1.0)
        enable_tracing: Whether to enable performance tracing
    """
    if not dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return
    
    try:
        # Configure logging integration
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        # Initialize Sentry
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release or '2.0.0',
            traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
            profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
            integrations=[
                logging_integration,
                AsyncioIntegration(),
                RedisIntegration(),
                SqlalchemyIntegration(),
            ],
            # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
            # We recommend adjusting this value in production
            send_default_pii=False,  # Don't send personally identifiable information
            attach_stacktrace=True,  # Attach stack traces to messages
            max_breadcrumbs=50,  # Maximum number of breadcrumbs
            before_send=before_send_filter,
        )
        
        logger.info(
            f"Sentry initialized successfully: environment={environment}, "
            f"traces_sample_rate={traces_sample_rate}"
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event, hint):
    """
    Filter events before sending to Sentry.
    
    This function can be used to:
    - Filter out certain types of errors
    - Scrub sensitive data
    - Add additional context
    
    Args:
        event: The event dictionary
        hint: Additional information about the event
        
    Returns:
        Modified event or None to drop the event
    """
    # Example: Don't send 404 errors
    if 'exception' in event:
        exc_info = hint.get('exc_info')
        if exc_info:
            exc_type, exc_value, tb = exc_info
            if '404' in str(exc_value):
                return None
    
    # Example: Scrub sensitive headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        if 'Authorization' in headers:
            headers['Authorization'] = '[Filtered]'
        if 'X-API-Key' in headers:
            headers['X-API-Key'] = '[Filtered]'
    
    return event


def add_breadcrumb(
    message: str,
    category: str = 'default',
    level: str = 'info',
    data: Optional[dict] = None
) -> None:
    """
    Add a breadcrumb for debugging context.
    
    Breadcrumbs are a trail of events that happened before an error.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., 'scan', 'api', 'database')
        level: Level (debug, info, warning, error, critical)
        data: Additional data dictionary
    """
    try:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    except Exception as e:
        logger.debug(f"Failed to add Sentry breadcrumb: {e}")


def capture_exception(error: Exception, **kwargs) -> None:
    """
    Manually capture an exception.
    
    Args:
        error: The exception to capture
        **kwargs: Additional context (tags, extras, etc.)
    """
    try:
        with sentry_sdk.push_scope() as scope:
            # Add tags
            for key, value in kwargs.get('tags', {}).items():
                scope.set_tag(key, value)
            
            # Add extra context
            for key, value in kwargs.get('extras', {}).items():
                scope.set_extra(key, value)
            
            # Set user context if provided
            if 'user' in kwargs:
                scope.set_user(kwargs['user'])
            
            # Capture exception
            sentry_sdk.capture_exception(error)
            
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {e}")


def capture_message(message: str, level: str = 'info', **kwargs) -> None:
    """
    Manually capture a message.
    
    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        **kwargs: Additional context (tags, extras, etc.)
    """
    try:
        with sentry_sdk.push_scope() as scope:
            # Add tags
            for key, value in kwargs.get('tags', {}).items():
                scope.set_tag(key, value)
            
            # Add extra context
            for key, value in kwargs.get('extras', {}).items():
                scope.set_extra(key, value)
            
            # Capture message
            sentry_sdk.capture_message(message, level=level)
            
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {e}")


def set_user_context(user_id: str, email: Optional[str] = None, **kwargs) -> None:
    """
    Set user context for error tracking.
    
    Args:
        user_id: User ID
        email: User email (optional)
        **kwargs: Additional user attributes
    """
    try:
        user_data = {
            'id': user_id,
            **kwargs
        }
        if email:
            user_data['email'] = email
        
        sentry_sdk.set_user(user_data)
        
    except Exception as e:
        logger.debug(f"Failed to set user context in Sentry: {e}")


def set_context(key: str, value: dict) -> None:
    """
    Set additional context for error tracking.
    
    Args:
        key: Context key (e.g., 'scan', 'request')
        value: Context data dictionary
    """
    try:
        sentry_sdk.set_context(key, value)
    except Exception as e:
        logger.debug(f"Failed to set context in Sentry: {e}")


def set_tag(key: str, value: str) -> None:
    """
    Set a tag for error tracking.
    
    Tags are searchable in Sentry.
    
    Args:
        key: Tag key
        value: Tag value
    """
    try:
        sentry_sdk.set_tag(key, value)
    except Exception as e:
        logger.debug(f"Failed to set tag in Sentry: {e}")


# Example usage:
# from core.sentry_config import init_sentry, add_breadcrumb, capture_exception
#
# # Initialize Sentry
# init_sentry(
#     dsn="https://xxx@sentry.io/xxx",
#     environment="production",
#     release="2.0.0"
# )
#
# # Add breadcrumbs
# add_breadcrumb("Starting scan", category="scan", data={"domain": "example.com"})
#
# # Capture exception
# try:
#     # ... code that might fail
#     pass
# except Exception as e:
#     capture_exception(e, tags={"scan_mode": "quick"}, extras={"domain": "example.com"})
