# Database Migrations

This directory contains database migration scripts for the Cookie Scanner Platform.

## Structure

```
database/
├── migrations/          # SQL migration files
│   └── 001_initial_schema.sql
├── migrate.py          # Migration runner script
└── README.md           # This file
```

## Running Migrations

### Prerequisites

1. PostgreSQL database server running
2. Database created
3. `DATABASE_URL` environment variable set

### Execute Migrations

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/cookie_scanner"

# Run migrations
python database/migrate.py
```

### With Custom Database URL

```bash
python database/migrate.py --url "postgresql://user:password@localhost:5432/cookie_scanner"
```

### With Custom Migrations Directory

```bash
python database/migrate.py --dir /path/to/migrations
```

## Migration Files

Migration files are SQL scripts that should be named with a numeric prefix for ordering:

- `001_initial_schema.sql` - Initial database schema
- `002_add_indexes.sql` - Additional indexes (example)
- `003_add_columns.sql` - Schema changes (example)

## Migration Tracking

The migration system creates a `schema_migrations` table to track which migrations have been applied:

```sql
CREATE TABLE schema_migrations (
    migration_id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

## Creating New Migrations

1. Create a new SQL file in the `migrations/` directory
2. Name it with the next sequential number (e.g., `002_description.sql`)
3. Write your SQL statements
4. Run the migration script

Example migration file:

```sql
-- Migration: 002_add_user_preferences.sql
-- Description: Add user preferences table
-- Date: 2025-11-04

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
```

## Rollback

Automatic rollback is not currently implemented. To rollback a migration:

1. Manually write and execute the reverse SQL statements
2. Remove the migration entry from `schema_migrations` table

## Best Practices

1. **Test migrations** on a development database first
2. **Backup production data** before running migrations
3. **Keep migrations small** and focused on a single change
4. **Use transactions** where appropriate
5. **Document changes** in migration file comments
6. **Never modify** existing migration files after they've been applied

## Troubleshooting

### Migration fails with "relation already exists"

This usually means the migration was partially applied. Check the database state and either:
- Complete the migration manually
- Drop the partially created objects and re-run

### Cannot connect to database

Verify:
- Database server is running
- `DATABASE_URL` is correct
- User has necessary permissions
- Network connectivity

### Migration tracking table not found

The migration script automatically creates the `schema_migrations` table on first run. If you see this error, ensure the database user has CREATE TABLE permissions.
