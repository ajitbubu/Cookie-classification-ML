"""
Integration tests for API endpoints.

These tests verify the complete workflow of API endpoints including:
- Scan creation and retrieval
- Schedule CRUD operations
- Analytics endpoints
- Authentication and authorization
- Error handling and validation
"""

import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime
from typing import AsyncGenerator
import asyncpg
from httpx import AsyncClient, ASGITransport

# Import the FastAPI app
from api.main import create_app


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create test database pool."""
    # Use test database URL
    test_db_url = "postgresql://postgres:postgres@localhost:5432/dcs_test"
    
    pool = await asyncpg.create_pool(
        dsn=test_db_url,
        min_size=2,
        max_size=5
    )
    
    yield pool
    
    await pool.close()


@pytest.fixture
async def clean_database(db_pool: asyncpg.Pool):
    """Clean database before each test."""
    async with db_pool.acquire() as conn:
        # Clean tables in correct order (respecting foreign keys)
        await conn.execute("DELETE FROM cookies")
        await conn.execute("DELETE FROM scan_results")
        await conn.execute("DELETE FROM schedules")
        await conn.execute("DELETE FROM api_keys")
        await conn.execute("DELETE FROM users")
    
    yield
    
    # Clean again after test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM cookies")
        await conn.execute("DELETE FROM scan_results")
        await conn.execute("DELETE FROM schedules")
        await conn.execute("DELETE FROM api_keys")
        await conn.execute("DELETE FROM users")


@pytest.fixture
async def test_user(db_pool: asyncpg.Pool) -> dict:
    """Create a test user."""
    user_id = uuid4()
    email = "test@example.com"
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNqN8qN8q"  # "password"
    
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
        "password": "password",
        "role": "admin"
    }


@pytest.fixture
async def auth_token(test_user: dict) -> str:
    """Generate authentication token for test user."""
    from api.auth.jwt import create_access_token
    
    token_data = {
        "sub": str(test_user["user_id"]),
        "email": test_user["email"],
        "scopes": ["scans:read", "scans:write", "schedules:read", "schedules:write"]
    }
    
    return create_access_token(token_data)


@pytest.fixture
async def client(clean_database) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    app = create_app()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Scan Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_scan_success(client: AsyncClient, auth_token: str):
    """Test successful scan creation."""
    response = await client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "domain": "https://example.com",
            "scan_mode": "quick",
            "params": {
                "custom_pages": ["/about", "/contact"]
            }
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "pending"
    assert "message" in data


@pytest.mark.asyncio
async def test_create_scan_invalid_domain(client: AsyncClient, auth_token: str):
    """Test scan creation with invalid domain."""
    response = await client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "domain": "not-a-valid-url",
            "scan_mode": "quick"
        }
    )
    
    assert response.status_code == 400
    assert "protocol" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_scan_unauthorized(client: AsyncClient):
    """Test scan creation without authentication."""
    response = await client.post(
        "/api/v1/scans",
        json={
            "domain": "https://example.com",
            "scan_mode": "quick"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_scan_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test retrieving a scan by ID."""
    # Create a scan in database
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
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            """,
            scan_id, domain_config_id, "https://example.com", "quick",
            datetime.utcnow(), "success", 10, 5, 45.2
        )
    
    response = await client.get(
        f"/api/v1/scans/{scan_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["scan_id"] == str(scan_id)
    assert data["domain"] == "https://example.com"
    assert data["status"] == "success"
    assert data["total_cookies"] == 10


@pytest.mark.asyncio
async def test_get_scan_not_found(client: AsyncClient, auth_token: str):
    """Test retrieving non-existent scan."""
    scan_id = uuid4()
    
    response = await client.get(
        f"/api/v1/scans/{scan_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_scans_pagination(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test listing scans with pagination."""
    # Create multiple scans
    domain_config_id = uuid4()
    
    async with db_pool.acquire() as conn:
        for i in range(5):
            scan_id = uuid4()
            await conn.execute(
                """
                INSERT INTO scan_results (
                    scan_id, domain_config_id, domain, scan_mode,
                    timestamp_utc, status, total_cookies, page_count,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                scan_id, domain_config_id, f"https://example{i}.com", "quick",
                datetime.utcnow(), "success", i * 10, i * 5
            )
    
    response = await client.get(
        "/api/v1/scans?page=1&page_size=3",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert data["has_next"] is True
    assert data["has_prev"] is False


@pytest.mark.asyncio
async def test_list_scans_filtering(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test listing scans with filters."""
    domain_config_id = uuid4()
    
    async with db_pool.acquire() as conn:
        # Create scans with different statuses
        for status in ["success", "failed", "pending"]:
            scan_id = uuid4()
            await conn.execute(
                """
                INSERT INTO scan_results (
                    scan_id, domain_config_id, domain, scan_mode,
                    timestamp_utc, status, total_cookies, page_count,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                scan_id, domain_config_id, "https://example.com", "quick",
                datetime.utcnow(), status, 10, 5
            )
    
    # Filter by status
    response = await client.get(
        "/api/v1/scans?status=success",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_delete_scan_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test deleting a completed scan."""
    scan_id = uuid4()
    domain_config_id = uuid4()
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scan_results (
                scan_id, domain_config_id, domain, scan_mode,
                timestamp_utc, status, total_cookies, page_count,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            """,
            scan_id, domain_config_id, "https://example.com", "quick",
            datetime.utcnow(), "success", 10, 5
        )
    
    response = await client.delete(
        f"/api/v1/scans/{scan_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 204
    
    # Verify scan is deleted
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM scan_results WHERE scan_id = $1",
            scan_id
        )
        assert row is None


# ============================================================================
# Schedule Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_schedule_success(client: AsyncClient, auth_token: str):
    """Test successful schedule creation."""
    response = await client.post(
        "/api/v1/schedules",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
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
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "schedule_id" in data
    assert data["domain"] == "https://example.com"
    assert data["frequency"] == "daily"
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_schedule_invalid_time_config(client: AsyncClient, auth_token: str):
    """Test schedule creation with invalid time configuration."""
    response = await client.post(
        "/api/v1/schedules",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "domain_config_id": str(uuid4()),
            "domain": "https://example.com",
            "frequency": "daily",
            "time_config": {
                "minute": 0  # Missing 'hour' for daily schedule
            },
            "enabled": True
        }
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_schedule_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test retrieving a schedule by ID."""
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
            schedule_id, domain_config_id, "https://example.com", "quick",
            '{}', "daily", '{"hour": 9, "minute": 0}', True
        )
    
    response = await client.get(
        f"/api/v1/schedules/{schedule_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["schedule_id"] == str(schedule_id)
    assert data["domain"] == "https://example.com"
    assert data["frequency"] == "daily"


@pytest.mark.asyncio
async def test_list_schedules_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test listing schedules."""
    domain_config_id = uuid4()
    
    async with db_pool.acquire() as conn:
        for i in range(3):
            schedule_id = uuid4()
            await conn.execute(
                """
                INSERT INTO schedules (
                    schedule_id, domain_config_id, domain, scan_type,
                    scan_params, frequency, time_config, enabled,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                schedule_id, domain_config_id, f"https://example{i}.com", "quick",
                '{}', "daily", '{"hour": 9, "minute": 0}', True
            )
    
    response = await client.get(
        "/api/v1/schedules",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_update_schedule_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test updating a schedule."""
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
            schedule_id, domain_config_id, "https://example.com", "quick",
            '{}', "daily", '{"hour": 9, "minute": 0}', True
        )
    
    response = await client.put(
        f"/api/v1/schedules/{schedule_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "frequency": "weekly",
            "time_config": {
                "day_of_week": "monday",
                "hour": 10,
                "minute": 30
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["frequency"] == "weekly"
    assert data["time_config"]["hour"] == 10


@pytest.mark.asyncio
async def test_delete_schedule_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test deleting a schedule."""
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
            schedule_id, domain_config_id, "https://example.com", "quick",
            '{}', "daily", '{"hour": 9, "minute": 0}', True
        )
    
    response = await client.delete(
        f"/api/v1/schedules/{schedule_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 204
    
    # Verify schedule is deleted
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM schedules WHERE schedule_id = $1",
            schedule_id
        )
        assert row is None


@pytest.mark.asyncio
async def test_enable_schedule_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test enabling a disabled schedule."""
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
            schedule_id, domain_config_id, "https://example.com", "quick",
            '{}', "daily", '{"hour": 9, "minute": 0}', False
        )
    
    response = await client.post(
        f"/api/v1/schedules/{schedule_id}/enable",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_disable_schedule_success(client: AsyncClient, auth_token: str, db_pool: asyncpg.Pool):
    """Test disabling an enabled schedule."""
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
            schedule_id, domain_config_id, "https://example.com", "quick",
            '{}', "daily", '{"hour": 9, "minute": 0}', True
        )
    
    response = await client.post(
        f"/api/v1/schedules/{schedule_id}/disable",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False


# ============================================================================
# Authentication Tests
# ============================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user: dict):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": "wrong_password"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await client.get("/api/v1/scans")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token."""
    response = await client.get(
        "/api/v1/scans",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_validation_error_response_format(client: AsyncClient, auth_token: str):
    """Test that validation errors return proper format."""
    response = await client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "domain": "https://example.com",
            "scan_mode": "invalid_mode"  # Invalid enum value
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_not_found_error_response_format(client: AsyncClient, auth_token: str):
    """Test that 404 errors return proper format."""
    response = await client.get(
        f"/api/v1/scans/{uuid4()}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
