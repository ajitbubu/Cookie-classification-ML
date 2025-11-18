#!/usr/bin/env python3
"""
Run database migrations for the enhanced scheduler.
"""

import sys
import logging
from database.migrate import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        print("Running database migrations...")
        run_migrations()
        print("Migrations completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
