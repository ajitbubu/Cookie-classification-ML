"""
Database connection management with connection pooling.
"""

import os
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database connection manager with connection pooling.
    
    Provides connection pooling for PostgreSQL database operations
    with automatic connection health checks.
    """
    
    def __init__(
        self,
        database_url: str,
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize database connection pool.
        
        Args:
            database_url: PostgreSQL connection URL
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                self.database_url
            )
            logger.info(
                f"Database connection pool initialized "
                f"(min={self.min_connections}, max={self.max_connections})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            Database connection
        """
        if self.pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            conn = self.pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn):
        """
        Return a connection to the pool.
        
        Args:
            conn: Database connection to return
        """
        if self.pool is None:
            return
        
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        if self.pool is not None:
            self.pool.closeall()
            logger.info("All database connections closed")
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """
        Execute a query and return results.
        
        Args:
            query: SQL query
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, None otherwise
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_many(self, query: str, params_list: list):
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch execution failed: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def ping(self) -> bool:
        """
        Check if database is available.
        
        Returns:
            True if database is available, False otherwise
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False
        finally:
            if conn:
                self.return_connection(conn)


# Singleton instance
_db_connection: Optional[DatabaseConnection] = None


def get_db_connection() -> DatabaseConnection:
    """Get the global database connection instance."""
    global _db_connection
    if _db_connection is None:
        raise RuntimeError(
            "Database connection not initialized. Call init_db_connection() first."
        )
    return _db_connection


def init_db_connection(
    database_url: Optional[str] = None,
    min_connections: int = 1,
    max_connections: int = 10
) -> DatabaseConnection:
    """
    Initialize the global database connection instance.
    
    Args:
        database_url: PostgreSQL connection URL (defaults to DATABASE_URL env var)
        min_connections: Minimum connections in pool
        max_connections: Maximum connections in pool
        
    Returns:
        DatabaseConnection instance
    """
    global _db_connection
    
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    _db_connection = DatabaseConnection(
        database_url,
        min_connections=min_connections,
        max_connections=max_connections
    )
    return _db_connection
