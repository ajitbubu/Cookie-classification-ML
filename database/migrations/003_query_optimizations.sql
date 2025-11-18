-- Migration: 003_query_optimizations.sql
-- Description: Add additional indexes and optimizations for frequently-run queries
-- Date: 2025-11-17

-- Additional indexes for scan_results table
-- Optimize queries filtering by status and timestamp together
CREATE INDEX IF NOT EXISTS idx_scan_results_status_timestamp 
    ON scan_results(status, timestamp_utc DESC);

-- Optimize queries filtering by domain_config_id and timestamp
CREATE INDEX IF NOT EXISTS idx_scan_results_config_timestamp 
    ON scan_results(domain_config_id, timestamp_utc DESC);

-- Optimize queries filtering by scan_mode and status
CREATE INDEX IF NOT EXISTS idx_scan_results_mode_status 
    ON scan_results(scan_mode, status);

-- Partial index for active/running scans (most frequently queried)
CREATE INDEX IF NOT EXISTS idx_scan_results_active 
    ON scan_results(scan_id, domain, timestamp_utc DESC) 
    WHERE status IN ('pending', 'running');

-- Additional indexes for cookies table
-- Optimize queries grouping by category and type
CREATE INDEX IF NOT EXISTS idx_cookies_category_type 
    ON cookies(category, cookie_type);

-- Optimize queries filtering by domain and category
CREATE INDEX IF NOT EXISTS idx_cookies_domain_category 
    ON cookies(domain, category);

-- Optimize queries filtering by vendor
CREATE INDEX IF NOT EXISTS idx_cookies_vendor_category 
    ON cookies(vendor, category) WHERE vendor IS NOT NULL;

-- Partial index for third-party cookies (frequently analyzed)
CREATE INDEX IF NOT EXISTS idx_cookies_third_party 
    ON cookies(scan_id, name, domain) 
    WHERE cookie_type = 'Third Party';

-- Additional indexes for schedules table
-- Optimize queries for upcoming scheduled jobs
CREATE INDEX IF NOT EXISTS idx_schedules_next_run_enabled 
    ON schedules(next_run, domain) 
    WHERE enabled = TRUE AND next_run IS NOT NULL;

-- Optimize queries filtering by frequency
CREATE INDEX IF NOT EXISTS idx_schedules_frequency_enabled 
    ON schedules(frequency, enabled);

-- Additional indexes for job_executions table
-- Optimize queries filtering by status and time range
CREATE INDEX IF NOT EXISTS idx_job_executions_status_started 
    ON job_executions(status, started_at DESC);

-- Optimize queries for recent failed executions
CREATE INDEX IF NOT EXISTS idx_job_executions_failed 
    ON job_executions(domain, started_at DESC) 
    WHERE status = 'failed';

-- Optimize queries grouping by domain
CREATE INDEX IF NOT EXISTS idx_job_executions_domain_status 
    ON job_executions(domain, status, started_at DESC);

-- Additional indexes for notifications table
-- Optimize queries for pending notifications
CREATE INDEX IF NOT EXISTS idx_notifications_pending 
    ON notifications(created_at) 
    WHERE status = 'pending';

-- Optimize queries for failed notifications needing retry
CREATE INDEX IF NOT EXISTS idx_notifications_retry 
    ON notifications(retry_count, created_at) 
    WHERE status IN ('failed', 'retrying');

-- Additional indexes for reports table
-- Optimize queries filtering by type and date
CREATE INDEX IF NOT EXISTS idx_reports_type_generated 
    ON reports(report_type, generated_at DESC);

-- Optimize queries filtering by scan and type
CREATE INDEX IF NOT EXISTS idx_reports_scan_type 
    ON reports(scan_id, report_type);

-- Additional indexes for scan_profiles table
-- Optimize queries filtering by name (for lookups)
CREATE INDEX IF NOT EXISTS idx_scan_profiles_name 
    ON scan_profiles(name);

-- GIN indexes for JSONB columns (for faster JSON queries)
-- Enable faster queries on config JSONB in scan_profiles
CREATE INDEX IF NOT EXISTS idx_scan_profiles_config_gin 
    ON scan_profiles USING GIN (config);

-- Enable faster queries on params JSONB in scan_results
CREATE INDEX IF NOT EXISTS idx_scan_results_params_gin 
    ON scan_results USING GIN (params);

-- Enable faster queries on time_config JSONB in schedules
CREATE INDEX IF NOT EXISTS idx_schedules_time_config_gin 
    ON schedules USING GIN (time_config);

-- Enable faster queries on metadata JSONB in cookies
CREATE INDEX IF NOT EXISTS idx_cookies_metadata_gin 
    ON cookies USING GIN (metadata);

-- Enable faster queries on iab_purposes JSONB in cookies
CREATE INDEX IF NOT EXISTS idx_cookies_iab_purposes_gin 
    ON cookies USING GIN (iab_purposes);

-- Enable faster queries on error_details JSONB in job_executions
CREATE INDEX IF NOT EXISTS idx_job_executions_error_details_gin 
    ON job_executions USING GIN (error_details);

-- Enable faster queries on data JSONB in notifications
CREATE INDEX IF NOT EXISTS idx_notifications_data_gin 
    ON notifications USING GIN (data);

-- Add statistics targets for better query planning
-- Increase statistics for frequently filtered columns
ALTER TABLE scan_results ALTER COLUMN domain SET STATISTICS 1000;
ALTER TABLE scan_results ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE scan_results ALTER COLUMN timestamp_utc SET STATISTICS 1000;

ALTER TABLE cookies ALTER COLUMN category SET STATISTICS 1000;
ALTER TABLE cookies ALTER COLUMN cookie_type SET STATISTICS 1000;
ALTER TABLE cookies ALTER COLUMN domain SET STATISTICS 1000;

ALTER TABLE schedules ALTER COLUMN enabled SET STATISTICS 1000;
ALTER TABLE schedules ALTER COLUMN next_run SET STATISTICS 1000;

ALTER TABLE job_executions ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE job_executions ALTER COLUMN started_at SET STATISTICS 1000;

-- Create materialized view for frequently accessed analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_domain_scan_summary AS
SELECT 
    domain,
    COUNT(*) as total_scans,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_scans,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_scans,
    MAX(timestamp_utc) as last_scan_time,
    AVG(duration_seconds) as avg_duration_seconds,
    AVG(total_cookies) as avg_total_cookies
FROM scan_results
WHERE timestamp_utc >= NOW() - INTERVAL '90 days'
GROUP BY domain;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_domain_scan_summary_domain 
    ON mv_domain_scan_summary(domain);

CREATE INDEX IF NOT EXISTS idx_mv_domain_scan_summary_last_scan 
    ON mv_domain_scan_summary(last_scan_time DESC);

-- Create materialized view for cookie category statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_cookie_category_stats AS
SELECT 
    c.domain,
    c.category,
    c.cookie_type,
    COUNT(*) as cookie_count,
    COUNT(DISTINCT c.name) as unique_cookies,
    MAX(sr.timestamp_utc) as last_updated
FROM cookies c
JOIN scan_results sr ON c.scan_id = sr.scan_id
WHERE sr.timestamp_utc >= NOW() - INTERVAL '30 days'
GROUP BY c.domain, c.category, c.cookie_type;

-- Create indexes on cookie category stats view
CREATE INDEX IF NOT EXISTS idx_mv_cookie_category_stats_domain 
    ON mv_cookie_category_stats(domain);

CREATE INDEX IF NOT EXISTS idx_mv_cookie_category_stats_category 
    ON mv_cookie_category_stats(category);

-- Add comments for documentation
COMMENT ON INDEX idx_scan_results_active IS 'Optimizes queries for active/running scans';
COMMENT ON INDEX idx_cookies_third_party IS 'Optimizes queries for third-party cookie analysis';
COMMENT ON INDEX idx_schedules_next_run_enabled IS 'Optimizes scheduler queries for upcoming jobs';
COMMENT ON INDEX idx_job_executions_failed IS 'Optimizes queries for failed job analysis';
COMMENT ON INDEX idx_notifications_pending IS 'Optimizes queries for pending notification processing';

COMMENT ON MATERIALIZED VIEW mv_domain_scan_summary IS 'Pre-computed domain scan statistics for dashboard';
COMMENT ON MATERIALIZED VIEW mv_cookie_category_stats IS 'Pre-computed cookie category statistics for analytics';

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_domain_scan_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cookie_category_stats;
END;
$$ LANGUAGE plpgsql;

-- Add comment on function
COMMENT ON FUNCTION refresh_analytics_views() IS 'Refreshes all analytics materialized views';
