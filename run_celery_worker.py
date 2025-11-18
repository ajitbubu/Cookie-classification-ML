#!/usr/bin/env python3
"""
Celery worker startup script.

Usage:
    python run_celery_worker.py [options]

Options:
    --queue QUEUE       Queue name to consume from (default: all queues)
    --concurrency N     Number of worker processes (default: 4)
    --loglevel LEVEL    Log level (default: INFO)
    --autoscale MAX,MIN Enable autoscaling with max and min workers
"""

import sys
import argparse
import logging
from services.celery_app import celery_app
from core.config import init_config

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Start Celery worker')
    
    parser.add_argument(
        '--queue',
        type=str,
        default=None,
        help='Queue name to consume from (default: all queues)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=4,
        help='Number of worker processes (default: 4)'
    )
    
    parser.add_argument(
        '--loglevel',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level (default: INFO)'
    )
    
    parser.add_argument(
        '--autoscale',
        type=str,
        default=None,
        help='Enable autoscaling with max,min workers (e.g., 10,3)'
    )
    
    parser.add_argument(
        '--pool',
        type=str,
        default='prefork',
        choices=['prefork', 'solo', 'threads', 'gevent'],
        help='Worker pool type (default: prefork)'
    )
    
    return parser.parse_args()


def main():
    """Start Celery worker."""
    args = parse_args()
    
    # Initialize configuration
    try:
        init_config()
        logger.info("Configuration initialized")
    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}")
        sys.exit(1)
    
    # Build worker arguments
    worker_args = [
        'worker',
        f'--loglevel={args.loglevel}',
        f'--pool={args.pool}',
    ]
    
    # Add queue if specified
    if args.queue:
        worker_args.extend(['--queues', args.queue])
        logger.info(f"Worker will consume from queue: {args.queue}")
    else:
        # Consume from all queues
        worker_args.extend(['--queues', 'default,reports,notifications'])
        logger.info("Worker will consume from all queues")
    
    # Add concurrency or autoscale
    if args.autoscale:
        worker_args.extend(['--autoscale', args.autoscale])
        logger.info(f"Worker autoscaling enabled: {args.autoscale}")
    else:
        worker_args.extend(['--concurrency', str(args.concurrency)])
        logger.info(f"Worker concurrency: {args.concurrency}")
    
    # Additional worker options
    worker_args.extend([
        '--time-limit=300',  # Hard time limit (5 minutes)
        '--soft-time-limit=270',  # Soft time limit (4.5 minutes)
        '--max-tasks-per-child=1000',  # Restart worker after N tasks
        '--prefetch-multiplier=4',  # Number of tasks to prefetch
    ])
    
    logger.info(f"Starting Celery worker with args: {' '.join(worker_args)}")
    
    # Start worker
    try:
        celery_app.worker_main(argv=worker_args)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
