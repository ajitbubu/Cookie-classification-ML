"""
Logger Setup Module

This module configures logging for the application. It supports:
- Daily rotating log files with retention.
- Optional console logging.
- Unified formatting for consistency across all loggers.
"""

import os
import logging
from logging import Logger
from logging.handlers import TimedRotatingFileHandler

from config import LOG_DIR, LOG_FILE, LOG_TO_CONSOLE


def setup_logger() -> Logger:
    """
    Configure and return the root logger.

    Features:
    - Creates the log directory if it does not exist.
    - Rotates log files daily at midnight.
    - Keeps 15 days of backups.
    - Logs to console if LOG_TO_CONSOLE is enabled.

    Returns:
        Logger: Configured root logger instance.
    """
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Common log format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler - rotate daily, keep 15 days
    handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=15, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Console handler (optional, controlled by config)
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
