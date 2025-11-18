#!/usr/bin/env python3
"""
Celery Beat scheduler startup script.

Usage:
    python run_celery_beat.py [options]

Options:
    --loglevel LEVEL    Log level (default: INFO)
"""

import sys
import argparse
import logging
from services.celery_app import celery_app
from services.celery_beat_config import *  # Load beat schedule
from core.config import init_config

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Start Celery Beat scheduler')
    
    parser.add_argument(
        '--loglevel',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level (default: INFO)'
    )
    
    return parser.parse_args()


def main():
    """Start Celery Beat scheduler."""
    args = parse_args()
    
    # Initialize configuration
    try:
        init_config()
        logger.info("Configuration initialized")
    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}")
        sys.exit(1)
    
    # Build beat arguments
    beat_args = [
        'beat',
        f'--loglevel={args.loglevel}',
    ]
    
    logger.info(f"Starting Celery Beat scheduler with args: {' '.join(beat_args)}")
    logger.info(f"Scheduled tasks: {list(celery_app.conf.beat_schedule.keys())}")
    
    # Start beat scheduler
    try:
        celery_app.start(argv=beat_args)
    except KeyboardInterrupt:
        logger.info("Beat scheduler stopped by user")
    except Exception as e:
        logger.error(f"Beat scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
