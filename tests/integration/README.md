# Integration Tests

This directory contains integration tests for the Cookie Scanner Platform API endpoints.

## Overview

Integration tests verify the complete workflow of API endpoints including:
- Scan creation and retrieval
- Schedule CRUD operations
- Analytics endpoints
- Authentication and authorization
- Error handling and validation

## Prerequisites

Before running integration tests, ensure you have:

1. **Test Database**: PostgreSQL database for testing
2. **Redis**: Redis instance for caching (optional)
3. **Python Dependencies**: All requirements installed
4. **Environment Variables**: Test configuration set up

## Setup

### 1. Create Test Database

```bash
# Create test database
createdb dcs_test

# Run migrations on test database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dcs_test python run_migrations.py
```

### 2. Configure Environment

Create a `.env.test` file or set environment variables:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dcs_test

# Redis (optional)
REDIS_URL=redis://localhost:6379/1

# JWT
JWT_SECRET_KEY=test_secret_key_change_in_production

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

## Running Tests

### Run All Integration Tests

```bash
# From project root
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest tests/integration/test_api_integration.py -v
```

### Run Specific Test

```bash
pytest tests/integration/test_api_integration.py::test_create_scan_success -v
```

### Run with Coverage

```bash
pytest tests/integration/ --cov=api --cov=services --cov-report=html
```

### Run in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/integration/ -n auto
```

## Test Structure

```
tests/integration/
├── README.md                    # This file
├── test_api_integration.py      # Main API integration tests
├── conftest.py                  # Shared fixtures (if needed)
└── __init__.py
```

## Test Categories

### Scan Endpoint Tests
- `test_create_scan_success` - Create scan successfully
- `test_create_scan_invalid_domain` - Validation error handling
- `test_create_scan_unauthorized` - Authentication required
- `test_get_scan_success` - Retrieve scan by ID
- `test_get_scan_not_found` - Handle missing scan
- `test_list_scans_pagination` - Pagination functionality
- `test_list_scans_filtering` - Filter by status/domain
- `test_delete_scan_success` - Delete completed scan

### Schedule Endpoint Tests
- `test_create_schedule_success` - Create schedule successfully
- `test_create_schedule_invalid_time_config` - Validation errors
- `test_get_schedule_success` - Retrieve schedule by ID
- `test_list_schedules_success` - List all schedules
- `test_update_schedule_success` - Update schedule configuration
- `test_delete_schedule_success` - Delete schedule
- `test_enable_schedule_success` - Enable disabled schedule
- `test_disable_schedule_success` - Disable active schedule

### Authentication Tests
- `test_login_success` - Successful login
- `test_login_invalid_credentials` - Invalid credentials
- `test_protected_endpoint_without_token` - Require authentication
- `test_protected_endpoint_with_invalid_token` - Invalid token

### Error Handling Tests
- `test_validation_error_response_format` - Validation error format
- `test_not_found_error_response_format` - 404 error format

## Fixtures

### Database Fixtures
- `db_pool` - Test database connection pool
- `clean_database` - Clean database before/after each test

### Authentication Fixtures
- `test_user` - Create test user in database
- `auth_token` - Generate JWT token for test user

### Client Fixtures
- `client` - HTTP client for making API requests

## Best Practices

### 1. Test Isolation
Each test should be independent and not rely on other tests. Use fixtures to set up required state.

### 2. Database Cleanup
The `clean_database` fixture ensures a clean state before each test. Always use it.

### 3. Async Tests
All tests are async and use `@pytest.mark.asyncio` decorator.

### 4. Assertions
Use clear, specific assertions:
```python
# Good
assert response.status_code == 201
assert data["domain"] == "https://example.com"

# Avoid
assert response.status_code in [200, 201]
assert "domain" in data
```

### 5. Error Testing
Always test error cases:
- Invalid input
- Missing authentication
- Not found errors
- Validation errors

## Troubleshooting

### Database Connection Errors

```bash
# Check if PostgreSQL is running
pg_isready

# Check if test database exists
psql -l | grep dcs_test

# Recreate test database
dropdb dcs_test
createdb dcs_test
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dcs_test python run_migrations.py
```

### Import Errors

```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
cd /path/to/project
pytest tests/integration/
```

### Async Warnings

If you see warnings about event loops:
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure tests use @pytest.mark.asyncio
```

### Test Database Not Cleaned

If tests fail due to existing data:
```bash
# Manually clean test database
psql dcs_test -c "DELETE FROM cookies; DELETE FROM scan_results; DELETE FROM schedules; DELETE FROM users;"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: dcs_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/dcs_test
        run: python run_migrations.py
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/dcs_test
          REDIS_URL: redis://localhost:6379/1
          JWT_SECRET_KEY: test_secret_key
        run: pytest tests/integration/ -v --cov=api --cov=services
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Adding New Tests

When adding new API endpoints, follow this pattern:

1. **Create test function** with descriptive name
2. **Use appropriate fixtures** (client, auth_token, db_pool)
3. **Set up test data** in database if needed
4. **Make API request** using client
5. **Assert response** status code and data
6. **Verify side effects** (database changes, etc.)

Example:
```python
@pytest.mark.asyncio
async def test_new_endpoint_success(client: AsyncClient, auth_token: str):
    """Test new endpoint functionality."""
    # Setup
    # ...
    
    # Execute
    response = await client.post(
        "/api/v1/new-endpoint",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"key": "value"}
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "value"
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [HTTPX Documentation](https://www.python-httpx.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Questions?** Open an issue or contact the development team.
