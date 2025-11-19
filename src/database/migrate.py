#!/usr/bin/env python3
"""
Database migration runner for Cookie Scanner Platform.
Executes SQL migration files in order.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment variable."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return db_url


def create_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        logger.info("Migrations tracking table ready")


def get_applied_migrations(conn):
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations ORDER BY migration_id")
        return {row[0] for row in cur.fetchall()}


def get_pending_migrations(migrations_dir, applied):
    """Get list of pending migration files."""
    migrations_path = Path(migrations_dir)
    if not migrations_path.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return []
    
    all_migrations = sorted([
        f for f in migrations_path.glob("*.sql")
        if f.is_file()
    ])
    
    pending = [m for m in all_migrations if m.name not in applied]
    return pending


def apply_migration(conn, migration_file):
    """Apply a single migration file."""
    logger.info(f"Applying migration: {migration_file.name}")
    
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (migration_file.name,)
            )
        conn.commit()
        logger.info(f"Successfully applied: {migration_file.name}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to apply {migration_file.name}: {e}")
        raise


def run_migrations(database_url=None, migrations_dir=None):
    """Run all pending migrations."""
    if database_url is None:
        database_url = get_database_url()
    
    if migrations_dir is None:
        migrations_dir = Path(__file__).parent / "migrations"
    
    logger.info(f"Connecting to database...")
    conn = psycopg2.connect(database_url)
    
    try:
        # Create migrations tracking table
        create_migrations_table(conn)
        
        # Get applied and pending migrations
        applied = get_applied_migrations(conn)
        pending = get_pending_migrations(migrations_dir, applied)
        
        if not pending:
            logger.info("No pending migrations")
            return
        
        logger.info(f"Found {len(pending)} pending migration(s)")
        
        # Apply each pending migration
        for migration_file in pending:
            apply_migration(conn, migration_file)
        
        logger.info("All migrations applied successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def rollback_last_migration(database_url=None):
    """Rollback the last applied migration (not implemented - manual rollback required)."""
    logger.warning("Automatic rollback not implemented. Please manually rollback if needed.")
    # Note: Implementing automatic rollback would require down migration files


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--url', help='Database URL (overrides DATABASE_URL env var)')
    parser.add_argument('--dir', help='Migrations directory path')
    
    args = parser.parse_args()
    
    try:
        run_migrations(
            database_url=args.url,
            migrations_dir=args.dir
        )
    except Exception as e:
        logger.error(f"Migration error: {e}")
        sys.exit(1)
