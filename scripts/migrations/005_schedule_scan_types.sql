-- Migration: Add scan_type and scan_params to schedules table
-- Description: Extend schedules table to support three-tier scanning system
--              (quick scans, deep scans with configurable parameters)
-- Version: 005
-- Date: 2025-01-15

-- ============================================================================
-- UP Migration
-- ============================================================================

-- Add scan_type column to schedules table
ALTER TABLE schedules
ADD COLUMN IF NOT EXISTS scan_type VARCHAR(20) NOT NULL DEFAULT 'quick';

-- Add scan_params column to schedules table
ALTER TABLE schedules
ADD COLUMN IF NOT EXISTS scan_params JSONB DEFAULT '{}';

-- Add comment to scan_type column
COMMENT ON COLUMN schedules.scan_type IS 'Type of scan: quick (main page + custom pages) or deep (full crawl up to max_pages)';

-- Add comment to scan_params column
COMMENT ON COLUMN schedules.scan_params IS 'Scan configuration parameters (max_pages, custom_pages, chunk_size, etc.)';

-- Create index on scan_type for filtering
CREATE INDEX IF NOT EXISTS idx_schedules_scan_type ON schedules(scan_type);

-- Update existing schedules to have default scan_type
UPDATE schedules
SET scan_type = 'quick'
WHERE scan_type IS NULL;

-- Update existing schedules to have empty scan_params
UPDATE schedules
SET scan_params = '{}'::jsonb
WHERE scan_params IS NULL;

-- Add check constraint for scan_type
ALTER TABLE schedules
ADD CONSTRAINT chk_schedules_scan_type
CHECK (scan_type IN ('quick', 'deep'));

-- ============================================================================
-- Example scan_params structures
-- ============================================================================

-- Quick scan params example:
-- {
--   "custom_pages": ["/about", "/contact", "/privacy"]
-- }

-- Deep scan params example:
-- {
--   "max_pages": 5000,
--   "custom_pages": ["/important-page"],
--   "chunk_size": 1000,
--   "browser_pool_size": 5,
--   "pages_per_browser": 20,
--   "timeout": 30000,
--   "accept_selector": "button:has-text('Accept')"
-- }

-- ============================================================================
-- DOWN Migration (Rollback)
-- ============================================================================

-- To rollback this migration, run:
--
-- DROP INDEX IF EXISTS idx_schedules_scan_type;
-- ALTER TABLE schedules DROP CONSTRAINT IF EXISTS chk_schedules_scan_type;
-- ALTER TABLE schedules DROP COLUMN IF EXISTS scan_params;
-- ALTER TABLE schedules DROP COLUMN IF EXISTS scan_type;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify columns exist
-- SELECT column_name, data_type, column_default, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'schedules'
-- AND column_name IN ('scan_type', 'scan_params');

-- Count schedules by scan type
-- SELECT scan_type, COUNT(*) as count
-- FROM schedules
-- GROUP BY scan_type;

-- View schedules with scan parameters
-- SELECT schedule_id, domain, scan_type, scan_params, frequency, enabled
-- FROM schedules
-- ORDER BY created_at DESC
-- LIMIT 10;
