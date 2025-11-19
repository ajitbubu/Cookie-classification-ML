# Database Encryption at Rest Setup

This document provides guidance on setting up encryption at rest for the Cookie Scanner Platform database.

## Overview

The platform implements multiple layers of encryption for sensitive data:

1. **Application-level encryption**: Sensitive fields (webhook URLs, API secrets) are encrypted using Fernet symmetric encryption before storage
2. **Database-level encryption**: PostgreSQL Transparent Data Encryption (TDE) for entire database encryption
3. **Hashing**: API keys and cookie values are hashed using SHA-256 (one-way, not reversible)

## Application-Level Encryption

### Encrypted Fields

The following fields are encrypted at the application level using the `EncryptionManager`:

- **Notification webhook URLs** (notifications table)
- **SMTP passwords** (configuration)
- **Slack webhook URLs** (configuration)
- **API secrets** (configuration)

### Implementation

```python
from api.auth.encryption import get_encryption_manager

# Encrypt sensitive data before storage
manager = get_encryption_manager()
encrypted_url = manager.encrypt(webhook_url)

# Decrypt when retrieving
decrypted_url = manager.decrypt(encrypted_url)
```

### Key Management

- Encryption keys are derived from the `JWT_SECRET_KEY` environment variable
- Use a strong, randomly generated secret key (minimum 32 characters)
- Store the secret key securely (environment variables, secrets manager)
- **IMPORTANT**: Backup your secret key - data cannot be decrypted without it

## Database-Level Encryption (PostgreSQL TDE)

### Option 1: PostgreSQL pgcrypto Extension

For column-level encryption within PostgreSQL:

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt data when inserting
INSERT INTO sensitive_table (encrypted_field)
VALUES (pgp_sym_encrypt('sensitive data', 'encryption_key'));

-- Decrypt data when querying
SELECT pgp_sym_decrypt(encrypted_field::bytea, 'encryption_key')
FROM sensitive_table;
```

### Option 2: Full Database Encryption

For production deployments, use full database encryption:

#### PostgreSQL with LUKS (Linux)

1. **Create encrypted volume**:
```bash
# Create LUKS encrypted volume
cryptsetup luksFormat /dev/sdb1

# Open encrypted volume
cryptsetup luksOpen /dev/sdb1 pgdata

# Format and mount
mkfs.ext4 /dev/mapper/pgdata
mount /dev/mapper/pgdata /var/lib/postgresql/data
```

2. **Configure PostgreSQL to use encrypted volume**:
```bash
# Update PostgreSQL data directory
sudo systemctl stop postgresql
sudo rsync -av /var/lib/postgresql/data/ /mnt/encrypted/data/
sudo chown -R postgres:postgres /mnt/encrypted/data
```

3. **Update PostgreSQL configuration**:
```bash
# Edit /etc/postgresql/15/main/postgresql.conf
data_directory = '/mnt/encrypted/data'
```

#### PostgreSQL with ZFS Encryption

```bash
# Create encrypted ZFS dataset
zfs create -o encryption=on -o keyformat=passphrase rpool/pgdata

# Mount and configure PostgreSQL
zfs set mountpoint=/var/lib/postgresql/data rpool/pgdata
chown -R postgres:postgres /var/lib/postgresql/data
```

### Option 3: Cloud Provider Encryption

#### AWS RDS

```terraform
resource "aws_db_instance" "postgres" {
  engine               = "postgres"
  storage_encrypted    = true
  kms_key_id          = aws_kms_key.db_encryption.arn
  
  # Other configuration...
}
```

#### Google Cloud SQL

```terraform
resource "google_sql_database_instance" "postgres" {
  settings {
    disk_encryption_configuration {
      kms_key_name = google_kms_crypto_key.db_key.id
    }
  }
}
```

#### Azure Database for PostgreSQL

```terraform
resource "azurerm_postgresql_server" "postgres" {
  infrastructure_encryption_enabled = true
  
  # Other configuration...
}
```

## Backup Encryption

### PostgreSQL Backup with Encryption

```bash
# Backup with encryption
pg_dump -U postgres cookie_scanner | \
  gpg --symmetric --cipher-algo AES256 > backup.sql.gpg

# Restore from encrypted backup
gpg --decrypt backup.sql.gpg | \
  psql -U postgres cookie_scanner
```

### Automated Encrypted Backups

```bash
#!/bin/bash
# backup_encrypted.sh

BACKUP_DIR="/var/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cookie_scanner_$DATE.sql"
GPG_KEY="backup@example.com"

# Create backup
pg_dump -U postgres cookie_scanner > "$BACKUP_FILE"

# Encrypt backup
gpg --encrypt --recipient "$GPG_KEY" "$BACKUP_FILE"

# Remove unencrypted backup
rm "$BACKUP_FILE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.gpg" -mtime +30 -delete
```

## SSL/TLS for Data in Transit

### PostgreSQL SSL Configuration

1. **Generate SSL certificates**:
```bash
# Generate server certificate
openssl req -new -x509 -days 365 -nodes -text \
  -out server.crt -keyout server.key \
  -subj "/CN=postgres.example.com"

# Set permissions
chmod 600 server.key
chown postgres:postgres server.key server.crt
```

2. **Configure PostgreSQL**:
```bash
# Edit postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
ssl_ca_file = '/path/to/root.crt'
```

3. **Update connection string**:
```bash
DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require"
```

### Connection String SSL Modes

- `disable`: No SSL (not recommended for production)
- `allow`: Try SSL, fall back to non-SSL
- `prefer`: Try SSL first, fall back to non-SSL
- `require`: Require SSL (recommended minimum)
- `verify-ca`: Require SSL and verify CA
- `verify-full`: Require SSL and verify hostname (most secure)

## Security Best Practices

### Key Management

1. **Use a secrets manager**:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

2. **Rotate encryption keys regularly**:
   - Schedule key rotation every 90 days
   - Implement key versioning
   - Re-encrypt data with new keys

3. **Separate encryption keys by environment**:
   - Development: Different key
   - Staging: Different key
   - Production: Different key

### Access Control

1. **Limit database access**:
```sql
-- Revoke public access
REVOKE ALL ON DATABASE cookie_scanner FROM PUBLIC;

-- Grant specific permissions
GRANT CONNECT ON DATABASE cookie_scanner TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
```

2. **Use connection pooling with authentication**:
```python
# Use connection pooling with SSL
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=verify-full&sslcert=/path/to/client.crt&sslkey=/path/to/client.key"
```

### Monitoring

1. **Enable audit logging**:
```sql
-- Enable PostgreSQL audit logging
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
```

2. **Monitor encryption status**:
```sql
-- Check if database is encrypted (cloud providers)
SELECT datname, datencryption FROM pg_database WHERE datname = 'cookie_scanner';
```

## Compliance Considerations

### GDPR

- Encrypt all personal data at rest
- Implement data retention policies
- Provide data export functionality
- Enable right to erasure (data deletion)

### HIPAA

- Use FIPS 140-2 validated encryption modules
- Implement access controls and audit logging
- Encrypt backups
- Use encrypted connections (TLS 1.2+)

### PCI DSS

- Encrypt cardholder data at rest
- Use strong cryptography (AES-256)
- Implement key management procedures
- Regularly test encryption systems

## Troubleshooting

### Cannot decrypt data

**Problem**: Data cannot be decrypted after key change

**Solution**: 
- Ensure `JWT_SECRET_KEY` matches the key used for encryption
- Check for key rotation without data re-encryption
- Restore from backup if key is lost

### Performance impact

**Problem**: Encryption/decryption causing performance issues

**Solution**:
- Use connection pooling to reduce overhead
- Cache decrypted values when appropriate
- Consider hardware acceleration (AES-NI)
- Use database-level encryption for better performance

### SSL connection errors

**Problem**: Cannot connect to database with SSL

**Solution**:
```bash
# Verify SSL configuration
psql "postgresql://user@host/db?sslmode=require" -c "SHOW ssl;"

# Check certificate validity
openssl x509 -in server.crt -text -noout

# Test connection
openssl s_client -connect host:5432 -starttls postgres
```

## References

- [PostgreSQL Encryption Options](https://www.postgresql.org/docs/current/encryption-options.html)
- [Python Cryptography Library](https://cryptography.io/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [NIST Encryption Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)
