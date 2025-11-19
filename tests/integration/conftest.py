"""
Shared fixtures for integration tests.

This module provides common fixtures used across integration tests.
"""

import pytest
import os
from typing import AsyncGenerator
import asyncpg
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/dcs_test')
os.environ['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
os.environ['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'test_secret_key_change_in_production')


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool_session() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create database pool for the test session."""
    test_db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/dcs_test')
    
    pool = await asyncpg.create_pool(
        dsn=test_db_url,
        min_size=2,
        max_size=10
    )
    
    yield pool
    
    await pool.close()


@pytest.fixture
async def db_pool(db_pool_session: asyncpg.Pool) -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide database pool for each test."""
    yield db_pool_session


@pytest.fixture
async def clean_database(db_pool: asyncpg.Pool):
    """Clean database before and after each test."""
    async with db_pool.acquire() as conn:
        # Clean tables in correct order (respecting foreign keys)
        await conn.execute("DELETE FROM cookies")
        await conn.execute("DELETE FROM scan_results")
        await conn.execute("DELETE FROM schedules")
        await conn.execute("DELETE FROM notification_preferences")
        await conn.execute("DELETE FROM notifications")
        await conn.execute("DELETE FROM reports")
        await conn.execute("DELETE FROM scan_profiles")
        await conn.execute("DELETE FROM api_keys")
        await conn.execute("DELETE FROM audit_logs")
        await conn.execute("DELETE FROM users")
    
    yield
    
    # Clean again after test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM cookies")
        await conn.execute("DELETE FROM scan_results")
        await conn.execute("DELETE FROM schedules")
        await conn.execute("DELETE FROM notification_preferences")
        await conn.execute("DELETE FROM notifications")
        await conn.execute("DELETE FROM reports")
        await conn.execute("DELETE FROM scan_profiles")
        await conn.execute("DELETE FROM api_keys")
        await conn.execute("DELETE FROM audit_logs")
        await conn.execute("DELETE FROM users")


@pytest.fixture
async def test_user(db_pool: asyncpg.Pool) -> dict:
    """Create a test user with admin role."""
    from api.auth.password import hash_password
    
    user_id = uuid4()
    email = "test@example.com"
    password = "password123"
    password_hash = hash_password(password)
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, email, password_hash, role, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            user_id, email, password_hash, "admin"
        )
    
    return {
        "user_id": user_id,
        "email": email,
        "password": password,
        "role": "admin"
    }


@pytest.fixture
async def test_user_viewer(db_pool: asyncpg.Pool) -> dict:
    """Create a test user with viewer role."""
    from api.auth.password import hash_password
    
    user_id = uuid4()
    email = "viewer@example.com"
    password = "password123"
    password_hash = hash_password(password)
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, email, password_hash, role, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            user_id, email, password_hash, "viewer"
        )
    
    return {
        "user_id": user_id,
        "email": email,
        "password": password,
        "role": "viewer"
    }


@pytest.fixture
async def auth_token(test_user: dict) -> str:
    """Generate JWT authentication token for test user."""
    from api.auth.jwt import create_access_token
    
    token_data = {
        "sub": str(test_user["user_id"]),
        "email": test_user["email"],
        "scopes": [
            "scans:read", "scans:write",
            "schedules:read", "schedules:write",
            "analytics:read",
            "profiles:read", "profiles:write",
            "notifications:read", "notifications:write"
        ]
    }
    
    return create_access_token(token_data)


@pytest.fixture
async def auth_token_viewer(test_user_viewer: dict) -> str:
    """Generate JWT authentication token for viewer user."""
    from api.auth.jwt import create_access_token
    
    token_data = {
        "sub": str(test_user_viewer["user_id"]),
        "email": test_user_viewer["email"],
        "scopes": [
            "scans:read",
            "schedules:read",
            "analytics:read"
        ]
    }
    
    return create_access_token(token_data)


@pytest.fixture
async def client(clean_database) -> AsyncGenerator[AsyncClient, None]:
    """Create HTTP client for API requests."""
    from api.main import create_app
    
    app = create_app()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_scan_data() -> dict:
    """Provide sample scan data for tests."""
    return {
        "domain": "https://example.com",
        "scan_mode": "quick",
        "params": {
            "custom_pages": ["/about", "/contact"],
            "max_retries": 3
        }
    }


@pytest.fixture
def sample_schedule_data() -> dict:
    """Provide sample schedule data for tests."""
    return {
        "domain_config_id": str(uuid4()),
        "domain": "https://example.com",
        "scan_type": "quick",
        "frequency": "daily",
        "time_config": {
            "hour": 9,
            "minute": 0
        },
        "enabled": True
    }


@pytest.fixture
async def create_test_scan(db_pool: asyncpg.Pool):
    """Factory fixture to create test scans in database."""
    async def _create_scan(
        domain: str = "https://example.com",
        scan_mode: str = "quick",
        status: str = "success",
        total_cookies: int = 10
    ):
        scan_id = uuid4()
        domain_config_id = uuid4()
        
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scan_results (
                    scan_id, domain_config_id, domain, scan_mode,
                    timestamp_utc, status, total_cookies, page_count,
                    duration_seconds, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, NOW(), NOW())
                """,
                scan_id, domain_config_id, domain, scan_mode,
                status, total_cookies, 5, 45.2
            )
        
        return scan_id
    
    return _create_scan


@pytest.fixture
async def create_test_schedule(db_pool: asyncpg.Pool):
    """Factory fixture to create test schedules in database."""
    async def _create_schedule(
        domain: str = "https://example.com",
        frequency: str = "daily",
        enabled: bool = True
    ):
        schedule_id = uuid4()
        domain_config_id = uuid4()
        
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO schedules (
                    schedule_id, domain_config_id, domain, scan_type,
                    scan_params, frequency, time_config, enabled,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                schedule_id, domain_config_id, domain, "quick",
                '{}', frequency, '{"hour": 9, "minute": 0}', enabled
            )
        
        return schedule_id
    
    return _create_schedule
