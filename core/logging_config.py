"""
Structured logging configuration using structlog.

This module configures structured logging for the entire application,
providing JSON-formatted logs with contextual information like request_id
and user_id.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to log entries.
    
    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary
        
    Returns:
        Modified event dictionary with app context
    """
    event_dict['app'] = 'dynamic-cookie-scanner'
    event_dict['version'] = '2.0.0'
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add log level to event dict.
    
    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary
        
    Returns:
        Modified event dictionary with log level
    """
    if method_name == 'warn':
        # Normalize 'warn' to 'warning'
        event_dict['level'] = 'warning'
    else:
        event_dict['level'] = method_name
    return event_dict


def configure_structlog(
    log_level: str = 'INFO',
    json_logs: bool = True,
    development_mode: bool = False
) -> None:
    """
    Configure structlog for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        development_mode: Whether to use development-friendly formatting
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )
    
    # Define processors
    processors: list[Processor] = [
        # Add log level
        add_log_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add app context
        add_app_context,
        # Add caller information (file, line, function)
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        # Stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
    ]
    
    if development_mode:
        # Development mode: colorful console output
        processors.extend([
            structlog.dev.ConsoleRenderer()
        ])
    else:
        # Production mode: JSON output
        if json_logs:
            processors.extend([
                structlog.processors.JSONRenderer()
            ])
        else:
            processors.extend([
                structlog.dev.ConsoleRenderer()
            ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to the logger.
    
    This adds context that will be included in all subsequent log entries
    within the current context (e.g., request_id, user_id).
    
    Args:
        **kwargs: Context variables to bind
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables from the logger.
    
    Args:
        *keys: Context variable keys to unbind
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """
    Clear all context variables from the logger.
    """
    structlog.contextvars.clear_contextvars()


# Example usage:
# from core.logging_config import get_logger, bind_context
#
# logger = get_logger(__name__)
# bind_context(request_id="abc123", user_id="user456")
# logger.info("processing_request", endpoint="/api/v1/scans")
# logger.error("scan_failed", scan_id="scan789", error="timeout")
