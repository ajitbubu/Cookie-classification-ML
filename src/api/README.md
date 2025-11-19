# Dynamic Cookie Scanning Service API

FastAPI-based REST API for the Dynamic Cookie Scanning Service platform.

## Features

- **FastAPI Framework**: Modern, fast, and async-ready
- **Authentication**: JWT tokens and API keys
- **Rate Limiting**: Redis-based rate limiting
- **Request Validation**: Automatic validation with Pydantic
- **Error Handling**: Standardized error responses
- **OpenAPI Documentation**: Auto-generated interactive docs
- **CORS Support**: Configurable cross-origin requests
- **Logging**: Request/response logging with unique request IDs

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Redis server
- Required environment variables (see Configuration)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (see Configuration section)

3. Run the API server:
```bash
python run_api.py
```

The API will be available at `http://localhost:8000`

### Interactive Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dcs

# Redis
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET_KEY=your-secret-key-min-32-chars
API_KEY_SALT=your-api-key-salt-min-16-chars

# API Server (optional)
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# CORS (optional)
CORS_ORIGINS=http://localhost:3000,https://dashboard.example.com
```

### Configuration File

You can also use a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env with your values
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/api-keys` - Generate API key
- `GET /api/v1/auth/me` - Get current user

### Scans

- `POST /api/v1/scans` - Create new scan
- `GET /api/v1/scans` - List scans (paginated)
- `GET /api/v1/scans/{scan_id}` - Get scan result
- `DELETE /api/v1/scans/{scan_id}` - Cancel/delete scan
- `GET /api/v1/scans/{scan_id}/progress` - Get scan progress

### Schedules

- `POST /api/v1/schedules` - Create schedule
- `GET /api/v1/schedules` - List schedules
- `GET /api/v1/schedules/{schedule_id}` - Get schedule
- `PUT /api/v1/schedules/{schedule_id}` - Update schedule
- `DELETE /api/v1/schedules/{schedule_id}` - Delete schedule
- `POST /api/v1/schedules/{schedule_id}/enable` - Enable schedule
- `POST /api/v1/schedules/{schedule_id}/disable` - Disable schedule

### Health

- `GET /api/v1/health` - Health check

## Authentication

### JWT Token Authentication

1. Login to get token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

2. Use token in requests:
```bash
curl http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer <your-token>"
```

### API Key Authentication

1. Generate API key (requires JWT token):
```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "scopes": ["scans:read", "scans:write"],
    "rate_limit": 100
  }'
```

2. Use API key in requests:
```bash
curl http://localhost:8000/api/v1/scans \
  -H "X-API-Key: <your-api-key>"
```

## Rate Limiting

All endpoints are rate-limited. Default limits:
- 100 requests per minute per API key/user
- 429 status code when limit exceeded

Rate limit headers in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Error Handling

All errors follow a standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "timestamp": 1234567890.123,
    "request_id": "uuid"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` (400) - Invalid request data
- `AUTHENTICATION_ERROR` (401) - Authentication failed
- `AUTHORIZATION_ERROR` (403) - Insufficient permissions
- `NOT_FOUND` (404) - Resource not found
- `RATE_LIMIT_EXCEEDED` (429) - Rate limit exceeded
- `INTERNAL_SERVER_ERROR` (500) - Server error

## Development

### Running in Development Mode

```bash
# Enable auto-reload
export API_RELOAD=true
python run_api.py
```

### Project Structure

```
api/
├── __init__.py
├── main.py              # FastAPI app creation
├── auth/                # Authentication utilities
│   ├── api_key.py
│   ├── dependencies.py
│   ├── jwt.py
│   └── password.py
├── errors/              # Error handling
│   ├── exceptions.py
│   └── handlers.py
├── middleware/          # Custom middleware
│   ├── logging.py
│   └── rate_limit.py
└── routers/             # API endpoints
    ├── analytics.py
    ├── auth.py
    ├── health.py
    ├── notifications.py
    ├── profiles.py
    ├── scans.py
    └── schedules.py
```

## Testing

Run tests with pytest:

```bash
pytest tests/
```

## Deployment

### Using Docker

```bash
docker build -t dcs-api .
docker run -p 8000:8000 --env-file .env dcs-api
```

### Using Docker Compose

```bash
docker-compose up api
```

### Production Considerations

1. Set strong secrets for JWT_SECRET_KEY and API_KEY_SALT
2. Use HTTPS/TLS in production
3. Configure appropriate CORS origins
4. Set up database connection pooling
5. Enable Redis for rate limiting
6. Configure logging and monitoring
7. Set API_RELOAD=false in production

## Monitoring

Health check endpoint:
```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "2.0.0",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "scanner": "healthy"
  }
}
```

## Support

For issues and questions, please contact the development team.
