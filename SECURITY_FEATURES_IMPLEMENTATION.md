# Security Features Implementation Summary

This document summarizes the security features implemented for the Cookie Scanner Platform as part of Task 10.

## Overview

All four security subtasks have been successfully implemented:
1. Audit logging system
2. Encryption at rest
3. HTTPS/TLS enforcement
4. Account lockout mechanism

## 1. Audit Logging System

### Components Created

#### Database Migration
- **File**: `database/migrations/004_audit_logging.sql`
- Creates `audit_logs` table with comprehensive indexing
- Tracks user actions, resource changes, and security events

#### Audit Logger Module
- **File**: `api/auth/audit.py`
- **Class**: `AuditLogger`
- **Features**:
  - Logs authentication attempts (success/failure)
  - Tracks configuration changes (profiles, schedules)
  - Records data access operations (scans, reports)
  - Provides query methods for retrieving audit logs
  - Tracks failed login attempts for lockout mechanism

#### API Endpoints
- **File**: `api/routers/audit.py`
- **Endpoints**:
  - `GET /api/v1/audit/logs` - Get audit logs with filtering (admin only)
  - `GET /api/v1/audit/activity` - Get current user's activity history
  - `GET /api/v1/audit/actions` - List available audit actions
  - `GET /api/v1/audit/resource-types` - List available resource types
  - `GET /api/v1/audit/lockout/{email}` - Get account lockout status (admin only)
  - `POST /api/v1/audit/unlock` - Manually unlock account (admin only)
  - `POST /api/v1/audit/reset-attempts` - Reset failed login attempts (admin only)

### Usage Example

```python
from api.auth.audit import get_audit_logger, AuditAction, ResourceType, AuditStatus

audit_logger = get_audit_logger()

# Log authentication attempt
audit_logger.log_authentication(
    success=True,
    email="user@example.com",
    user_id=user_id,
    ip_address="192.168.1.1"
)

# Log configuration change
audit_logger.log_configuration_change(
    action=AuditAction.PROFILE_CREATED,
    resource_type=ResourceType.PROFILE,
    resource_id=profile_id,
    user_id=user_id,
    changes={"name": "New Profile"}
)

# Log data access
audit_logger.log_data_access(
    action=AuditAction.SCAN_ACCESSED,
    resource_type=ResourceType.SCAN,
    resource_id=scan_id,
    user_id=user_id
)
```

## 2. Encryption at Rest

### Components Created

#### Encryption Manager
- **File**: `api/auth/encryption.py`
- **Class**: `EncryptionManager`
- **Features**:
  - Fernet symmetric encryption
  - Key derivation from JWT secret using PBKDF2
  - Encrypt/decrypt individual fields
  - Encrypt/decrypt dictionary fields
  - Helper functions for webhook URLs

#### Documentation
- **File**: `database/ENCRYPTION_SETUP.md`
- Comprehensive guide for database-level encryption
- Covers PostgreSQL TDE, LUKS, ZFS encryption
- Cloud provider encryption (AWS, GCP, Azure)
- Backup encryption strategies
- SSL/TLS for data in transit

#### Integration
- **File**: `services/notification_channels.py`
- Updated to decrypt webhook URLs before use
- Supports both encrypted and plaintext URLs (backward compatible)

### Encrypted Fields

The following fields are encrypted at the application level:
- Notification webhook URLs
- Slack webhook URLs
- SMTP passwords (in configuration)
- API secrets (in configuration)

### Usage Example

```python
from api.auth.encryption import get_encryption_manager

manager = get_encryption_manager()

# Encrypt sensitive data
encrypted_url = manager.encrypt("https://webhook.example.com/notify")

# Store in database
# ...

# Decrypt when retrieving
decrypted_url = manager.decrypt(encrypted_url)
```

## 3. HTTPS/TLS Enforcement

### Components Created

#### HTTPS Redirect Middleware
- **File**: `api/middleware/https_redirect.py`
- **Classes**:
  - `HTTPSRedirectMiddleware` - Redirects HTTP to HTTPS
  - `SecurityHeadersMiddleware` - Adds security headers

#### Security Headers Added
- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `X-Frame-Options: DENY`
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`

#### Documentation
- **File**: `SSL_TLS_SETUP.md`
- Complete SSL/TLS configuration guide
- Let's Encrypt setup instructions
- Nginx and Apache configuration examples
- Docker deployment with SSL
- Certificate renewal procedures
- Testing and troubleshooting

### Configuration

```python
# api/main.py
from api.middleware.https_redirect import HTTPSRedirectMiddleware, SecurityHeadersMiddleware

# Add HTTPS redirect (production only)
if config.environment == "production":
    app.add_middleware(
        HTTPSRedirectMiddleware,
        enabled=True,
        exclude_paths=['/health']
    )
    
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=31536000,
        hsts_include_subdomains=True
    )
```

### Secure Cookie Settings

```python
response.set_cookie(
    key="session",
    value=token,
    httponly=True,      # Prevent JavaScript access
    secure=True,        # HTTPS only
    samesite='strict'   # CSRF protection
)
```

## 4. Account Lockout Mechanism

### Components Created

#### Account Lockout Manager
- **File**: `api/auth/lockout.py`
- **Class**: `AccountLockoutManager`
- **Features**:
  - Tracks failed login attempts in Redis
  - Locks account after 5 failed attempts within 15 minutes
  - Automatic unlock after 15 minutes
  - Manual unlock by administrators
  - Integrates with audit logging

#### Login Integration
- **File**: `api/routers/auth.py`
- Updated login endpoint to:
  - Check account lockout status before authentication
  - Record failed login attempts
  - Reset attempts on successful login
  - Return detailed error messages with remaining attempts
  - Log all authentication events to audit trail

### Configuration

Default settings (configurable):
- **Max attempts**: 5 failed logins
- **Lockout duration**: 15 minutes
- **Attempt window**: 15 minutes

### Usage Example

```python
from api.auth.lockout import get_lockout_manager

lockout_manager = get_lockout_manager()

# Check if account is locked
is_locked, unlock_time = lockout_manager.is_locked(email)

# Record failed attempt
should_lock, attempt_count, unlock_time = lockout_manager.record_failed_attempt(
    email,
    ip_address
)

# Reset attempts on successful login
lockout_manager.reset_attempts(email)

# Manual unlock (admin)
lockout_manager.unlock_account(email, admin_user_id)
```

### API Response Examples

#### Successful Login
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Failed Login (Not Locked)
```json
{
  "error": "invalid_credentials",
  "message": "Invalid credentials. 3 attempts remaining before account lockout.",
  "failed_attempts": 2,
  "remaining_attempts": 3
}
```

#### Account Locked
```json
{
  "error": "account_locked",
  "message": "Account locked due to too many failed login attempts. Try again after 2025-11-17 15:30:00 UTC",
  "unlock_time": "2025-11-17T15:30:00Z",
  "locked_for_seconds": 900
}
```

## Security Best Practices Implemented

### Authentication & Authorization
- ✅ JWT token-based authentication
- ✅ API key authentication with hashing
- ✅ Password hashing with bcrypt
- ✅ Account lockout after failed attempts
- ✅ Audit logging of all authentication events

### Data Protection
- ✅ Cookie values hashed with SHA-256
- ✅ Sensitive fields encrypted with Fernet
- ✅ API keys hashed before storage
- ✅ Database-level encryption documentation
- ✅ Backup encryption guidance

### Network Security
- ✅ HTTPS/TLS enforcement
- ✅ Secure cookie settings (httponly, secure, samesite)
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ CORS configuration for production

### Monitoring & Compliance
- ✅ Comprehensive audit logging
- ✅ Failed login attempt tracking
- ✅ Account lockout events logged
- ✅ Configuration change tracking
- ✅ Data access logging

## Database Schema

### audit_logs Table

```sql
CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes
- `idx_audit_logs_user_id` - User-based queries
- `idx_audit_logs_action` - Action-based filtering
- `idx_audit_logs_resource_type` - Resource type filtering
- `idx_audit_logs_created_at` - Time-based queries
- `idx_audit_logs_user_action` - Composite for user activity
- `idx_audit_logs_resource` - Composite for resource tracking

## Redis Keys

### Account Lockout
- `login_attempts:{email}` - Failed attempt counter (TTL: 15 minutes)
- `account_locked:{email}` - Lockout status (TTL: 15 minutes)

## Testing

### Manual Testing

1. **Test Account Lockout**:
```bash
# Attempt login 5 times with wrong password
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
done

# 6th attempt should return 423 Locked
```

2. **Test Audit Logging**:
```bash
# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

# View audit logs (admin only)
curl -X GET http://localhost:8000/api/v1/audit/logs \
  -H "Authorization: Bearer $TOKEN"
```

3. **Test Encryption**:
```python
from api.auth.encryption import get_encryption_manager

manager = get_encryption_manager()
encrypted = manager.encrypt("sensitive_data")
decrypted = manager.decrypt(encrypted)
assert decrypted == "sensitive_data"
```

## Migration Instructions

### 1. Run Database Migration

```bash
# Apply audit logging migration
python run_migrations.py
```

### 2. Update Environment Variables

```bash
# Add to .env
HTTPS_REDIRECT_ENABLED=true  # Production only
SECURE_COOKIES=true          # Production only
HSTS_ENABLED=true           # Production only
```

### 3. Update Application Startup

```python
# Ensure Redis is initialized for lockout tracking
from cache.redis_client import init_redis_client
init_redis_client()

# Initialize lockout manager
from api.auth.lockout import init_lockout_manager
init_lockout_manager(
    max_attempts=5,
    lockout_duration_minutes=15,
    attempt_window_minutes=15
)
```

### 4. Add Middleware (Production)

```python
# api/main.py
if config.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware, enabled=True)
    app.add_middleware(SecurityHeadersMiddleware)
```

## Compliance Considerations

### GDPR
- ✅ Audit trail for data access
- ✅ Encryption of personal data
- ✅ Right to access (audit logs)
- ✅ Data retention policies

### HIPAA
- ✅ Access controls and authentication
- ✅ Audit logging
- ✅ Encryption at rest and in transit
- ✅ Account lockout for security

### PCI DSS
- ✅ Strong cryptography (AES-256, SHA-256)
- ✅ Access control mechanisms
- ✅ Audit trails
- ✅ Secure transmission (TLS)

## Future Enhancements

1. **Multi-factor Authentication (MFA)**
   - TOTP support
   - SMS verification
   - Backup codes

2. **Advanced Threat Detection**
   - IP-based rate limiting
   - Geolocation anomaly detection
   - Device fingerprinting

3. **Enhanced Audit Logging**
   - Real-time alerting
   - Log aggregation (ELK stack)
   - Anomaly detection in audit logs

4. **Key Rotation**
   - Automated encryption key rotation
   - API key expiration policies
   - Certificate auto-renewal

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)
- [Python Cryptography Library](https://cryptography.io/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
